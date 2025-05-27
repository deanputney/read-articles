#!/usr/bin/env python3
"""
Script to update the podcast XML feed and website with new episodes
"""

import os
import re
import sys
import time
import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom
import subprocess

def get_audio_duration(audio_path):
    """Get the duration of an audio file in seconds using ffprobe"""
    try:
        # Try to use ffprobe if available
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
             '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        duration = int(float(result.stdout.strip()))
        return duration
    except (subprocess.SubprocessError, ValueError, FileNotFoundError):
        # If ffprobe fails or is not available, estimate based on file size
        # This is a rough estimate: ~192kbps MP3 = ~24KB/s
        file_size = Path(audio_path).stat().st_size
        estimated_duration = int(file_size / (24 * 1024))
        return max(estimated_duration, 1)  # Ensure at least 1 second

def copy_audio_to_episodes_folder(source_path):
    """Copy MP3 file to episodes directory"""
    episodes_dir = Path("docs/episodes")
    episodes_dir.mkdir(exist_ok=True)
    
    filename = Path(source_path).name
    destination = episodes_dir / filename
    
    # Copy the file
    with open(source_path, "rb") as src, open(destination, "wb") as dst:
        dst.write(src.read())
    
    print(f"Copied {source_path} to {destination}")
    return destination

def format_rfc822_date(days_offset=0):
    """Format the current date in RFC 822 format for the podcast feed
    Optionally with an offset in days (negative for past dates)"""
    date = datetime.datetime.now() + datetime.timedelta(days=days_offset)
    return date.strftime("%a, %d %b %Y %H:%M:%S GMT")

def update_podcast_xml(audio_files, article_titles, voices):
    """Update the podcast XML feed with new episodes"""
    podcast_path = Path("docs/podcast.xml")
    
    # If podcast.xml doesn't exist, create a basic structure
    if not podcast_path.exists():
        # Create basic podcast XML template
        root = ET.Element("rss")
        root.set("version", "2.0")
        root.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
        root.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")
        
        channel = ET.SubElement(root, "channel")
        ET.SubElement(channel, "title").text = "Read Articles Podcast"
        ET.SubElement(channel, "link").text = "https://deanputney.github.io/read-articles/"
        ET.SubElement(channel, "description").text = "AI-generated audio versions of interesting articles using Kokoro TTS"
        ET.SubElement(channel, "language").text = "en-us"
        ET.SubElement(channel, "copyright").text = f"© {datetime.datetime.now().year} Read Articles Podcast"
        
        itunes_author = ET.SubElement(channel, "itunes:author")
        itunes_author.text = "Read Articles"
        
        itunes_summary = ET.SubElement(channel, "itunes:summary")
        itunes_summary.text = "AI-generated audio versions of interesting articles using Kokoro TTS"
        
        itunes_owner = ET.SubElement(channel, "itunes:owner")
        ET.SubElement(itunes_owner, "itunes:name").text = "Read Articles"
        ET.SubElement(itunes_owner, "itunes:email").text = "your-email@example.com"
        
        itunes_image = ET.SubElement(channel, "itunes:image")
        itunes_image.set("href", "https://deanputney.github.io/read-articles/podcast-cover.jpg")
        
        ET.SubElement(channel, "itunes:category").set("text", "News")
        ET.SubElement(channel, "itunes:category").set("text", "Technology")
        ET.SubElement(channel, "itunes:explicit").text = "false"
        
        lastBuildDate = ET.SubElement(channel, "lastBuildDate")
        lastBuildDate.text = format_rfc822_date()
        
        pubDate = ET.SubElement(channel, "pubDate")
        pubDate.text = format_rfc822_date()
    else:
        # Parse existing XML
        tree = ET.parse(podcast_path)
        root = tree.getroot()
        channel = root.find("channel")
        
        # Update the build date
        lastBuildDate = channel.find("lastBuildDate")
        if lastBuildDate is not None:
            lastBuildDate.text = format_rfc822_date()
        else:
            lastBuildDate = ET.SubElement(channel, "lastBuildDate")
            lastBuildDate.text = format_rfc822_date()
    
    # Add new episodes to the channel
    for i, (audio_path, article_title, voice) in enumerate(zip(audio_files, article_titles, voices)):
        filename = Path(audio_path).name
        file_size = Path(audio_path).stat().st_size
        
        # Extract article source from title if it contains a hyphen
        article_source = ""
        if " - " in article_title:
            parts = article_title.split(" - ")
            if len(parts) > 1:
                article_source = parts[-1]
        
        # Create new item
        item = ET.SubElement(channel, "item")
        
        # Add voice info to title
        voice_display_name = voice.replace("am_", "").replace("af_", "").title()
        ET.SubElement(item, "title").text = f"{article_title} ({voice_display_name} Voice)"
        
        ET.SubElement(item, "link").text = "https://deanputney.github.io/read-articles/"
        ET.SubElement(item, "description").text = f"{article_title}. Read by AI voice: {voice}"
        
        # Create enclosure for MP3
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", f"https://deanputney.github.io/read-articles/episodes/{filename}")
        enclosure.set("length", str(file_size))
        enclosure.set("type", "audio/mpeg")
        
        # Create unique GUID
        date_part = datetime.datetime.now().strftime("%Y_%m_%d")
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', filename.split('.')[0])
        ET.SubElement(item, "guid", isPermaLink="false").text = f"{clean_name}_{date_part}"
        
        # Set publication date with slight offset so items are ordered correctly
        ET.SubElement(item, "pubDate").text = format_rfc822_date(-i)
        
        # Get audio duration
        duration = get_audio_duration(audio_path)
        ET.SubElement(item, "itunes:duration").text = str(duration)
        
        # Add other iTunes specific tags
        ET.SubElement(item, "itunes:author").text = f"{article_source} (AI Narrated)" if article_source else "AI Narrated"
        
        # Create a short subtitle from article title
        subtitle = article_title
        if len(subtitle) > 50:
            subtitle = subtitle[:47] + "..."
        ET.SubElement(item, "itunes:subtitle").text = subtitle
        
        # Summary
        ET.SubElement(item, "itunes:summary").text = f"{article_title}. Narrated by AI voice {voice}."
        
        ET.SubElement(item, "itunes:explicit").text = "false"
    
    # Format and save the XML file
    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ")
    with open(podcast_path, "w", encoding="utf-8") as f:
        f.write(xmlstr)
    
    print(f"Updated podcast XML with {len(audio_files)} new episodes")
    return True

