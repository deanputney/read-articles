# 🎧 Read Articles Podcast

An AI-powered podcast that converts interesting articles into high-quality audio using [Kokoro TTS](https://github.com/thewh1teagle/kokoro-onnx).

## 🔗 Listen to the Podcast

**Website:** [https://deanputney.github.io/read-articles/](https://deanputney.github.io/read-articles/)

**RSS Feed:** `https://deanputney.github.io/read-articles/podcast.xml`

## 📱 How to Subscribe

1. Copy the RSS feed URL above
2. Open your favorite podcast app (Apple Podcasts, Spotify, Overcast, etc.)
3. Add a new podcast by URL/RSS feed
4. Paste the RSS feed URL

## 🤖 How It Works

This project uses **Kokoro TTS**, a high-quality AI text-to-speech model, to convert written articles into natural-sounding audio podcasts.

### Features

- **URL-to-Audio Conversion**: Convert any article URL directly to audio podcast
- **AI-Generated Summaries**: Uses Gemini CLI to create intelligent summaries for each episode
- **Multiple Voices**: Different AI voices for variety (am_santa, af_bella, etc.)
- **High Quality**: 24kHz audio, 192kbps MP3 encoding with intro music and ducking
- **Rich RSS Feed**: Includes article summaries, original article links, and proper chronological ordering
- **Automated Publishing**: Simple workflow to publish new episodes with git integration
- **GitHub Pages**: Free hosting for the podcast website and episodes

### Current Episodes

- **What Are People Still Doing on X? - The Atlantic**
  - Santa Voice (am_santa): 10:12
  - Bella Voice (af_bella): 10:44

## 🛠️ Technical Setup

### Prerequisites

**Python Dependencies:**
```bash
pip install -r requirements.txt
```

**Gemini CLI:** Required for generating article summaries
```bash
npm install -g @google/generative-ai-cli
```

### Generate Audio from URLs

Convert any article URL to an audio podcast episode:

```bash
python3 url_to_podcast.py "https://example.com/article-url"
```

### Regenerate Feed

Regenerate the podcast feed and website from existing episodes:

```bash
python3 url_to_podcast.py --reset
```

### Quick Commands with Just

```bash
# Convert an article from URL
just read "https://example.com/article-url"

# Convert an article from PDF with URL for links
just read "https://example.com/article-url" "/path/to/article.pdf"

# Convert from PDF only (uses PDF filename for reference)
just read "" "/path/to/article.pdf"

# Regenerate feed from existing episodes
just reset

# Publish all changes (reset + git commit + push)
just publish
```

### Available Voices

The script supports multiple Kokoro TTS voices:

**American Voices:**

- `af_bella`, `af_sarah`, `af_nova` (Female)
- `am_santa`, `am_adam`, `am_echo` (Male)

**British Voices:**

- `bf_alice`, `bf_emma` (Female)
- `bm_daniel`, `bm_george` (Male)

And many more in different languages!

## 🚀 Deployment

This podcast is automatically deployed using GitHub Pages:

1. Push changes to the `main` branch
2. GitHub Pages serves the content from the `docs/` folder
3. The RSS feed and episodes are immediately available

### File Structure

```
docs/
├── index.html          # Main podcast website
├── podcast.xml         # RSS feed for podcast apps
└── episodes/           # Audio files
    ├── flounder-mode_af_bella.mp3
    ├── atharvas-blog_af_bella.mp3
    └── community-is-motivation-on-tap_af_bella.mp3
url_to_podcast.py       # Main script: URL to audio converter
kokoro_tts.py          # Direct TTS conversion utility
articles.csv           # Episode database with summaries and metadata
justfile               # Task runner commands
assets/
└── intro_music.mp3     # Intro music for episodes
```

## 📄 Adding New Episodes

1.  **Generate Episode:** Convert any article URL to audio:
    ```bash
    python3 url_to_podcast.py "https://example.com/article-url"
    ```
    This automatically:
    - Fetches the article content
    - Generates an AI summary using Gemini CLI
    - Creates high-quality audio with intro music
    - Updates the RSS feed and website
    - Adds episode to the articles.csv database

2.  **Publish Changes:** Deploy to GitHub Pages:
    ```bash
    just publish
    ```
    This automatically:
    - Regenerates the feed from the database
    - Commits all changes
    - Pushes to GitHub for immediate deployment

## 🎯 Future Enhancements

- [ ] Automated episode generation from RSS feeds
- [ ] Multiple language support
- [ ] Voice blending capabilities
- [ ] Automatic podcast feed updates
- [ ] Chapter markers for long articles
- [ ] Speed control options

## 📊 Model Information

- **TTS Model**: Kokoro v1.0 (82M parameters)
- **Sample Rate**: 24kHz
- **Model Size**: ~310MB (excluded from git)
- **Voices File**: ~27MB (excluded from git)

## 🔧 Development

The model files are automatically downloaded when running the script for the first time. They're excluded from git due to size constraints.

## 📜 License

This project is open source. The Kokoro TTS model is licensed under Apache 2.0.

---

**Generated with ❤️ using AI**
