"""
Caption Generator Service using Vosk + Gemini hybrid approach
- Vosk: Accurate word-level timestamps (offline, fast)
- Gemini: Text correction and punctuation (optional enhancement)
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

# Configure Gemini for text enhancement
genai.configure(api_key=GEMINI_API_KEY)


class CaptionGenerator:
    def __init__(self):
        """
        Initialize caption generator with Vosk for accurate timestamps
        Falls back to Gemini-only mode if Vosk model not found
        """
        self.captions_dir = Path("uploads/captions")
        self.captions_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Vosk model
        self.vosk_model = None
        self.use_vosk = False
        
        if VOSK_AVAILABLE:
            # Suppress Vosk logs
            SetLogLevel(-1)
            
            # Try to load Vosk model
            model_path = Path("models/vosk-model-small-en-us-0.15")
            if model_path.exists():
                try:
                    self.vosk_model = Model(str(model_path))
                    self.use_vosk = True
                    print("✅ Caption Generator initialized with Vosk (accurate timestamps)")
                except Exception as e:
                    print(f"⚠️ Vosk model load failed: {e}")
            else:
                print(f"⚠️ Vosk model not found at {model_path}")
                print("Download from: https://alphacephei.com/vosk/models")
        
        # Gemini for text enhancement
        self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        if not self.use_vosk:
            print("⚠️ Using Gemini-only mode (less accurate timestamps)")
            print("For best results, download Vosk model to models/ directory")
    
    def extract_audio(self, video_path: str) -> str:
        """
        Extract audio from video file using FFmpeg
        
        Args:
            video_path: Path to video file
            
        Returns:
            Path to extracted audio WAV file
        """
        audio_path = str(Path(video_path).with_suffix('.wav'))
        
        try:
            print(f"Extracting audio from {video_path}...")
            (
                ffmpeg
                .input(video_path)
                .output(
                    audio_path,
                    acodec='pcm_s16le',  # PCM 16-bit
                    ar='16000',          # 16kHz sample rate
                    ac=1                 # Mono audio
                )
                .overwrite_output()
                .run(quiet=True, capture_stdout=True, capture_stderr=True)
            )
            print(f"Audio extracted to {audio_path}")
            return audio_path
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            print(f"FFmpeg error: {error_msg}")
            raise Exception(f"Audio extraction failed: {error_msg}")
    
    def transcribe_with_vosk(self, audio_path: str) -> Dict:
        """
        Transcribe audio using Vosk with REAL word-level timestamps
        
        Args:
            audio_path: Path to WAV audio file
            
        Returns:
            Dict with accurate transcription and word-level timestamps
        """
        if not self.use_vosk:
            raise RuntimeError("Vosk not available. Use transcribe_with_gemini() instead")
        
        try:
            print("Transcribing with Vosk (offline, accurate timestamps)...")
            
            # Open WAV file
            wf = wave.open(audio_path, "rb")
            
            # Validate audio format
            if wf.getnchannels() != 1:
                wf.close()
                raise ValueError("Audio must be mono channel")
            if wf.getsampwidth() != 2:
                wf.close()
                raise ValueError("Audio must be 16-bit PCM")
            if wf.getframerate() not in [8000, 16000, 32000, 44100, 48000]:
                wf.close()
                raise ValueError(f"Sample rate {wf.getframerate()} not supported")
            
            # Create recognizer
            rec = KaldiRecognizer(self.vosk_model, wf.getframerate())
            rec.SetWords(True)  # Enable word-level timestamps
            
            # Process audio in chunks
            all_words = []
            full_text = []
            
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if 'result' in result:
                        for word_info in result['result']:
                            all_words.append({
                                "word": word_info['word'],
                                "start": round(word_info['start'], 2),
                                "end": round(word_info['end'], 2),
                                "confidence": round(word_info.get('conf', 1.0), 2)
                            })
                            full_text.append(word_info['word'])
            
            # Get final result
            final_result = json.loads(rec.FinalResult())
            if 'result' in final_result:
                for word_info in final_result['result']:
                    all_words.append({
                        "word": word_info['word'],
                        "start": round(word_info['start'], 2),
                        "end": round(word_info['end'], 2),
                        "confidence": round(word_info.get('conf', 1.0), 2)
                    })
                    full_text.append(word_info['word'])
            
            wf.close()
            
            transcription = {
                "text": " ".join(full_text),
                "words": all_words,
                "method": "vosk",
                "accuracy": "high"
            }
            
            print(f"✅ Vosk transcription: {len(all_words)} words with accurate timestamps")
            return transcription
            
        except Exception as e:
            print(f"Vosk transcription error: {str(e)}")
            raise RuntimeError(f"Vosk transcription failed: {str(e)}")
    
    def enhance_with_gemini(self, vosk_text: str) -> str:
        """
        Optional: Enhance Vosk transcription with proper punctuation using Gemini
        
        Args:
            vosk_text: Raw text from Vosk (no punctuation)
            
        Returns:
            Enhanced text with punctuation and capitalization
        """
        try:
            prompt = f"""Add proper punctuation and capitalization to this transcription.