def update_website_with_episodes(audio_files, article_titles, voices, durations):
    """Update the website's index.html with new episodes"""
    index_path = Path("docs/index.html")
    
    if not index_path.exists():
        print("Error: index.html not found")
        return False
    
    # Parse the HTML
    with open(index_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    
    # Find where to insert episodes
    episodes_heading = soup.find("h2", string="Latest Episodes")
    if not episodes_heading:
        print("Could not find 'Latest Episodes' heading in index.html")
        return False
    
    # Create episode entries
    for i, (audio_path, article_title, voice, duration) in enumerate(zip(audio_files, article_titles, voices, durations)):
        filename = Path(audio_path).name
        
        # Create episode div
        episode_div = soup.new_tag("div", **{"class": "episode"})
        
        # Format title with voice
        voice_display_name = voice.replace("am_", "").replace("af_", "").title()
        title_tag = soup.new_tag("h3")
        title_tag.string = f"{article_title} ({voice_display_name} Voice)"
        episode_div.append(title_tag)
        
        # Add metadata
        meta_div = soup.new_tag("div", **{"class": "episode-meta"})
        # Format duration as MM:SS
        minutes = duration // 60
        seconds = duration % 60
        formatted_duration = f"{minutes}:{seconds:02d}"
        meta_div.string = f"Duration: {formatted_duration} | Voice: {voice} | Published: {datetime.datetime.now().strftime('%b %d, %Y')}"
        episode_div.append(meta_div)
        
        # Add description
        desc_p = soup.new_tag("p")
        desc_p.string = f"AI-narrated version of '{article_title}' using the {voice_display_name} voice."
        episode_div.append(desc_p)
        
        # Add audio player
        audio_tag = soup.new_tag("audio", controls=True, **{"class": "audio-player"})
        source_tag = soup.new_tag("source", src=f"episodes/{filename}", type="audio/mpeg")
        audio_tag.append(source_tag)
        audio_tag.append("Your browser does not support the audio element.")
        episode_div.append(audio_tag)
        
        # Insert the new episode after the heading
        episodes_heading.insert_after(episode_div)
    
    # Save the updated HTML
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(str(soup))
    
    print(f"Updated index.html with {len(audio_files)} new episodes")
    return True

def main():
    """Update podcast feed and website with newly generated MP3 files"""
    # Look for MP3 files in the root directory
    mp3_files = list(Path(".").glob("*.mp3"))
    
    if not mp3_files:
        print("No MP3 files found in the root directory")
        return False
    
    print(f"Found {len(mp3_files)} MP3 files")
    
    audio_files = []
    article_titles = []
    voices = []
    durations = []
    
    # Process each MP3 file
    for mp3_file in mp3_files:
        # Copy to episodes folder
        dest_path = copy_audio_to_episodes_folder(mp3_file)
        
        # Try to extract info from filename
        filename = mp3_file.name
        base_name = filename.split('.')[0]
        
        # Try to extract voice from filename (e.g., article_name_am_santa.mp3)
        voice = "unknown"
        if "_am_" in base_name:
            voice = "am_" + base_name.split("_am_")[1]
        elif "_af_" in base_name:
            voice = "af_" + base_name.split("_af_")[1]
        
        # Try to extract article title
        article_title = base_name
        if "_am_" in base_name:
            article_title = base_name.split("_am_")[0].replace("_", " ")
        elif "_af_" in base_name:
            article_title = base_name.split("_af_")[0].replace("_", " ")
            
        # Capitalize title
        article_title = article_title.title().replace("-", " - ")
        
        # Get duration
        duration = get_audio_duration(mp3_file)
        
        # Store information for updating XML and website
        audio_files.append(str(dest_path))
        article_titles.append(article_title)
        voices.append(voice)
        durations.append(duration)
    
    # Update podcast XML feed
    update_podcast_xml(audio_files, article_titles, voices)
    
    # Update the website
    update_website_with_episodes(audio_files, article_titles, voices, durations)
    
    print("Website and podcast feed updated successfully")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)