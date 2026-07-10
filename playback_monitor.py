import threading
import time
from typing import Optional, Callable, Dict
import spotipy


class PlaybackMonitor:
    """
    Runs in a background thread.
    Polls Spotify every 3 seconds.
    When a track is near its end (within threshold_ms), fires the transition callback.
    """

    def __init__(
        self,
        sp: spotipy.Spotify,
        on_transition: Callable[[Dict], None],  # called with current track info
        threshold_ms: int = 15000,              # trigger 15 seconds before end
        poll_interval: float = 3.0,
    ):
        self.sp              = sp
        self.on_transition   = on_transition
        self.threshold_ms    = threshold_ms
        self.poll_interval   = poll_interval

        self._thread: Optional[threading.Thread] = None
        self._stop_event     = threading.Event()
        self._fired_for_track: Optional[str] = None  # avoid double-firing

    def start(self):
        if self._thread and self._thread.is_alive():
            return  # already running
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def _run(self):
        while not self._stop_event.is_set():
            try:
                pb = self.sp.current_playback()

                if pb and pb.get("is_playing"):
                    item         = pb.get("item") or {}
                    track_id     = item.get("id")
                    duration_ms  = item.get("duration_ms", 0)
                    progress_ms  = pb.get("progress_ms", 0)
                    remaining_ms = duration_ms - progress_ms

                    # Fire transition callback when close to end
                    # and only once per track
                    if (
                        remaining_ms > 0
                        and remaining_ms <= self.threshold_ms
                        and track_id != self._fired_for_track
                    ):
                        self._fired_for_track = track_id
                        self.on_transition({
                            "track_id":    track_id,
                            "track_uri":   item.get("uri"),
                            "track_name":  item.get("name"),
                            "remaining_ms": remaining_ms,
                            "duration_ms": duration_ms,
                            "progress_ms": progress_ms,
                        })

            except Exception:
                pass  # network blip — just keep polling

            self._stop_event.wait(self.poll_interval)