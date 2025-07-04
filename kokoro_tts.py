#!/usr/bin/env python3
"""
Script to convert an article from a URL to MP3 using Kokoro TTS,
and update the podcast feed.
"""

import os
import re
from pathlib import Path
import urllib.request
import numpy as np
import soundfile as sf
from pydub import AudioSegment
import tempfile
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime
from gemini import Gemini

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

def fetch_article(url):
    """Fetch article content from a URL using Gemini."""
    gemini = Gemini()
    prompt = f"Please extract the title and main text content of the article at this URL: {url}. Return the result as a single JSON object with two keys: 'title' and 'text'."
    response = gemini.web_fetch(prompt)
    return response

def clean_text_for_tts(text):
    """Clean and prepare text for TTS"""
    # Remove markdown formatting
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)      # Italic
    text = re.sub(r'`(.+?)`', r'\1', text)        # Code
    text = re.sub(r'#+ ', '', text)               # Headers
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Clean up whitespace
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def save_audio_as_mp3(audio_data, sample_rate, output_path):
    """Save audio data as MP3 using soundfile and pydub"""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_wav_path = temp_file.name
    
    try:
        sf.write(temp_wav_path, audio_data, sample_rate)
        print(f"Converting to MP3...")
        audio_segment = AudioSegment.from_wav(temp_wav_path)
        audio_segment.export(output_path, format="mp3", bitrate="192k")
    finally:
        if Path(temp_wav_path).exists():
            os.unlink(temp_wav_path)

def update_podcast_feed(title, mp3_url, description):
    """Update the podcast.xml file with a new episode."""
    tree = ET.parse('docs/podcast.xml')
    root = tree.getroot()
    channel = root.find('channel')
    
    item = ET.SubElement(channel, 'item')
    ET.SubElement(item, 'title').text = title
    ET.SubElement(item, 'description').text = description
    ET.SubElement(item, 'pubDate').text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
    ET.SubElement(item, 'enclosure', {'url': mp3_url, 'type': 'audio/mpeg', 'length': '0'})
    
    tree.write('docs/podcast.xml')

def update_index_html(title, mp3_url, description):
    """Update the index.html file with a new episode."""
    with open('docs/index.html', 'r+') as f:
        content = f.read()
        f.seek(0)
        new_episode = f"""
<div class="episode">
    <h2>{title}</h2>
    <p>{description}</p>
    <audio controls>
        <source src="{mp3_url}" type="audio/mpeg">
    </audio>
</div>
"""
        content = content.replace('<div id="episodes"></div>', f'<div id="episodes">{new_episode}</div>')
        f.write(content)

def main():
    parser = argparse.ArgumentParser(description="Convert an article from a URL to an MP3 and update the podcast feed.")
    parser.add_argument("url", help="The URL of the article to convert.")
    parser.add_argument("voice", help="The voice to use for the TTS conversion (e.g., am_santa).")
    args = parser.parse_args()

    if not download_model_files():
        print("Failed to download required model files")
        return

    article_data = fetch_article(args.url)
    if not article_data or 'title' not in article_data or 'text' not in article_data:
        print("Failed to fetch or parse article data.")
        return

    title = article_data['title']
    text = article_data['text']
    
    clean_content = clean_text_for_tts(text)
    
    print(f"Processing '{title}'...")
    
    model_path = "kokoro-v1.0.onnx"
    voices_path = "voices-v1.0.bin"
    
    print("Initializing Kokoro TTS...")
    tts = kokoro_onnx.Kokoro(model_path=model_path, voices_path=voices_path)
    
    print(f"Generating audio with Kokoro TTS using voice: {args.voice}...")
    audio = tts.create(clean_content, voice=args.voice)
    
    output_filename = f"{title.lower().replace(' ', '-')}_{args.voice}.mp3"
    output_path = Path("docs/episodes") / output_filename
    
    print(f"Saving audio to {output_path}...")
    save_audio_as_mp3(audio[0], 24000, str(output_path))
    
    mp3_url = f"https://deanputney.github.io/read-articles/episodes/{output_filename}"
    
    print("Updating podcast feed...")
    update_podcast_feed(title, mp3_url, f"An audio version of the article: {title}")
    
    print("Updating website...")
    update_index_html(title, mp3_url, f"An audio version of the article: {title}")
    
    print("Done.")

if __name__ == "__main__":
    main()