#!/usr/bin/env python3
"""
Script to fetch articles from URLs and convert them to markdown
"""

import os
import re
import sys
import time
import requests
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from readability import Document
import html2text
import urllib.parse

def clean_filename(title):
    """Convert a title to a safe filename"""
    # Replace spaces with dashes and remove non-alphanumeric characters
    safe_filename = re.sub(r'[^a-zA-Z0-9\s\-]', '', title)
    safe_filename = re.sub(r'\s+', ' ', safe_filename).strip()
    safe_filename = safe_filename.replace(' ', '-')
    return safe_filename

def get_from_archive_is(url):
    """Try to get content from archive.is"""
    archive_url = f"https://archive.is/{url}"
    try:
        print(f"Trying to get content from archive.is: {archive_url}")
        response = requests.get(archive_url, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to get from archive.is, status: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error accessing archive.is: {e}")
        return None

def fetch_article(url):
    """Fetch article from URL and convert to markdown"""
    try:
        print(f"Fetching article: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        
        # Check if request was successful
        if response.status_code != 200:
            print(f"Failed to fetch article, status: {response.status_code}")
            
            # Try archive.is if initial request fails (might be paywall)
            archive_content = get_from_archive_is(url)
            if not archive_content:
                return None, None
            response_text = archive_content
        else:
            response_text = response.text
        
        # Parse the article using readability
        doc = Document(response_text)
        title = doc.title()
        content = doc.summary()
        
        # Convert HTML to markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0  # No wrapping
        markdown_content = h.handle(content)
        
        # Add title at the top
        full_content = f"# {title}\n\n{markdown_content}"
        
        return title, full_content
    except Exception as e:
        print(f"Error fetching article: {e}")
        return None, None

def main():
    """Process URLs from file and convert to markdown"""
    # Path for the URLs file
    urls_file = Path("article_urls.txt")
    
    if not urls_file.exists():
        print(f"Error: {urls_file} not found")
        return False
    
    # Read URLs from file
    with open(urls_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f.readlines() if line.strip() and not line.strip().startswith('#')]
    
    if not urls:
        print("No URLs found in the file")
        return False
    
    success_count = 0
    
    # Process each URL
    for url in urls:
        title, content = fetch_article(url)
        
        if not title or not content:
            print(f"Failed to process URL: {url}")
            continue
        
        # Create a safe filename from the title
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')
        safe_title = clean_filename(title)
        filename = f"{safe_title} - {domain}.md"
        
        # Save markdown to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"Saved article: {filename}")
        success_count += 1
        
        # Add a short delay to avoid overwhelming the server
        time.sleep(2)
    
    print(f"Processed {success_count} out of {len(urls)} URLs")
    return success_count > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)