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

- **Multiple Voices**: Different AI voices for variety (am_santa, af_bella, etc.)
- **High Quality**: 24kHz audio, 192kbps MP3 encoding
- **Automatic Processing**: Scripts to convert articles to audio
- **Podcast Feed**: Standards-compliant RSS feed for podcast apps
- **GitHub Pages**: Free hosting for the podcast website and episodes

### Current Episodes

- **What Are People Still Doing on X? - The Atlantic**
  - Santa Voice (am_santa): 10:12
  - Bella Voice (af_bella): 10:44

## 🛠️ Technical Setup

### Prerequisites

```bash
pip install kokoro-onnx soundfile pydub scipy
```

### Generate Audio

1. Place your article in Markdown format in the root directory
2. Update the script with the filename
3. Run the TTS conversion:

```bash
python3 kokoro_tts.py
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
    ├── episode1.mp3
    └── episode2.mp3
kokoro_tts.py          # TTS conversion script
```

## 📄 Adding New Episodes

1. Add your article (Markdown format) to the root directory
2. Update `kokoro_tts.py` with the filename and desired voice
3. Run the script to generate audio
4. Copy the MP3 to `docs/episodes/`
5. Update `docs/podcast.xml` with the new episode
6. Update `docs/index.html` with the episode info
7. Commit and push to GitHub

8. **Push to GitHub:**
   ```bash
   git remote add origin https://github.com/deanputney/read-articles.git
   git branch -M main
   git push -u origin main
   ```

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
