from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SongStatus(str, Enum):
    QUEUED = "queued"
    RESOLVING = "resolving"
    DOWNLOADING = "downloading"
    READY = "ready"
    PLAYING = "playing"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class Song:
    title: str
    page_url: str
    channel: Optional[str] = None
    duration: Optional[float] = None
    stream_url: Optional[str] = None
    local_path: Optional[str] = None
    source: Optional[str] = None  # e.g. "youtube", "spotify"
    status: SongStatus = SongStatus.QUEUED
    error: Optional[str] = None
    id: Optional[str] = field(default=None)

    @classmethod
    def from_ydl_entry(cls, entry: dict, source: str = "youtube") -> Song:
        """Build a Song from a yt-dlp info / flat-playlist entry."""
        return cls(
            id=entry.get("id"),
            title=entry.get("title") or "Unknown",
            page_url=entry.get("webpage_url") or entry.get("url") or "",
            channel=entry.get("channel") or entry.get("uploader"),
            duration=entry.get("duration"),
            stream_url=None,
            source=source,
            status=SongStatus.QUEUED,
        )

    def is_playable(self) -> bool:
        return self.status in {
            SongStatus.READY,
            SongStatus.PLAYING,
            SongStatus.DOWNLOADING,
        } and self.local_path is not None
