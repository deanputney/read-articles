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
import csv

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
    ET.SubElement(item, 'enclosure', {'url': mp3_url, 'type': 'audio/mpeg', 'length': '0'}) # Length is placeholder
    
    ET.indent(tree, space="  ", level=0)
    tree.write('docs/podcast.xml', encoding='utf-8', xml_declaration=True)

def update_index_html(title, mp3_url, description, article_url):
    """Update the index.html file with a new episode."""
    with open('docs/index.html', 'r+') as f:
        soup = BeautifulSoup(f, 'html.parser')
        episodes_div = soup.find(id='episodes')
        
        new_episode_div = soup.new_tag('div', **{'class': 'episode'})
        
        title_tag = soup.new_tag('h2')
        link_tag = soup.new_tag('a', href=article_url)
        link_tag.string = title
        title_tag.append(link_tag)
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

def update_articles_csv(title, article_url, mp3_url, voice):
    """Update the articles.csv file with new episode details."""
    csv_file = 'articles.csv'
    file_exists = os.path.isfile(csv_file)
    
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Title', 'Article URL', 'MP3 URL', 'Voice', 'Date Added'])
        writer.writerow([title, article_url, mp3_url, voice, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

def regenerate_feed_and_html_from_mp3s():
    """Regenerate podcast.xml and index.html from existing MP3s and articles.csv."""
    print("Resetting podcast.xml and index.html...")
    # Reset podcast.xml
    with open('docs/podcast.xml', 'w') as f:
        f.write("""<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<rss version=\"2.0\" xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\">\n  <channel>\n    <title>Read Articles Podcast</title>\n    <link>https://deanputney.github.io/read-articles/</link>\n    <description>An AI-powered podcast that converts interesting articles into high-quality audio.</description>\n    <language>en-us</language>\n  </channel>\n</rss>""")
    
    # Reset index.html
    with open('docs/index.html', 'w') as f:
        f.write("""<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Read Articles Podcast</title>\n    <style>\n        body {\n            font-family: sans-serif;\n            margin: 40px auto;\n            max-width: 800px;\n            line-height: 1.6;\n            font-size: 18px;\n            color: #333;\n            background-color: #f9f9f9;\n        }\n        h1, h2 {\n            line-height: 1.2;\n        }\n        a {\n            color: #007bff;\n        }\n        .episode {\n            border-bottom: 1px solid #ddd;\n            padding-bottom: 20px;\n            margin-bottom: 20px;\n        }\n    </style>\n</head>\n<body>\n    <h1>Read Articles Podcast</h1>\n    <p>An AI-powered podcast that converts interesting articles into high-quality audio. Subscribe with this <a href=\"podcast.xml\">RSS feed</a>.</p>\n    <div id=\"episodes\"></div>\n</body>\n</html>""")

    # Read articles from CSV
    articles_data = []
    csv_file = 'articles.csv'
    if os.path.exists(csv_file):
        with open(csv_file, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader) # Skip header
            for row in reader:
                articles_data.append({'Title': row[0], 'Article URL': row[1], 'MP3 URL': row[2], 'Voice': row[3], 'Date Added': row[4]})
    
    # Re-add articles to feed and HTML in reverse order (newest first)
    for article in reversed(articles_data):
        title = article['Title']
        mp3_url = article['MP3 URL']
        article_url = article['Article URL']
        description = f"An audio version of the article: {title}"
        update_podcast_feed(title, mp3_url, description)
        update_index_html(title, mp3_url, description, article_url)
    
    print("Podcast feed and HTML regenerated successfully.")

def main():
    parser = argparse.ArgumentParser(description="Convert an article from a URL to an MP3 and update the podcast feed, or regenerate the feed from existing MP3s.")
    parser.add_argument("url", nargs='?', help="The URL of the article to convert. Omit to regenerate feed.")
    parser.add_argument("--voice", default="af_bella", help="The voice to use for the TTS conversion (e.g., af_bella, am_santa).")
    parser.add_argument("--reset", action="store_true", help="Reset and regenerate podcast.xml and index.html from existing MP3s and articles.csv.")
    args = parser.parse_args()

    if args.reset:
        regenerate_feed_and_html_from_mp3s()
        return

    if not args.url:
        parser.error("The --reset flag must be used, or a URL must be provided.")

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
    update_index_html(title, mp3_url, description, args.url)
    
    print("Updating articles CSV...")
    update_articles_csv(title, args.url, mp3_url, args.voice)
    
    print("Done.")

if __name__ == "__main__":
    main()
