"""Transcript download and loading (youtube-transcript-api 1.2.4)."""
import json
from pathlib import Path


def fetch_and_save(video_id, out_dir="data/transcripts"):
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id)
    lines = [{"text": s.text, "start": float(s.start), "duration": float(s.duration)} for s in fetched]
    path = Path(out_dir) / f"{video_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lines, ensure_ascii=False, indent=1), encoding="utf-8")
    return path, len(lines)


def load_transcript(video_id, out_dir="data/transcripts"):
    path = Path(out_dir) / f"{video_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))
