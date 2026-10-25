import json
import os
import random
import sys
import time
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TypedDict
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import httpx
import ollama
from dotenv import load_dotenv
from plyer import notification

load_dotenv(Path(__file__).with_name(".env"))

MODEL = "gemma3:1b"
INTERVAL = 30  # seconds; set to 3600 for hourly breaks
VIDEO_CACHE_PATH = Path(__file__).with_name("video-cache.json")
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"
SEARCH_WINDOW_SECONDS = 24 * 60 * 60
MAX_SEARCH_CALLS_PER_DAY = 90
MAX_SEEN_VIDEO_IDS = 1000
VIDEO_CACHE_VERSION = 2

SEARCH_QUERIES = {
    "calm": "calm relaxing cat video",
    "chaotic": "funny playful cat video",
    "cute": "cute kitten cat video",
}

FALLBACK = {"vibe": "cute", "message": "Stretch, drink water, then look at this cat."}


class Video(TypedDict):
    id: str
    title: str


class VideoCache(TypedDict):
    cache_version: int
    seen_video_ids: list[str]
    videos_by_vibe: dict[str, list[Video]]
    search_timestamps: list[float]


def ask_model(hours_worked: float, clock: str) -> dict[str, str]:
    prompt = f"""It is {clock}. The user has been at their computer for {hours_worked:.1f} hours.
Choose the best cat video vibe from: calm, chaotic, cute.
Write a short, funny, gentle nudge to stretch or drink water.
Reply only as JSON: {{"vibe": "...", "message": "..."}}"""
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        format="json",
    )

    try:
        output = json.loads(response["message"]["content"])
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("The local model returned an invalid JSON response.") from error

    if not isinstance(output, dict):
        print("The local model response was not a JSON object; using the fallback.")
        return FALLBACK.copy()

    vibe = output.get("vibe")
    message = output.get("message")
    if (
        not isinstance(vibe, str)
        or vibe not in SEARCH_QUERIES
        or not isinstance(message, str)
        or not message.strip()
    ):
        print("The local model response was missing a valid vibe or message; using the fallback.")
        return FALLBACK.copy()

    return {"vibe": vibe, "message": message.strip()}


def load_video_cache(cache_path: Path) -> VideoCache:
    if not cache_path.exists():
        return {
            "cache_version": VIDEO_CACHE_VERSION,
            "seen_video_ids": [],
            "videos_by_vibe": {},
            "search_timestamps": [],
        }

    try:
        raw_cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not read video cache at {cache_path}: {error}") from error

    if not isinstance(raw_cache, dict):
        raise RuntimeError(f"Video cache at {cache_path} must contain a JSON object.")

    seen_ids = raw_cache.get("seen_video_ids", [])
    raw_videos = raw_cache.get("videos_by_vibe", {})
    raw_timestamps = raw_cache.get("search_timestamps", [])
    if (
        not isinstance(seen_ids, list)
        or not all(isinstance(video_id, str) for video_id in seen_ids)
        or not isinstance(raw_videos, dict)
        or not isinstance(raw_timestamps, list)
        or not all(
            isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool)
            for timestamp in raw_timestamps
        )
    ):
        raise RuntimeError(f"Video cache at {cache_path} has an invalid structure.")

    videos_by_vibe: dict[str, list[Video]] = {}
    for vibe, raw_pool in raw_videos.items():
        if vibe not in SEARCH_QUERIES or not isinstance(raw_pool, list):
            raise RuntimeError(f"Video cache at {cache_path} has an invalid video pool.")

        pool: list[Video] = []
        for raw_video in raw_pool:
            if (
                not isinstance(raw_video, dict)
                or not isinstance(raw_video.get("id"), str)
                or not isinstance(raw_video.get("title"), str)
            ):
                raise RuntimeError(f"Video cache at {cache_path} contains an invalid video.")
            pool.append({"id": raw_video["id"], "title": raw_video["title"]})
        videos_by_vibe[vibe] = pool

    cache_version = raw_cache.get("cache_version")
    if cache_version != VIDEO_CACHE_VERSION:
        videos_by_vibe = {}

    return {
        "cache_version": VIDEO_CACHE_VERSION,
        "seen_video_ids": seen_ids,
        "videos_by_vibe": videos_by_vibe,
        "search_timestamps": [float(timestamp) for timestamp in raw_timestamps],
    }


