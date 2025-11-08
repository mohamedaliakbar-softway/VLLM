"""
SIMPLE Caption Generator - Start with Gemini, optionally use Vosk

IMPORTANT CLARIFICATIONS:
1. Vosk has NO API KEY - it's offline software (model already downloaded)
2. You only need Gemini API key (which you have)
3. This file tries Vosk first (best quality), falls back to Gemini (still good)

WHY THIS APPROACH:
- Test Gemini first to see if it's "good enough"
- Use Vosk if you want guaranteed accuracy
- Automatic fallback means it always works
"""
import os
import json
import ffmpeg
import wave
from pathlib import Path
from typing import Dict, List
from google import genai
from config import settings

# Try to import Vosk (offline speech recognition)
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False


class CaptionGenerator:
    """
    Hybrid caption generator:
    - Tries Vosk first (offline, accurate, FREE)
    - Falls back to Gemini (cloud, good enough, costs ~$0.001)
    """
    
    def __init__(self):
        self.captions_dir = Path("uploads/captions")
        self.captions_dir.mkdir(parents=True, exist_ok=True)
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.0-flash-exp"
        
        # Try to load Vosk model (offline ASR)
        self.vosk_model = None
        self.use_vosk = False
        
        if VOSK_AVAILABLE:
            SetLogLevel(-1)  # Quiet mode
            model_path = Path("models/vosk-model-small-en-us-0.15")
            
            if model_path.exists():
                try:
                    self.vosk_model = Model(str(model_path))
                    self.use_vosk = True
                    print("✅ Vosk loaded - will use accurate offline timestamps")
                except Exception as e:
                    print(f"⚠️ Vosk load failed: {e}")
        
        if not self.use_vosk:
            print("📡 Using Gemini for captions (online, API-based)")
            print("   Note: Vosk is available but not loaded")
            print("   For offline processing, ensure Vosk model exists")
    
    def extract_audio(self, video_path: str) -> str:
        """Extract audio as 16kHz mono WAV"""
        audio_path = str(Path(video_path).with_suffix('.wav'))
        
        try:
            (
                ffmpeg
                .input(video_path)
                .output(audio_path, acodec='pcm_s16le', ar='16000', ac=1)
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            return audio_path
        except ffmpeg.Error as e:
            raise RuntimeError(f"Audio extraction failed: {e.stderr.decode() if e.stderr else str(e)}")
    
    def transcribe_with_vosk(self, audio_path: str) -> Dict:
        """
        Vosk transcription - ACCURATE timestamps from audio analysis
        NO API KEY NEEDED - completely offline
        """
        if not self.use_vosk:
            raise RuntimeError("Vosk not available")
        
        wf = wave.open(audio_path, "rb")
        if wf.getnchannels() != 1:
            wf.close()
            raise ValueError("Audio must be mono")
        
        rec = KaldiRecognizer(self.vosk_model, wf.getframerate())
        rec.SetWords(True)
        
        all_words = []
        
        # Process audio chunks
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                if 'result' in result:
                    for w in result['result']:
                        all_words.append({
                            "word": w['word'],
                            "start": round(w['start'], 2),
                            "end": round(w['end'], 2),
                            "confidence": round(w.get('conf', 1.0), 2)
                        })
        
        # Final result
        final = json.loads(rec.FinalResult())
        if 'result' in final:
            for w in final['result']:
                all_words.append({
                    "word": w['word'],
                    "start": round(w['start'], 2),
                    "end": round(w['end'], 2),
                    "confidence": round(w.get('conf', 1.0), 2)
                })
        
        wf.close()
        
        return {
            "text": " ".join([w['word'] for w in all_words]),
            "words": all_words,
            "method": "vosk",
            "accuracy": "high"
        }
    
    def transcribe_with_gemini(self, audio_path: str) -> Dict:
        """
        Gemini transcription - ESTIMATED timestamps
        Uses your Gemini API key (you have this!)
        
        NOTE: Test this first! It might be good enough for your needs.
        """
        # Upload audio file
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        
        prompt = """Transcribe this audio with word-level timestamps in JSON:
{
  "text": "full transcription",
  "words": [
    {"word": "Hello", "start": 0.0, "end": 0.5},
    {"word": "world", "start": 0.5, "end": 1.0}
  ]
}

Provide the most accurate timestamps possible."""

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                {"parts": [{"inline_data": {"mime_type": "audio/wav", "data": audio_data}}]},
                {"parts": [{"text": prompt}]}
            ]
        )
        
        # Parse response
        text = response.text.strip()
        if text.startswith('```'):
            text = '\n'.join(text.split('\n')[1:-1])
        if text.startswith('json'):
            text = text[4:].strip()
        
        result = json.loads(text)
        result['method'] = 'gemini'
        result['accuracy'] = 'estimated'
        
        return result
    
    def get_video_duration(self, video_path: str) -> float:
        """Get video duration"""
        try:
            probe = ffmpeg.probe(video_path)
            return float(probe['streams'][0]['duration'])
        except:
            return 30.0
    
    def generate_caption_file(self, clip_id: int, video_path: str) -> str:
        """
        Main pipeline: Extract audio → Transcribe → Save
        
        Automatically chooses best method:
        1. Try Vosk (if available) - offline, accurate
        2. Fallback to Gemini - online, good enough
        """
        audio_path = None
        
        try:
            duration = self.get_video_duration(video_path)
            audio_path = self.extract_audio(video_path)
            
            # Try Vosk first (best quality)
            if self.use_vosk:
                try:
                    print("🎯 Using Vosk (offline, accurate)...")
                    transcription = self.transcribe_with_vosk(audio_path)
                except Exception as e:
                    print(f"⚠️ Vosk failed: {e}, trying Gemini...")
                    transcription = self.transcribe_with_gemini(audio_path)
            else:
                # Use Gemini (still works!)
                print("📡 Using Gemini (online, estimated timestamps)...")
                transcription = self.transcribe_with_gemini(audio_path)
            
            # Save
            caption_data = {
                "words": transcription['words'],
                "full_text": transcription['text'],
                "duration": duration,
                "method": transcription['method'],
                "accuracy": transcription['accuracy']
            }
            
            caption_file = self.captions_dir / f"clip_{clip_id}_captions.json"
            with open(caption_file, 'w', encoding='utf-8') as f:
                json.dump(caption_data, f, indent=2, ensure_ascii=False)
            
            # Cleanup
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            
            print(f"✅ Captions saved: {caption_file}")
            print(f"   Method: {transcription['method']}")
            print(f"   Words: {len(transcription['words'])}")
            
            return str(caption_file)
            
        except Exception as e:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            raise RuntimeError(f"Caption generation failed: {str(e)}")


if __name__ == "__main__":
    gen = CaptionGenerator()
    print(f"\nStatus: {'Vosk available' if gen.use_vosk else 'Gemini only'}")
    print(f"API Keys needed: Gemini only (Vosk is offline)")
