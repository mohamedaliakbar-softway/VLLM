"""
IMPROVED Caption Generator Service
Uses Vosk for accurate word-level timestamps + Gemini for text enhancement

Key Improvements:
1. REAL word-level timestamps from Vosk (not estimated)
2. Confidence scores for each word
3. Proper audio analysis
4. Optional Gemini enhancement for punctuation
5. Graceful fallback to Gemini-only if Vosk unavailable
"""
import os
import json
import ffmpeg
import wave
from pathlib import Path
from typing import Dict, List, Optional
import google.generativeai as genai
from config import GEMINI_API_KEY

try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("WARNING: Vosk not available. Install with: pip install vosk")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


class CaptionGenerator:
    """
    Hybrid caption generator using Vosk + Gemini
    - Vosk: Accurate offline speech recognition with real timestamps
    - Gemini: Text enhancement (punctuation, capitalization)
    """
    
    def __init__(self):
        """Initialize with Vosk model if available, otherwise Gemini-only"""
        self.captions_dir = Path("uploads/captions")
        self.captions_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Vosk
        self.vosk_model = None
        self.use_vosk = False
        
        if VOSK_AVAILABLE:
            SetLogLevel(-1)  # Suppress Vosk logs
            model_path = Path("models/vosk-model-small-en-us-0.15")
            
            if model_path.exists():
                try:
                    self.vosk_model = Model(str(model_path))
                    self.use_vosk = True
                    print("✅ Vosk loaded - ACCURATE timestamps enabled")
                except Exception as e:
                    print(f"⚠️ Vosk load failed: {e}")
            else:
                print("⚠️ Vosk model not found")
                print(f"   Download: https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
                print(f"   Extract to: {model_path}")
        
        # Gemini for enhancement/fallback
        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        if not self.use_vosk:
            print("⚠️ FALLBACK MODE: Using Gemini (timestamps are ESTIMATES)")
    
    def extract_audio(self, video_path: str) -> str:
        """
        Extract audio from video as 16kHz mono WAV (required for Vosk)
        
        Args:
            video_path: Path to video file
            
        Returns:
            Path to extracted WAV file
        """
        audio_path = str(Path(video_path).with_suffix('.wav'))
        
        try:
            print(f"Extracting audio from {video_path}...")
            (
                ffmpeg
                .input(video_path)
                .output(
                    audio_path,
                    acodec='pcm_s16le',  # 16-bit PCM
                    ar='16000',          # 16kHz (Vosk compatible)
                    ac=1                 # Mono
                )
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            print(f"✅ Audio extracted: {audio_path}")
            return audio_path
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            raise RuntimeError(f"Audio extraction failed: {error_msg}")
    
    def transcribe_with_vosk(self, audio_path: str) -> Dict:
        """
        Transcribe with Vosk - ACCURATE word-level timestamps
        
        This is the REAL solution for live captions.
        Vosk analyzes audio waveforms and provides precise timing.
        
        Args:
            audio_path: Path to 16kHz mono WAV file
            
        Returns:
            Dict with text, words (with start/end/confidence), method, accuracy
        """
        if not self.use_vosk:
            raise RuntimeError("Vosk not initialized")
        
        try:
            print("🎙️ Transcribing with Vosk (accurate timestamps)...")
            
            wf = wave.open(audio_path, "rb")
            
            # Validate audio format
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                wf.close()
                raise ValueError("Audio must be 16-bit mono WAV")
            
            # Create recognizer with word timestamps enabled
            rec = KaldiRecognizer(self.vosk_model, wf.getframerate())
            rec.SetWords(True)
            
            all_words = []
            
            # Process audio in chunks
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                
                if rec.AcceptWaveform(data):
                    self._process_vosk_result(rec.Result(), all_words)
            
            # Get final partial result
            self._process_vosk_result(rec.FinalResult(), all_words)
            wf.close()
            
            full_text = " ".join([w['word'] for w in all_words])
            
            print(f"✅ Vosk: {len(all_words)} words with REAL timestamps")
            
            return {
                "text": full_text,
                "words": all_words,
                "method": "vosk",
                "accuracy": "high"
            }
            
        except Exception as e:
            raise RuntimeError(f"Vosk transcription failed: {str(e)}")
    
    def _process_vosk_result(self, result_json: str, words_list: List[Dict]):
        """Helper to extract word data from Vosk result"""
        result = json.loads(result_json)
        if 'result' in result:
            for word_info in result['result']:
                words_list.append({
                    "word": word_info['word'],
                    "start": round(word_info['start'], 2),
                    "end": round(word_info['end'], 2),
                    "confidence": round(word_info.get('conf', 1.0), 2)
                })
    
    def enhance_with_gemini(self, raw_text: str) -> str:
        """
        Enhance Vosk output with punctuation/capitalization
        
        Vosk returns lowercase words without punctuation.
        Gemini adds proper formatting while keeping timing intact.
        
        Args:
            raw_text: Raw Vosk transcription
            
        Returns:
            Enhanced text with punctuation
        """
        try:
            prompt = f"""Add proper punctuation and capitalization to this transcription.
IMPORTANT: Keep the EXACT same words in the EXACT same order.
Only add punctuation marks (. , ! ? " ') and fix capitalization.

Raw text: {raw_text}

Return only the corrected text."""

            response = self.gemini_model.generate_content(prompt)
            enhanced = response.text.strip()
            
            print("✅ Text enhanced with punctuation")
            return enhanced
            
        except Exception as e:
            print(f"⚠️ Enhancement failed: {e}, using raw text")
            return raw_text
    
    def transcribe_with_gemini(self, audio_path: str) -> Dict:
        """
        Fallback: Gemini-only transcription (ESTIMATED timestamps)
        
        WARNING: Gemini is NOT an audio analysis model.
        It cannot provide accurate word-level timing.
        Use only when Vosk is unavailable.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict with text and ESTIMATED word timestamps
        """
        try:
            print("⚠️ Using Gemini fallback (timestamps are ESTIMATES)...")
            
            audio_file = genai.upload_file(audio_path)
            
            prompt = """Transcribe this audio with word-level timestamps in JSON format:
{
  "text": "full transcription",
  "words": [
    {"word": "Hello", "start": 0.0, "end": 0.5},
    {"word": "world", "start": 0.5, "end": 1.0}
  ]
}

Rules:
- One word per entry with estimated start/end times
- Sequential, non-overlapping timestamps
- Include punctuation with words"""

            response = self.gemini_model.generate_content([audio_file, prompt])
            
            # Clean response
            text = response.text.strip()
            if text.startswith('```'):
                text = '\n'.join(text.split('\n')[1:-1])
            if text.startswith('json'):
                text = text[4:].strip()
            
            result = json.loads(text)
            result['method'] = 'gemini'
            result['accuracy'] = 'estimated'
            
            print(f"⚠️ Gemini: {len(result.get('words', []))} words (ESTIMATED timing)")
            return result
            
        except Exception as e:
            raise RuntimeError(f"Gemini transcription failed: {str(e)}")
    
    def get_video_duration(self, video_path: str) -> float:
        """Get video duration via FFmpeg probe"""
        try:
            probe = ffmpeg.probe(video_path)
            return float(probe['streams'][0]['duration'])
        except Exception:
            return 30.0  # Fallback
    
    def generate_caption_file(self, clip_id: int, video_path: str, enhance: bool = True) -> str:
        """
        COMPLETE PIPELINE: Extract audio → Transcribe → Enhance → Save
        
        Args:
            clip_id: Clip identifier
            video_path: Path to video
            enhance: Use Gemini to add punctuation (recommended)
            
        Returns:
            Path to caption JSON file
        """
        audio_path = None
        
        try:
            duration = self.get_video_duration(video_path)
            print(f"📹 Video duration: {duration}s")
            
            # Extract audio
            audio_path = self.extract_audio(video_path)
            
            # Transcribe (Vosk preferred, Gemini fallback)
            if self.use_vosk:
                transcription = self.transcribe_with_vosk(audio_path)
                
                # Optional: Enhance with punctuation
                if enhance:
                    enhanced_text = self.enhance_with_gemini(transcription['text'])
                    transcription['text'] = enhanced_text
                    transcription['enhanced'] = True
            else:
                transcription = self.transcribe_with_gemini(audio_path)
                transcription['enhanced'] = False
            
            # Save captions
            caption_data = {
                "words": transcription['words'],
                "full_text": transcription['text'],
                "duration": duration,
                "method": transcription['method'],
                "accuracy": transcription['accuracy'],
                "enhanced": transcription.get('enhanced', False)
            }
            
            caption_file = self.captions_dir / f"clip_{clip_id}_captions.json"
            with open(caption_file, 'w', encoding='utf-8') as f:
                json.dump(caption_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Captions saved: {caption_file}")
            
            # Cleanup
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            
            return str(caption_file)
            
        except Exception as e:
            # Cleanup on error
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
            raise RuntimeError(f"Caption generation failed: {str(e)}")


# Test code
if __name__ == "__main__":
    gen = CaptionGenerator()
    print(f"\nVosk available: {gen.use_vosk}")
    print(f"Method: {'Vosk (accurate)' if gen.use_vosk else 'Gemini (estimated)'}")
