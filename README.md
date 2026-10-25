# Cat Break Agent

A tiny local AI agent that reminds you to stretch and drink water, then finds a cat video for your break. Gemma runs locally through Ollama; YouTube search supplies a rotating set of recent videos.

## What it does

On each break, the app asks Gemma to choose a vibe (`calm`, `chaotic`, or `cute`) and write a gentle nudge. It then picks a matching recent YouTube result, sends a desktop notification, and opens the video's watch page in your browser.

- Uses the local `gemma3:1b` model by default.
- Searches YouTube for relevant videos published in the last 30 days.
- Caches up to 50 search results per vibe and avoids recently shown video IDs.
- Limits searches to 90 per rolling 24 hours, below the default YouTube API search quota.
- Does not download videos. Browser autoplay and sound depend on your browser settings.

## Requirements

- Windows, Python 3.11+, and [Ollama](https://ollama.com/).
- A downloaded Ollama model, such as `gemma3:1b`.
- A YouTube Data API v3 key. API usage is subject to Google's quota and terms.

## Setup

From the project folder, create a virtual environment, install dependencies, and download the model:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull gemma3:1b
```

Create a Google Cloud project, enable **YouTube Data API v3**, and create an API key restricted to that API. Copy `.env.example` to `.env` and put the key in the copy:

```text
YOUTUBE_API_KEY=your-key-here
```

Keep `.env` private. It is ignored by Git; never commit or share the key. Select `.venv\Scripts\python.exe` as the VS Code interpreter if you use VS Code.

## Run

Start Ollama, then run:

```powershell
.\.venv\Scripts\python.exe .\catbreak.py
```

The current interval is **30 seconds** for testing. Set `INTERVAL = 3600` near the top of `catbreak.py` for hourly breaks. At 30 seconds, the app can open frequent browser tabs and notifications; stop it with `Ctrl+C` when done testing.

## Privacy and playback

The prompt containing the time and elapsed session duration goes to the local Ollama model. The app sends a generic, vibe-based search query and your API key to Google's YouTube Data API; it does not send your prompt or work duration to YouTube. Search results and recently shown video IDs are stored locally in `video-cache.json`, which is ignored by Git.

The app opens a YouTube watch page and requests autoplay. Browsers may block playback or sound until you interact with the page. The app does not use VLC or download YouTube videos.

## Tests

Run the focused tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

## Troubleshooting

- **Ollama connection error:** open the Ollama app or run `ollama serve`.
- **Model not found:** check the model name with `ollama list` and match it to `MODEL` in `catbreak.py`.
- **YouTube API error:** confirm the API is enabled, the key is valid, and its restrictions allow YouTube Data API v3. The script stops rather than silently substituting a stale result.
- **No notification:** check Windows notification and Focus Assist settings.
- **Video does not autoplay:** start playback manually; browser autoplay policies vary.

For the longer Hacktoberfest walkthrough and submission notes, see [Cat Break Agent Build Guide and Context](./Cat%20Break%20Agent%20Build%20Guide%20and%20Context.md).
