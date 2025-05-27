#!/usr/bin/env python3
"""
Script to convert markdown articles to MP3 using Kokoro TTS
"""

import os
import re
import sys
import argparse
from pathlib import Path
import urllib.request
import numpy as np
import soundfile as sf
from pydub import AudioSegment
import tempfile

try:
    import kokoro_onnx
except ImportError:
    print("Error: kokoro_onnx not found. Install with: pip install kokoro-onnx")
    exit(1)

def download_model_files():
    """Download required model files if they don't exist"""
    model_path = "kokoro-v1.0.onnx"
    voices_path = "voices-v1.0.bin"
    
    base_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
    
    files_to_download = [
        (model_path, base_url + model_path),
        (voices_path, base_url + voices_path)
    ]
    
    for file_path, url in files_to_download:
        if not Path(file_path).exists():
            print(f"Downloading {file_path}...")
            try:
                urllib.request.urlretrieve(url, file_path)
                print(f"Downloaded {file_path}")
            except Exception as e:
                print(f"Error downloading {file_path}: {e}")
                return False
        else:
            print(f"{file_path} already exists")
    
    return True

def clean_text_for_tts(text):
    """Clean and prepare text for TTS"""
    # Remove markdown formatting
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)      # Italic
    text = re.sub(r'`(.+?)`', r'\1', text)        # Code
    text = re.sub(r'#+ ', '', text)               # Headers
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Clean up whitespace
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def save_audio_as_mp3(audio_data, sample_rate, output_path):
    """Save audio data as MP3 using soundfile and pydub"""
    # Create a temporary WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_wav_path = temp_file.name
    
    try:
        # Save as WAV first using soundfile
        sf.write(temp_wav_path, audio_data, sample_rate)
        
        # Convert WAV to MP3 using pydub
        print(f"Converting to MP3...")
        audio_segment = AudioSegment.from_wav(temp_wav_path)
        audio_segment.export(output_path, format="mp3", bitrate="192k")
        
    finally:
        # Clean up temporary file
        if Path(temp_wav_path).exists():
            os.unlink(temp_wav_path)

def main():
    """Main function to process articles to audio"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert markdown articles to MP3 using Kokoro TTS')
    parser.add_argument('--article', '-a', help='Path to markdown article file')
    parser.add_argument('--voice', '-v', default='am_santa', help='Voice to use (e.g., am_santa, af_bella)')
    parser.add_argument('--all', action='store_true', help='Process all markdown files in the current directory')
    args = parser.parse_args()

    # Download model files if needed
    if not download_model_files():
        print("Failed to download required model files")
        return False

    # Initialize Kokoro TTS with required paths
    model_path = "kokoro-v1.0.onnx"
    voices_path = "voices-v1.0.bin"
    
    print("Initializing Kokoro TTS...")
    tts = kokoro_onnx.Kokoro(model_path=model_path, voices_path=voices_path)
    
    # Collect the files to process
    article_files = []
    
    if args.all:
        # Process all markdown files in the current directory
        article_files = list(Path('.').glob('*.md'))
        if not article_files:
            print("No markdown files found in the current directory")
            return False
    elif args.article:
        # Process a specific article file
        article_path = Path(args.article)
        if not article_path.exists():
            print(f"Error: {article_path} not found")
            return False
        article_files = [article_path]
    else:
        # No article specified, check for default one
        article_path = Path("What Are People Still Doing on X? - The Atlantic.md")
        if article_path.exists():
            article_files = [article_path]
        else:
            print("No article specified and no default article found")
            print("Use --article to specify an article file or --all to process all markdown files")
            return False
    
    success_count = 0
    
    # Process each article
    for article_path in article_files:
        print(f"\nProcessing article: {article_path}")
        
        # Read the article
        with open(article_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Clean the text
        clean_content = clean_text_for_tts(content)
        
        print(f"Processing {len(clean_content)} characters...")
        
        # Generate audio
        print(f"Generating audio with Kokoro TTS using voice: {args.voice}...")
        try:
            audio = tts.create(clean_content, voice=args.voice)
            
            # Create a safe filename from the article path
            base_name = article_path.stem.replace(' ', '_').lower()
            output_path = f"{base_name}_{args.voice}.mp3"
            sample_rate = 24000  # Kokoro TTS uses 24kHz sample rate
            
            print(f"Saving audio to {output_path}...")
            save_audio_as_mp3(audio[0], sample_rate, output_path)
            
            duration_seconds = len(audio[0]) / sample_rate
            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            
            print(f"Audio saved as {output_path}")
            print(f"Duration: {minutes}:{seconds:02d}")
            success_count += 1
            
        except Exception as e:
            print(f"Error generating audio for {article_path}: {e}")
    
    print(f"\nSuccessfully processed {success_count} out of {len(article_files)} articles")
    return success_count > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)