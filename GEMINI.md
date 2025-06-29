# Gemini Rules for the read-articles project

- This project takes markdown articles, converts them to MP3 using Google Text-to-Speech, and adds them to a podcast feed.
- The main script is `kokoro_tts.py`.
- To generate a new episode: `python kokoro_tts.py "input_filename.md" "voice"`
- The website is served from the `docs` directory using GitHub Pages.
- Source articles are in markdown files in the `source_articles` directory.
- Generated MP3s are in `docs/episodes`.
- The podcast feed is `docs/podcast.xml`.
- The website is `docs/index.html`.
