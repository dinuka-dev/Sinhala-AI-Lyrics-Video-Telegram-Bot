# Sinhala Lyric Video Generator

A Python-based application that creates animated lyric videos with Studio Ghibli-style backgrounds from Spotify tracks. The project supports both a standalone script and a Telegram bot interface.

## Features

- **Spotify Integration**: Download audio from Spotify tracks
- **AI-Generated Backgrounds**: Create Studio Ghibli-style images using OpenAI's image generation
- **Synchronized Lyrics**: Automatically fetch and sync lyrics with the audio
- **Multiple Font Support**: 5 different Sinhala fonts for lyric display
- **Animated Backgrounds**: Smooth panning and wave motion effects
- **Telegram Bot**: Interactive bot interface for easy video generation
- **Sinhala Text Support**: Convert Unicode Sinhala text to different typing styles

## Project Structure

```
├── app.py                 # Main video generation script
├── api.py                 # API integrations (Spotify, OpenAI, Lyrics)
├── bot.py                 # Telegram bot interface
├── gen.py                 # Video generation and processing
├── sinhala_converter/     # Sinhala text conversion utilities
├── fonts/                 # Sinhala font files (1.ttf - 5.ttf)
├── temp/                  # Temporary files during processing
├── outputs/               # Generated video files
└── data/                  # Video metadata storage
```

## Prerequisites

- Python 3.8 or higher
- FFmpeg (for video processing)
- Required Python packages (see Installation section)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd sinhala-lyric-video-generator
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or, install these packages manually:

```bash
pip install requests openai python-dotenv moviepy opencv-python pillow python-telegram-bot
```

### 3. Install FFmpeg

**Windows:**
- Download FFmpeg from https://ffmpeg.org/download.html
- Extract and add to your system PATH

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

### 4. Set Up Environment Variables

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` file with your API credentials:

```env
OPENAI_API_KEY=your_openai_api_key_here
RAPID_API_KEY=your_rapidapi_key_here
SCRAPE_DO_API_KEY=your_scrape_do_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

### 5. API Keys Setup

**OpenAI API Key:**
1. Visit https://platform.openai.com/api-keys
2. Create a new API key
3. Add it to your `.env` file

**RapidAPI Key (No Need Right Now, so skip this step):**
1. Sign up at https://rapidapi.com/
2. Subscribe to "Spotify Music MP3 Downloader API"
3. Get your API key from the dashboard

**scrape.do API Key:**
1. Sign up at https://scrape.do/
2. Get your API key for web scraping

**Telegram Bot Token:**
1. Message @BotFather on Telegram
2. Create a new bot with `/newbot`
3. Get your bot token

## Usage

1. Start the bot:
```bash
python bot.py
```

2. Open Telegram and find your bot
3. Send `/start` to begin
4. Send `/generate` to create a video
5. Follow the interactive prompts:
   - Provide Spotify track URL
   - Set start and end times
   - Choose background image source:
     - **Lyrics Based**: AI generates image from song lyrics
     - **Raw to Ghibli**: Convert your image to Ghibli style
     - **Ghibli Character**: Use your image as character reference
   - Upload image (if required)
   - Select font (1-5)
   - Choose song title option

## Configuration Options

### Font Selection
- **Font 1-5**: Different Sinhala fonts located in `fonts/` directory
- Each font provides different styling for lyric display

### Background Image Sources
- **lyrics_based**: AI generates background from song lyrics
- **raw_ghibli**: Converts uploaded image to Ghibli cartoon style
- **ghibli_char**: Uses uploaded image as character performing on stage

### Video Settings
You can modify these in `gen.py`:
- **Resolution**: 720x900 (optimized for mobile)
- **FPS**: 60
- **Animation**: Wave motion with configurable amplitude and speed

## Troubleshooting

### Common Issues

**1. FFmpeg not found:**
```
Error: FFmpeg not found
```
- Ensure FFmpeg is installed and in your system PATH
- Restart your terminal/command prompt after installation

**2. API Rate Limits:**
```
Error: API rate limit exceeded
```
- Check your API key quotas
- Wait before making new requests

**3. Font Issues:**
```
Warning: Sinhala font not found, using default font
```
- Ensure font files exist in `fonts/` directory
- Check font file permissions

**4. Memory Issues:**
```
Error: Out of memory
```
- Reduce video duration
- Close other applications
- Use smaller image files

### Performance Tips

- Use images under 5MB for faster processing
- Keep video clips under 2 minutes for optimal performance
- Ensure stable internet connection for API calls

## File Structure After Setup

```
project/
├── temp/                  # Temporary processing files
│   ├── audio_*.mp3       # Downloaded audio
│   ├── lyrics_*.json     # Fetched lyrics
│   ├── ghibli_*.png      # Generated backgrounds
│   └── raw_*.jpg         # Processed images
├── outputs/              # Final video outputs
│   └── final_*.mp4       # Generated videos
├── data/                 # Video metadata
│   └── *.json           # Processing data
└── bot_temp/            # Bot temporary files
    └── user_images/     # User uploaded images
```

## API Dependencies

- **OpenAI**: Image generation and editing
- **RapidAPI**: Spotify track downloading (not working right now)
- **scrape.do**: Synchronized lyrics fetching (tricky alternative to download from spotify)
- **LRCLib**: Synchronized lyrics fetching
- **Telegram Bot API**: Bot interface (optional)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational purposes. Ensure you comply with:
- Spotify's Terms of Service
- OpenAI's Usage Policies
- Copyright laws for music and images

## Support

For issues and questions:
1. Check the troubleshooting section
2. Verify all API keys are correctly configured
3. Ensure all dependencies are installed
4. Check system requirements

---

**Note**: This tool is designed for personal use and educational purposes. Always respect copyright laws and platform terms of service when using this application.