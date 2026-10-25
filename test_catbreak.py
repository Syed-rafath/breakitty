import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import catbreak


class YouTubeSearchTests(unittest.TestCase):
    def test_main_requires_an_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(SystemExit, "YOUTUBE_API_KEY"):
                catbreak.main()

    def test_fetch_youtube_videos_parses_search_results(self) -> None:
        response_body = {
            "items": [
                {
                    "id": {"videoId": "cat123"},
                    "snippet": {"title": "A Cat Video"},
                }
            ]
        }
        response = BytesIO(json.dumps(response_body).encode("utf-8"))

        with patch("catbreak.urlopen", return_value=response) as open_url:
            videos = catbreak.fetch_youtube_videos("cute", "test-key")

        self.assertEqual(videos, [{"id": "cat123", "title": "A Cat Video"}])
        request = open_url.call_args.args[0]
        params = parse_qs(urlparse(request.full_url).query)
        self.assertEqual(params["key"], ["test-key"])
        self.assertEqual(params["maxResults"], ["50"])
        self.assertEqual(params["order"], ["relevance"])
        self.assertIn("publishedAfter", params)
        self.assertEqual(params["type"], ["video"])

    def test_video_results_are_cached_and_not_reused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_path = Path(temporary_directory) / "video-cache.json"
            results = [
                {"id": "first", "title": "First Cat"},
                {"id": "second", "title": "Second Cat"},
            ]
            with patch("catbreak.fetch_youtube_videos", return_value=results) as fetch:
                first = catbreak.choose_video("cute", "test-key", cache_path)
                second = catbreak.choose_video("cute", "test-key", cache_path)

            self.assertNotEqual(first["id"], second["id"])
            fetch.assert_called_once_with("cute", "test-key")

    def test_old_cache_refreshes_stale_search_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_path = Path(temporary_directory) / "video-cache.json"
            cache_path.write_text(
                json.dumps(
                    {
                        "seen_video_ids": ["already-seen"],
                        "videos_by_vibe": {
                            "cute": [{"id": "stale", "title": "Stale search result"}]
                        },
                        "search_timestamps": [],
                    }
                ),
                encoding="utf-8",
            )

            new_results = [{"id": "fresh", "title": "Fresh cat"}]
            with patch("catbreak.fetch_youtube_videos", return_value=new_results) as fetch:
                selected = catbreak.choose_video("cute", "test-key", cache_path)

            self.assertEqual(selected, new_results[0])
            fetch.assert_called_once_with("cute", "test-key")

    def test_cache_rejects_reusing_all_seen_search_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_path = Path(temporary_directory) / "video-cache.json"
            results = [{"id": "same", "title": "Same Cat"}]
            with patch("catbreak.fetch_youtube_videos", return_value=results):
                catbreak.choose_video("cute", "test-key", cache_path)
                with self.assertRaisesRegex(RuntimeError, "no unseen videos"):
                    catbreak.choose_video("cute", "test-key", cache_path)

    def test_search_limit_stops_requests_before_daily_quota(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            cache_path = Path(temporary_directory) / "video-cache.json"
            recent_search = catbreak.time.time()
            cache_path.write_text(
                json.dumps(
                    {
                        "seen_video_ids": [],
                        "videos_by_vibe": {},
                        "search_timestamps": [
                            recent_search
                        ] * catbreak.MAX_SEARCH_CALLS_PER_DAY,
                    }
                ),
                encoding="utf-8",
            )

            with patch("catbreak.fetch_youtube_videos") as fetch:
                with self.assertRaisesRegex(RuntimeError, "90 YouTube searches"):
                    catbreak.choose_video("cute", "test-key", cache_path)
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
