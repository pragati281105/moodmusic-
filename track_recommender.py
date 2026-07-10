import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Optional


class TrackSimilarityModel:
    """
    Picks the best next track based on available track metadata.
    Works even when Spotify audio_features endpoint is unavailable (403).
    Falls back to popularity + artist overlap + genre matching.
    """

    def _extract_feature_vector(self, features: Dict) -> Optional[np.ndarray]:
        """
        Build a feature vector from whatever is available.
        Audio features (tempo, energy etc) are used if present,
        otherwise falls back to metadata-based estimates.
        """
        try:
            # If real audio features exist, use them
            if "energy" in features and "valence" in features:
                vector = [
                    features.get("tempo", 120) / 200.0,      # normalize to 0-1
                    features.get("energy", 0.5),
                    features.get("valence", 0.5),
                    features.get("danceability", 0.5),
                    features.get("acousticness", 0.5),
                ]
            else:
                # Fallback — estimate from metadata
                popularity = features.get("popularity", 50) / 100.0
                duration   = min(features.get("duration_ms", 210000) / 300000.0, 1.0)
                explicit   = float(features.get("explicit", False))
                vector = [
                    popularity,
                    duration,
                    explicit,
                    popularity * 0.8,   # rough energy estimate
                    1.0 - explicit,     # rough acousticness estimate
                ]
            return np.array(vector, dtype=float)
        except Exception:
            return None

    def _artist_overlap_score(self, track1: Dict, track2: Dict) -> float:
        """Bonus score if tracks share an artist."""
        try:
            artists1 = {a.get("id") for a in track1.get("artists", []) if a.get("id")}
            artists2 = {a.get("id") for a in track2.get("artists", []) if a.get("id")}
            if artists1 & artists2:
                return 0.2   # same artist = big bonus
        except Exception:
            pass
        return 0.0

    def find_best_next_track(
        self,
        current_features: Dict,
        candidate_tracks: List[Dict],
        strategy: str = "smooth",
        current_track: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Given current track features and a list of candidates,
        return the best next track.

        candidate_tracks format:
          [{"track": <spotify track dict>, "features": <dict or None>}, ...]

        strategy:
          smooth      — most similar feel (default)
          energy_up   — gradually increase energy
          energy_down — gradually decrease energy
        """
        if not candidate_tracks:
            return None

        current_vec = self._extract_feature_vector(current_features)
        if current_vec is None:
            # No features at all — just return first candidate
            return candidate_tracks[0]["track"]

        scored = []
        for candidate in candidate_tracks:
            track = candidate.get("track", {})
            f     = candidate.get("features") or {}

            # Use track metadata as fallback if no audio features
            if not f:
                f = {
                    "popularity":   track.get("popularity", 50),
                    "duration_ms":  track.get("duration_ms", 210000),
                    "explicit":     track.get("explicit", False),
                }

            candidate_vec = self._extract_feature_vector(f)
            if candidate_vec is None:
                continue

            # Base cosine similarity
            sim = cosine_similarity(
                current_vec.reshape(1, -1),
                candidate_vec.reshape(1, -1)
            )[0][0]

            # Strategy adjustments
            if strategy == "energy_up":
                energy_now  = current_features.get("energy", f.get("popularity", 50) / 100.0)
                energy_next = f.get("energy", f.get("popularity", 50) / 100.0)
                sim += (energy_next - energy_now) * 0.3

            elif strategy == "energy_down":
                energy_now  = current_features.get("energy", f.get("popularity", 50) / 100.0)
                energy_next = f.get("energy", f.get("popularity", 50) / 100.0)
                sim += (energy_now - energy_next) * 0.3

            # Artist overlap bonus
            if current_track:
                sim += self._artist_overlap_score(current_track, track)

            scored.append((sim, candidate))

        if not scored:
            return None

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]["track"]

    def rank_candidates(
        self,
        current_features: Dict,
        candidate_tracks: List[Dict],
        strategy: str = "smooth",
        current_track: Optional[Dict] = None,
    ) -> List[Dict]:
        """Same as find_best_next_track but returns full ranked list."""
        if not candidate_tracks:
            return []

        current_vec = self._extract_feature_vector(current_features)
        if current_vec is None:
            return [c["track"] for c in candidate_tracks]

        scored = []
        for candidate in candidate_tracks:
            track = candidate.get("track", {})
            f     = candidate.get("features") or {}

            if not f:
                f = {
                    "popularity":  track.get("popularity", 50),
                    "duration_ms": track.get("duration_ms", 210000),
                    "explicit":    track.get("explicit", False),
                }

            candidate_vec = self._extract_feature_vector(f)
            if candidate_vec is None:
                continue

            sim = cosine_similarity(
                current_vec.reshape(1, -1),
                candidate_vec.reshape(1, -1)
            )[0][0]

            if strategy == "energy_up":
                energy_now  = current_features.get("energy", f.get("popularity", 50) / 100.0)
                energy_next = f.get("energy", f.get("popularity", 50) / 100.0)
                sim += (energy_next - energy_now) * 0.3

            elif strategy == "energy_down":
                energy_now  = current_features.get("energy", f.get("popularity", 50) / 100.0)
                energy_next = f.get("energy", f.get("popularity", 50) / 100.0)
                sim += (energy_now - energy_next) * 0.3

            if current_track:
                sim += self._artist_overlap_score(current_track, track)

            scored.append((sim, track))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored]