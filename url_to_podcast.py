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
import requests
from bs4 import BeautifulSoup

try:
    import kokoro_onnx
except ImportError:
    print("Error: kokoro_onnx not found. Install with: pip install -r requirements.txt")
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
    """Fetch article content and title from a URL."""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = soup.find('h1').get_text()
        
        paragraphs = soup.find_all('p')
        text = '\n'.join([p.get_text() for p in paragraphs])
        
        return {"title": title, "text": text}
    except Exception as e:
        print(f"Error fetching article: {e}")
        return None

def clean_text_for_tts(text):
    """Clean and prepare text for TTS"""
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def update_podcast_feed(title, mp3_url, description):
    """Update the podcast.xml file with a new episode."""
    tree = ET.parse('docs/podcast.xml')
    root = tree.getroot()
    channel = root.find('channel')
    
    item = ET.SubElement(channel, 'item')
    ET.SubElement(item, 'title').text = title
    ET.SubElement(item, 'description').text = description
    ET.SubElement(item, 'pubDate').text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
    ET.SubElement(item, 'enclosure', {'url': mp3_url, 'type': 'audio/mpeg', 'length': '0'}) # Length is placeholder
    
    ET.indent(tree, space="  ", level=0)
    tree.write('docs/podcast.xml', encoding='utf-8', xml_declaration=True)

def update_index_html(title, mp3_url, description):
    """Update the index.html file with a new episode."""
    with open('docs/index.html', 'r+') as f:
        soup = BeautifulSoup(f, 'html.parser')
        episodes_div = soup.find(id='episodes')
        
        new_episode_div = soup.new_tag('div', **{'class': 'episode'})
        
        title_tag = soup.new_tag('h2')
        title_tag.string = title
        new_episode_div.append(title_tag)
        
        desc_tag = soup.new_tag('p')
        desc_tag.string = description
        new_episode_div.append(desc_tag)
        
        audio_tag = soup.new_tag('audio', controls=True)
        source_tag = soup.new_tag('source', src=mp3_url, type='audio/mpeg')
        audio_tag.append(source_tag)
        new_episode_div.append(audio_tag)
        
        episodes_div.insert(0, new_episode_div)
        
        f.seek(0)
        f.write(str(soup.prettify()))
        f.truncate()

def main():
    parser = argparse.ArgumentParser(description="Convert an article from a URL to an MP3 and update the podcast feed.")
    parser.add_argument("url", help="The URL of the article to convert.")
    parser.add_argument("--voice", default="af_bella", help="The voice to use for the TTS conversion (e.g., af_bella, am_santa).")
    args = parser.parse_args()

    if not download_model_files():
        print("Failed to download required model files")
        return

    article_data = fetch_article(args.url)
    if not article_data or not article_data['title'] or not article_data['text']:
        print("Failed to fetch or parse article data. The scraper might need adjustments for this website.")
        return

    title = article_data['title']
    text = article_data['text']
    
    clean_content = clean_text_for_tts(text)
    
    print(f"Processing '{title}'...")
    
    model_path = "kokoro-v1.0.onnx"
    voices_path = "voices-v1.0.bin"
    
    print("Initializing Kokoro TTS...")
    tts = kokoro_onnx.Kokoro(model_path=model_path, voices_path=voices_path)
    
    # --- Create Intro Sequence ---
    print("Generating intro...")
    
    intro_music = AudioSegment.from_mp3("assets/intro_music.mp3")

    intro_text = f"This is Dean's personal articles podcast. In this episode we're reading: {title}"
    intro_voiceover_audio = tts.create(intro_text, voice=args.voice)
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_wav_path = temp_file.name
    sf.write(temp_wav_path, intro_voiceover_audio[0], 24000)
    intro_voiceover = AudioSegment.from_wav(temp_wav_path)
    os.unlink(temp_wav_path)

    # --- Ducking Logic ---
    # The voiceover will start 1 second into the music.
    vo_start_in_music = 1000  # ms

    # 1. Split the music
    music_before = intro_music[:vo_start_in_music]
    
    vo_duration = len(intro_voiceover)
    music_during = intro_music[vo_start_in_music : vo_start_in_music + vo_duration]
    
    music_after = intro_music[vo_start_in_music + vo_duration:]

    # 2. Lower volume of the middle part (ducking)
    # Reducing by 8 decibels.
    quieter_during = music_during - 8
    
    # 3. Overlay the voiceover on the quieter part
    # If the voiceover is longer than the music segment, pydub handles it gracefully.
    overlayed_part = quieter_during.overlay(intro_voiceover)
    
    # 4. Stitch it all back together
    ducked_music = music_before + overlayed_part + music_after

    # 5. Add initial silence before the music starts
    final_intro = AudioSegment.silent(duration=1000) + ducked_music

    # --- Generate Main Article Audio ---
    print(f"Generating audio for article content with Kokoro TTS using voice: {args.voice}...")
    article_audio_data = tts.create(clean_content, voice=args.voice)
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_wav_path = temp_file.name
    sf.write(temp_wav_path, article_audio_data[0], 24000)
    article_audio = AudioSegment.from_wav(temp_wav_path)
    os.unlink(temp_wav_path)

    # --- Combine Intro and Article Audio ---
    final_audio = final_intro + AudioSegment.silent(duration=2000) + article_audio

    # --- Save Final MP3 ---
    safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '', title.lower().replace(' ', '-'))
    output_filename = f"{safe_filename}_{args.voice}.mp3"
    output_path = Path("docs/episodes") / output_filename
    
    print(f"Saving final audio to {output_path}...")
    final_audio.export(str(output_path), format="mp3", bitrate="192k")
    
    mp3_url = f"https://deanputney.github.io/read-articles/episodes/{output_filename}"
    description = f"An audio version of the article: {title}"
    
    print("Updating podcast feed...")
    update_podcast_feed(title, mp3_url, description)
    
    print("Updating website...")
    update_index_html(title, mp3_url, description)
    
    print("Done.")

if __name__ == "__main__":
    main()