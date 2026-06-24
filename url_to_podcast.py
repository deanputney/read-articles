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
import subprocess

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

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

        # Title: prefer <h1>, then og:title, then <title>. Not every site
        # exposes an <h1>, so fall back instead of crashing.
        title = None
        h1 = soup.find('h1')
        if h1 and h1.get_text(strip=True):
            title = h1.get_text().strip()
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title['content'].strip()
        if not title and soup.title and soup.title.get_text(strip=True):
            title = soup.title.get_text().strip()
        if not title:
            print("Error fetching article: could not determine a title (no <h1>, og:title, or <title>).")
            return None

        paragraphs = soup.find_all('p')
        text = '\n'.join([p.get_text() for p in paragraphs])
        if not text.strip():
            print("Error fetching article: no <p> text content found on the page.")
            return None

        return {"title": title, "text": text}
    except Exception as e:
        print(f"Error fetching article: {e}")
        return None

def extract_pdf_content(pdf_path):
    """Extract text and title from a PDF file."""
    if PyPDF2 is None:
        print("Error: PyPDF2 not found. Install with: pip install PyPDF2")
        return None
    
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Extract title from PDF metadata or first page
            title = ""
            if reader.metadata and reader.metadata.title:
                title = reader.metadata.title
            else:
                # Try to get title from first few lines of first page
                if len(reader.pages) > 0:
                    first_page_text = reader.pages[0].extract_text()
                    lines = first_page_text.strip().split('\n')
                    # Use the first non-empty line as title
                    for line in lines[:5]:
                        if line.strip():
                            title = line.strip()
                            break
            
            if not title:
                title = Path(pdf_path).stem  # Use filename as fallback
            
            # Extract all text from all pages
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            return {"title": title, "text": text}
    except Exception as e:
        print(f"Error extracting PDF content: {e}")
        return None