Keep the EXACT same words, just add punctuation marks and fix capitalization.
Do not add, remove, or change any words.

Transcription: {vosk_text}

Return only the corrected text, nothing else."""

            response = self.gemini_model.generate_content(prompt)
            enhanced_text = response.text.strip()
            
            print(f"✅ Text enhanced with Gemini")
            return enhanced_text
            
        except Exception as e:
            print(f"⚠️ Gemini enhancement failed: {e}. Using original text.")
            return vosk_text
        """
        Transcribe audio using Gemini AI with timestamps
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict with transcription and word-level timestamps
        """
        try:
            print(f"Uploading audio to Gemini AI...")
            
            # Upload audio file to Gemini
            audio_file = genai.upload_file(audio_path)
            
            prompt = """
            Transcribe this audio and provide word-level timestamps.
            
            Return ONLY a JSON response in this exact format:
            {
              "text": "full transcription here",
              "words": [
                {"word": "Hello", "start": 0.0, "end": 0.5},
                {"word": "world", "start": 0.5, "end": 1.0}
              ]
            }
            
            Important rules:
            1. Provide accurate timestamps for each word in seconds
            2. Split on spaces - each word should be separate
            3. Include punctuation with the word it belongs to
            4. Make timestamps sequential and non-overlapping
            5. Estimate timing if exact timing is difficult - spread words evenly across their segment
            """
            
            print("Transcribing with Gemini AI...")
            response = self.model.generate_content([audio_file, prompt])
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Clean up markdown code blocks if present
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else lines[1]
            if response_text.startswith('json'):
                response_text = response_text[4:].strip()
            
            transcription = json.loads(response_text)
            
            print(f"Transcription complete: {len(transcription.get('words', []))} words")
            return transcription
            
        except Exception as e:
            print(f"Gemini transcription error: {str(e)}")
            raise Exception(f"Transcription failed: {str(e)}")
    
    def fallback_word_splitting(self, text: str, duration: float) -> List[Dict]:
        """
        Fallback method to split text into words with estimated timestamps
        
        Args:
            text: Full transcription text
            duration: Total audio duration in seconds
            
        Returns:
            List of word dictionaries with timestamps
        """
        words_list = text.split()
        word_duration = duration / len(words_list) if words_list else 0
        
        words = []
        for i, word in enumerate(words_list):
            start_time = i * word_duration
            end_time = start_time + word_duration
            
            words.append({
                "word": word,
                "start": round(start_time, 2),
                "end": round(end_time, 2)
            })
        
        return words
    
    def get_video_duration(self, video_path: str) -> float:
        """
        Get video duration using FFmpeg
        
        Args:
            video_path: Path to video file
            
        Returns:
            Duration in seconds
        """
        try:
            probe = ffmpeg.probe(video_path)
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e:
            print(f"Error getting video duration: {e}")
            return 30.0  # Default fallback
    
    def save_captions(self, clip_id: int, captions_data: Dict) -> str:
        """
        Save captions to JSON file
        
        Args:
            clip_id: Unique clip identifier
            captions_data: Caption data to save
            
        Returns:
            Path to saved caption file
        """
        caption_file = self.captions_dir / f"clip_{clip_id}_captions.json"
        
        with open(caption_file, 'w', encoding='utf-8') as f:
            json.dump(captions_data, f, indent=2, ensure_ascii=False)
        
        print(f"Captions saved to {caption_file}")
        return str(caption_file)
    
    def generate_caption_file(self, clip_id: int, video_path: str) -> str:
        """
        Full pipeline: extract audio, transcribe, and save captions
        
        Args:
            clip_id: Unique clip identifier
            video_path: Path to video file
            
        Returns:
            Path to caption file
        """
        try:
            # Get video duration
            duration = self.get_video_duration(video_path)
            print(f"Video duration: {duration}s")
            
            # Extract audio
            audio_path = self.extract_audio(video_path)
            
            # Transcribe with Gemini
            transcription = self.transcribe_with_gemini(audio_path)
            
            # Validate word timestamps
            words = transcription.get('words', [])
            if not words:
                # Fallback to text splitting
                print("No word timestamps found, using fallback splitting")
                full_text = transcription.get('text', '')
                words = self.fallback_word_splitting(full_text, duration)
                transcription['words'] = words
            
            # Save to file
            caption_path = self.save_captions(clip_id, {
                "words": words,
                "full_text": transcription.get('text', ''),
                "duration": duration
            })
            
            # Cleanup audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"Cleaned up temporary audio file: {audio_path}")
            
            return caption_path
            
        except Exception as e:
            # Cleanup on error
            audio_path = str(Path(video_path).with_suffix('.wav'))
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            raise Exception(f"Caption generation failed: {str(e)}")


# For testing
if __name__ == "__main__":
    generator = CaptionGenerator()
    print("Caption Generator ready!")
