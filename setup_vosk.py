"""
Setup script to download Vosk model for accurate caption timestamps

Run this once to enable high-quality caption generation
"""
import os
import urllib.request
import zipfile
from pathlib import Path


def download_vosk_model():
    """Download and extract Vosk English model"""
    
    model_url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    models_dir = Path("models")
    model_dir = models_dir / "vosk-model-small-en-us-0.15"
    
    # Check if already exists
    if model_dir.exists():
        print("✅ Vosk model already downloaded!")
        return
    
    print("📥 Downloading Vosk model (40MB)...")
    print(f"   URL: {model_url}")
    
    models_dir.mkdir(exist_ok=True)
    zip_path = models_dir / "vosk-model.zip"
    
    try:
        # Download with progress
        def show_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size)
            print(f"\r   Progress: {percent:.1f}%", end='')
        
        urllib.request.urlretrieve(model_url, zip_path, show_progress)
        print("\n✅ Download complete!")
        
        # Extract
        print("📦 Extracting model...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(models_dir)
        
        # Cleanup
        os.remove(zip_path)
        
        print(f"✅ Vosk model ready at: {model_dir}")
        print("\n🎉 Setup complete! Restart your server to use Vosk.")
        
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        print("\nManual installation:")
        print(f"1. Download: {model_url}")
        print(f"2. Extract to: {models_dir}")
        print(f"3. Folder should be: {model_dir}")


if __name__ == "__main__":
    download_vosk_model()