def clean_text_for_tts(text):
    """Clean and prepare text for TTS"""
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def generate_summary(text, max_length=150):
    """Generate a summary using Gemini CLI"""
    try:
        # Clean the text first
        clean_text = clean_text_for_tts(text)
        
        # Prepare the prompt for Gemini
        prompt = f"Please provide a concise 1-2 sentence summary (max {max_length} characters) of this article that would be suitable for a podcast description:"
        
        # Call Gemini CLI
        result = subprocess.run(
            ['gemini', '-p', prompt],
            input=clean_text,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            summary = result.stdout.strip()
            # Truncate if too long
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            return summary
        else:
            print(f"Gemini CLI error: {result.stderr}")
            # Fallback to simple summary
            return f"An audio version of the article about {text[:50]}..."
            
    except subprocess.TimeoutExpired:
        print("Gemini CLI timed out, using fallback summary")
        return f"An audio version of the article about {text[:50]}..."
    except Exception as e:
        print(f"Error generating summary with Gemini CLI: {e}")
        return f"An audio version of the article about {text[:50]}..."

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

def update_podcast_feed(title, mp3_url, summary, article_url, published_date):
    """Update the podcast.xml file with a new episode."""
    tree = ET.parse('docs/podcast.xml')
    root = tree.getroot()
    channel = root.find('channel')
    
    item = ET.SubElement(channel, 'item')
    ET.SubElement(item, 'title').text = title
    ET.SubElement(item, 'description').text = f"{summary}\n\nOriginal article: {article_url}"
    
    # Parse the published date and format it for RSS
    try:
        pub_date = datetime.strptime(published_date, "%Y-%m-%d %H:%M:%S")
        ET.SubElement(item, 'pubDate').text = pub_date.strftime("%a, %d %b %Y %H:%M:%S +0000")
    except ValueError:
        # Fallback to current time if date parsing fails
        ET.SubElement(item, 'pubDate').text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
    
    ET.SubElement(item, 'link').text = article_url
    ET.SubElement(item, 'enclosure', {'url': mp3_url, 'type': 'audio/mpeg', 'length': '0'}) # Length is placeholder
    
    ET.indent(tree, space="  ", level=0)
    tree.write('docs/podcast.xml', encoding='utf-8', xml_declaration=True)

def update_index_html(title, mp3_url, summary, article_url):
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
        desc_tag.string = summary
        new_episode_div.append(desc_tag)
        
        audio_tag = soup.new_tag('audio', controls=True)
        source_tag = soup.new_tag('source', src=mp3_url, type='audio/mpeg')
        audio_tag.append(source_tag)
        new_episode_div.append(audio_tag)
        
        episodes_div.insert(0, new_episode_div)
        
        f.seek(0)
        f.write(str(soup.prettify()))
        f.truncate()

def update_articles_csv(title, article_url, mp3_url, voice, summary=""):
    """Update the articles.csv file with new episode details."""
    csv_file = 'articles.csv'
    file_exists = os.path.isfile(csv_file)
    
    current_time = datetime.now()
    date_added = current_time.strftime("%Y-%m-%d %H:%M:%S")
    published_date = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Generate a summary if not provided
    if not summary:
        summary = f"An audio version of the article: {title}"
    
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Title', 'Article URL', 'MP3 URL', 'Voice', 'Date Added', 'Published Date', 'Summary'])
        writer.writerow([title, article_url, mp3_url, voice, date_added, published_date, summary])

def regenerate_feed_and_html_from_mp3s():
    """Regenerate podcast.xml and index.html from existing MP3s and articles.csv."""
    print("Resetting podcast.xml and index.html...")
    # Reset podcast.xml
    with open('docs/podcast.xml', 'w') as f:
        f.write("""<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<rss version=\"2.0\" xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\">\n  <channel>\n    <title>Read Articles Podcast</title>\n    <link>https://deanputney.github.io/read-articles/</link>\n    <description>An AI-powered podcast that converts interesting articles into high-quality audio.</description>\n    <language>en-us</language>\n  </channel>\n</rss>""")
    
    # Reset index.html
    with open('docs/index.html', 'w') as f:
        f.write("""<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>Read Articles Podcast</title>\n    <style>\n        body {\n            font-family: sans-serif;\n            margin: 40px auto;\n            max-width: 800px;\n            line-height: 1.6;\n            font-size: 18px;\n            color: #333;\n            background-color: #f9f9f9;\n        }\n        h1, h2 {\n            line-height: 1.2;\n        }\n        a {\n            color: #007bff;\n        }\n        .episode {\n            border-bottom: 1px solid #ddd;\n            padding-bottom: 20px;\n            margin-bottom: 20px;\n        }\n    </style>\n</head>\n<body>\n    <h1>Read Articles Podcast</h1>\n    <p>An AI-powered podcast that converts interesting articles into high-quality audio. Subscribe with this <a href=\"podcast.xml\">RSS feed</a>.</p>\n    <div id=\"quick-submit\"></div>\n    <div id=\"episodes\"></div>\n    <script src=\"submit.js\"></script>\n    <script>RA.initQuickSubmit(\"quick-submit\");</script>\n</body>\n</html>""")

    # Read articles from CSV
    articles_data = []
    csv_file = 'articles.csv'
    if os.path.exists(csv_file):
        with open(csv_file, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader) # Skip header
            for row in reader:
                # Handle both old and new CSV formats
                if len(row) >= 7:  # New format with Published Date and Summary
                    articles_data.append({'Title': row[0], 'Article URL': row[1], 'MP3 URL': row[2], 'Voice': row[3], 'Date Added': row[4], 'Published Date': row[5], 'Summary': row[6]})
                else:  # Old format
                    articles_data.append({'Title': row[0], 'Article URL': row[1], 'MP3 URL': row[2], 'Voice': row[3], 'Date Added': row[4], 'Published Date': row[4], 'Summary': f"An audio version of the article: {row[0]}"})
    
    # Re-add articles to feed and HTML in chronological order (oldest first)
    # This ensures newest items appear first in both feed and HTML
    for article in articles_data:
        title = article['Title']
        mp3_url = article['MP3 URL']
        article_url = article['Article URL']
        summary = article['Summary']
        published_date = article['Published Date']
        update_podcast_feed(title, mp3_url, summary, article_url, published_date)
        update_index_html(title, mp3_url, summary, article_url)
    
    print("Podcast feed and HTML regenerated successfully.")

def main():
    parser = argparse.ArgumentParser(description="Convert an article from a URL to an MP3 and update the podcast feed, or regenerate the feed from existing MP3s.")
    parser.add_argument("url", nargs='?', help="The URL of the article to convert. Omit to regenerate feed.")
    parser.add_argument("pdf_path", nargs='?', help="Optional PDF file path to extract content from instead of scraping the URL.")
    parser.add_argument("--voice", default="af_bella", help="The voice to use for the TTS conversion (e.g., af_bella, am_santa).")
    parser.add_argument("--reset", action="store_true", help="Reset and regenerate podcast.xml and index.html from existing MP3s and articles.csv.")
    args = parser.parse_args()

    if args.reset:
        regenerate_feed_and_html_from_mp3s()
        return

    if not args.url and not args.pdf_path:
        parser.error("The --reset flag must be used, or a URL (and optionally PDF path) must be provided.")

    if not download_model_files():
        print("Failed to download required model files")
        exit(1)

    # Get article content from PDF or URL
    if args.pdf_path:
        print(f"Extracting content from PDF: {args.pdf_path}")
        article_data = extract_pdf_content(args.pdf_path)
        if not article_data or not article_data['title'] or not article_data['text']:
            print("Failed to extract content from PDF.")
            exit(1)
    else:
        print(f"Fetching article from URL: {args.url}")
        article_data = fetch_article(args.url)
        if not article_data or not article_data['title'] or not article_data['text']:
            print("Failed to fetch or parse article data. The scraper might need adjustments for this website.")
            exit(1)

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
    safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '', title.lower().replace(' ', '-')).strip('-')
    output_filename = f"{safe_filename}_{args.voice}.mp3"
    output_path = Path("docs/episodes") / output_filename
    
    print(f"Saving final audio to {output_path}...")
    final_audio.export(str(output_path), format="mp3", bitrate="192k")
    
    mp3_url = f"https://deanputney.github.io/read-articles/episodes/{output_filename}"
    
    # Generate summary from the article text
    summary = generate_summary(text)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Use URL if provided, otherwise use PDF path for reference
    article_url = args.url if args.url else args.pdf_path
    
    print("Updating podcast feed...")
    update_podcast_feed(title, mp3_url, summary, article_url, current_time)
    
    print("Updating website...")
    update_index_html(title, mp3_url, summary, article_url)
    
    print("Updating articles CSV...")
    update_articles_csv(title, article_url, mp3_url, args.voice, summary)
    
    print("Done.")

if __name__ == "__main__":
    main()