def save_video_cache(cache_path: Path, cache: VideoCache) -> None:
    temporary_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
    temporary_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    temporary_path.replace(cache_path)


def fetch_youtube_videos(vibe: str, api_key: str) -> list[Video]:
    params = urlencode(
        {
            "key": api_key,
            "part": "snippet",
            "q": SEARCH_QUERIES[vibe],
            "type": "video",
            "order": "relevance",
            "publishedAfter": (
                datetime.now(timezone.utc) - timedelta(days=30)
            ).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "maxResults": 50,
        }
    )
    request = Request(f"{YOUTUBE_API_URL}?{params}")

    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise RuntimeError(
            f"YouTube API request failed with HTTP {error.code}: {error.reason}"
        ) from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"Could not reach the YouTube API: {error}") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("YouTube API returned invalid JSON.") from error

    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise RuntimeError("YouTube API returned an unexpected response.")

    videos: list[Video] = []
    for item in payload["items"]:
        if not isinstance(item, dict):
            continue
        video_data = item.get("id")
        snippet = item.get("snippet")
        if not isinstance(video_data, dict) or not isinstance(snippet, dict):
            continue
        video_id = video_data.get("videoId")
        title = snippet.get("title")
        if isinstance(video_id, str) and isinstance(title, str):
            videos.append({"id": video_id, "title": title})

    if not videos:
        raise RuntimeError(f"YouTube returned no videos for the search '{SEARCH_QUERIES[vibe]}'.")
    return videos


def choose_video(
    vibe: str,
    api_key: str,
    cache_path: Path = VIDEO_CACHE_PATH,
) -> Video:
    if vibe not in SEARCH_QUERIES:
        raise ValueError(f"Unsupported video vibe: {vibe}")

    cache = load_video_cache(cache_path)
    seen_ids = set(cache["seen_video_ids"])
    candidates = cache["videos_by_vibe"].get(vibe, [])
    available = [video for video in candidates if video["id"] not in seen_ids]

    if not available:
        now = time.time()
        recent_searches = [
            timestamp
            for timestamp in cache["search_timestamps"]
            if now - timestamp < SEARCH_WINDOW_SECONDS
        ]
        if len(recent_searches) >= MAX_SEARCH_CALLS_PER_DAY:
            raise RuntimeError(
                "The app reached its safety limit of 90 YouTube searches in 24 hours. "
                "Cached videos will be available again when the daily window resets."
            )

        cache["search_timestamps"] = recent_searches + [now]
        save_video_cache(cache_path, cache)
        candidates = fetch_youtube_videos(vibe, api_key)
        cache["videos_by_vibe"][vibe] = candidates
        available = [video for video in candidates if video["id"] not in seen_ids]

    if not available:
        raise RuntimeError(
            "YouTube returned no unseen videos for this vibe. Try again later for newer uploads."
        )

    selected = random.choice(available)
    cache["seen_video_ids"] = (cache["seen_video_ids"] + [selected["id"]])[-MAX_SEEN_VIDEO_IDS:]
    save_video_cache(cache_path, cache)
    return selected


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise SystemExit(
            "Set YOUTUBE_API_KEY in the project's .env file. "
            "See the build guide for setup instructions."
        )

    start = time.monotonic()
    while True:
        hours_worked = (time.monotonic() - start) / 3600
        try:
            output = ask_model(hours_worked, datetime.now().strftime("%I:%M %p"))
        except (httpx.HTTPError, ollama.ResponseError, ValueError) as error:
            print(f"Local model unavailable; using the fallback: {error}", file=sys.stderr)
            output = FALLBACK.copy()

        video = choose_video(output["vibe"], api_key)
        video_url = f"https://www.youtube.com/watch?v={video['id']}&autoplay=1"
        notification.notify(title="Cat break", message=output["message"], timeout=20)
        print(f"{datetime.now()} {output} {video['title']} {video_url}")
        if not webbrowser.open(video_url, new=1, autoraise=True):
            print("Could not open the video in your default browser.", file=sys.stderr)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
