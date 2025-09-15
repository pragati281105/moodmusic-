import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyPKCE
from spotipy.exceptions import SpotifyException
import pandas as pd
import json
import time
import random
from datetime import datetime
import os
from dotenv import load_dotenv
import base64
from typing import Dict, List, Optional, Tuple
from spotipy.cache_handler import CacheFileHandler

# Load environment variables
load_dotenv()

# Spotify Configuration
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

# Minimal required scopes for compliance
SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private playlist-read-collaborative user-read-email"

# Mood configurations
MOOD_CONFIGS = {
    "Happy": {
        "valence": 0.8,
        "energy": 0.7,
        "tempo": (120, 140),
        "genres": ["pop", "dance", "funk"],
        "description": "Upbeat and energetic tracks"
    },
    "Focused": {
        "valence": 0.5,
        "energy": 0.4,
        "tempo": (80, 120),
        "genres": ["ambient", "electronic", "instrumental"],
        "description": "Concentration-friendly music"
    },
    "Relaxed": {
        "valence": 0.6,
        "energy": 0.3,
        "tempo": (60, 100),
        "genres": ["chill", "acoustic", "jazz"],
        "description": "Calm and soothing tracks"
    },
    "Hype": {
        "valence": 0.9,
        "energy": 0.9,
        "tempo": (130, 180),
        "genres": ["hip-hop", "electronic", "rock"],
        "description": "High-energy party tracks"
    },
    "Sad": {
        "valence": 0.2,
        "energy": 0.3,
        "tempo": (60, 90),
        "genres": ["indie", "alternative", "blues"],
        "description": "Melancholic and emotional tracks"
    }
}

# DJ Interface Configuration
DJ_CONFIG = {
    "max_tempo_change": 0.3,  # 30% tempo change max
    "crossfade_duration": 3.0,  # 3 seconds crossfade
    "cue_points": 8,  # Number of cue points per track
    "beat_grid_resolution": 0.25  # Quarter beat resolution
}

class SpotifyManager:
    """Handles all Spotify API interactions with compliance"""
    
    def __init__(self):
        self.sp = None
        self.user_id = None
        self.device_id = None
        self._genre_seeds_cache: Optional[List[str]] = None
        
    @st.cache_resource(show_spinner=False)
    def get_spotify_instance(_self):
        """Get authenticated Spotify instance with proper error handling"""
        if not SPOTIPY_CLIENT_ID:
            return None
            
        try:
            auth_manager = SpotifyPKCE(
                client_id=SPOTIPY_CLIENT_ID,
                redirect_uri=SPOTIPY_REDIRECT_URI,
                scope=SCOPE,
                cache_handler=CacheFileHandler(cache_path=".spotipy_token_cache"),
                open_browser=True
            )
            
            sp = spotipy.Spotify(auth_manager=auth_manager, requests_timeout=20)
            
            # Test authentication
            user = sp.current_user()
            _self.user_id = user['id']
            
            return sp
            
        except Exception as e:
            # Don't show error here, let the main function handle it
            return None
    
    def get_available_devices(self):
        """Get available Spotify devices"""
        if not self.sp:
            return []
        
        try:
            devices = self.sp.devices()
            return devices.get('devices', [])
        except Exception as e:
            st.error(f"Error fetching devices: {e}")
            return []

    def start_playback_for_track(self, track_uri: str, device_id: Optional[str]) -> bool:
        """Start playback on a Spotify Connect device. Returns True on success."""
        if not self.sp or not track_uri:
            return False
        try:
            # Transfer to target device if provided
            if device_id:
                try:
                    self.sp.transfer_playback(device_id=device_id, force_play=True)
                except Exception:
                    pass
            self.sp.start_playback(device_id=device_id, uris=[track_uri])
            return True
        except SpotifyException as e:
            if e.http_status == 404:
                st.warning("No active device found. Open Spotify on any device and try again.")
            elif e.http_status == 403:
                st.warning("Playback requires a Spotify Premium account.")
            else:
                st.error(f"Playback error: {e}")
            return False
        except Exception as e:
            st.error(f"Playback error: {e}")
            return False
    
    def search_tracks(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for tracks with rate limiting"""
        if not self.sp:
            return []
        
        try:
            results = self.sp.search(q=query, type='track', limit=limit)
            return results.get('tracks', {}).get('items', [])
        except SpotifyException as e:
            if e.http_status == 429:  # Rate limited
                st.warning("⚠️ Rate limited. Please wait a moment before searching again.")
                time.sleep(1)
            else:
                st.error(f"Search error: {e}")
            return []
    
    def get_track_features(self, track_id: str) -> Optional[Dict]:
        """Get audio features for a track"""
        if not self.sp:
            return None
        
        try:
            features = self.sp.audio_features(track_id)
            return features[0] if features else None
        except Exception as e:
            st.error(f"Error getting track features: {e}")
            return None
    
    def get_valid_genre_seeds(self) -> List[str]:
        """Fetch and cache valid Spotify genre seeds"""
        if self._genre_seeds_cache is not None:
            return self._genre_seeds_cache
        try:
            seeds = self.sp.recommendation_genre_seeds()
            self._genre_seeds_cache = seeds.get('genres', [])
        except Exception:
            self._genre_seeds_cache = []
        return self._genre_seeds_cache

    def get_recommendations(self, mood_config: Dict, limit: int = 20) -> List[Dict]:
        """Get mood-based recommendations"""
        if not self.sp:
            return []
        
        # Validate seeds against Spotify's allowed list
        allowed = set(self.get_valid_genre_seeds())
        requested = [g for g in mood_config['genres'] if g in allowed]
        if not requested:
            # Safe defaults
            requested = [g for g in ["pop", "rock", "dance"] if g in allowed] or ["pop"]

        # Try with full constraints first, then progressively relax
        try_order = [
            dict(seed_genres=requested, target_valence=mood_config['valence'], target_energy=mood_config['energy'], min_tempo=mood_config['tempo'][0], max_tempo=mood_config['tempo'][1]),
            dict(seed_genres=requested, target_valence=mood_config['valence'], target_energy=mood_config['energy']),
            dict(seed_genres=requested),
            dict(seed_genres=["pop"])  # last resort
        ]

        for params in try_order:
            try:
                recommendations = self.sp.recommendations(limit=limit, **params)
                tracks = recommendations.get('tracks', [])
                if tracks:
                    return tracks
            except SpotifyException as e:
                # Show concise hint and continue to next fallback
                st.warning(f"Recommendation attempt failed ({e.http_status}). Retrying with simpler filters...")
            except Exception:
                continue
        # Final fallback: search-based generation filtered by audio features
        return self._search_based_fallback(mood_config, limit)

    def _search_based_fallback(self, mood_config: Dict, limit: int) -> List[Dict]:
        """Fallback when recommendations endpoint fails: use search + audio feature filtering"""
        queries = [
            " ".join(mood_config.get('genres', [])[:2]) or "pop",
            "mood " + (mood_config.get('description') or ""),
            mood_config.get('genres', ["pop"])[0]
        ]
        seen_ids: set = set()
        collected: List[Dict] = []
        for q in queries:
            try:
                results = self.sp.search(q=q.strip() or "pop", type='track', limit=50)
                items = results.get('tracks', {}).get('items', [])
                for t in items:
                    if t['id'] not in seen_ids:
                        collected.append(t)
                        seen_ids.add(t['id'])
                if len(collected) >= 100:
                    break
            except Exception:
                continue

        if not collected:
            return []

        # Filter by audio features
        ids = [t['id'] for t in collected]
        filtered: List[Dict] = []
        try:
            for i in range(0, len(ids), 100):
                batch_ids = ids[i:i+100]
                features = self.sp.audio_features(batch_ids) or []
                id_to_feat = {f['id']: f for f in features if f}
                for t in collected[i:i+100]:
                    f = id_to_feat.get(t['id'])
                    if not f:
                        continue
                    tempo_ok = mood_config['tempo'][0] <= f.get('tempo', 120) <= mood_config['tempo'][1]
                    energy_ok = abs(f.get('energy', 0.5) - mood_config['energy']) <= 0.3
                    valence_ok = abs(f.get('valence', 0.5) - mood_config['valence']) <= 0.3
                    if tempo_ok and energy_ok and valence_ok:
                        filtered.append(t)
        except Exception:
            # If feature fetch fails, return the first N from collected as a last resort
            filtered = collected

        return filtered[:limit]

class DJInterface:
    """Handles DJ mixing functionality"""
    
    def __init__(self, spotify_manager: SpotifyManager):
        self.spotify = spotify_manager
        self.current_track = None
        self.next_track = None
        self.tempo = 120.0
        self.volume = 0.8
        self.crossfade_position = 0.0
        self.active_device_id: Optional[str] = None
        self.target_volume_percent = 80
        self.volume_a_percent = 80
        self.volume_b_percent = 80
        self.enable_beat_fill = False
        self.beat_fill_pulses = 4
        
    def calculate_bpm_match(self, track1_features: Dict, track2_features: Dict) -> float:
        """Calculate BPM compatibility between two tracks"""
        if not track1_features or not track2_features:
            return 0.0
        
        tempo1 = track1_features.get('tempo', 120)
        tempo2 = track2_features.get('tempo', 120)
        
        # Calculate tempo ratio (closer to 1.0 is better)
        ratio = min(tempo1, tempo2) / max(tempo1, tempo2)
        return ratio
    
    def suggest_mix_point(self, track_features: Dict) -> float:
        """Suggest optimal mix-in point for a track"""
        if not track_features:
            return 0.0
        
        # Look for energy valleys or breakdowns
        energy = track_features.get('energy', 0.5)
        valence = track_features.get('valence', 0.5)
        
        # Prefer mixing in during lower energy sections
        if energy < 0.4:
            return 0.3  # 30% into track
        elif energy < 0.6:
            return 0.2  # 20% into track
        else:
            return 0.1  # 10% into track (intro)

    def fade_transition(self, from_uri: Optional[str], to_uri: str, device_id: Optional[str]) -> bool:
        """Perform a simple fade-out/fade-in using Spotify volume API"""
        spm = self.spotify
        if not spm or not spm.sp:
            return False
        try:
            # Capture device
            if device_id:
                self.active_device_id = device_id
            device = self.active_device_id
            # Fade out current
            try:
                for vol in range(int(self.volume * 100), 0, -5):
                    spm.sp.volume(vol, device_id=device)
                    time.sleep(0.06)
            except Exception:
                pass
            # Start next
            ok = spm.start_playback_for_track(to_uri, device)
            time.sleep(0.2)
            # Fade in
            try:
                target = int(self.volume * 100) if self.volume else self.target_volume_percent
                for vol in range(0, target + 1, 5):
                    spm.sp.volume(vol, device_id=device)
                    time.sleep(0.06)
            except Exception:
                pass
            return ok
        except Exception:
            return False

    def get_audio_analysis(self, track_id: str) -> Optional[Dict]:
        try:
            return self.spotify.sp.audio_analysis(track_id)
        except Exception:
            return None

    def get_current_playback_position_ms(self) -> Optional[int]:
        try:
            pb = self.spotify.sp.current_playback()
            if not pb:
                return None
            return pb.get('progress_ms')
        except Exception:
            return None

    def find_next_beat_after(self, analysis: Dict, after_ms: int) -> Optional[int]:
        if not analysis or 'beats' not in analysis:
            return None
        for beat in analysis['beats']:
            ts_ms = int(beat.get('start', 0.0) * 1000)
            if ts_ms > after_ms:
                return ts_ms
        return None

    def beat_matched_transition(self, current_track_id: Optional[str], next_track_uri: str, next_track_id: str, device_id: Optional[str], cue_point_ms: Optional[int], crossfade_ms: int = 2000) -> bool:
        spm = self.spotify
        if not spm or not spm.sp or not next_track_uri:
            return False
        try:
            device = device_id or self.active_device_id
            now_ms = self.get_current_playback_position_ms() or 0
            analysis = None
            if current_track_id:
                analysis = self.get_audio_analysis(current_track_id)
            beat_ms = self.find_next_beat_after(analysis, now_ms) if analysis else None
            # If we have a beat, wait until just before it to start fading
            if beat_ms:
                delay = max(0, (beat_ms - now_ms) / 1000.0 - (crossfade_ms / 2000.0))
                if delay > 0:
                    time.sleep(delay)
            # Optional beat fill pulses before transition (device-global volume pulses)
            if self.enable_beat_fill and self.beat_fill_pulses > 0:
                try:
                    base_vol = spm.sp.current_playback().get('device', {}).get('volume_percent', self.target_volume_percent)
                except Exception:
                    base_vol = self.target_volume_percent
                for _ in range(self.beat_fill_pulses):
                    try:
                        spm.sp.volume(max(0, int(base_vol * 0.6)), device_id=device)
                        time.sleep(0.08)
                        spm.sp.volume(min(100, int(base_vol)), device_id=device)
                        time.sleep(0.08)
                    except Exception:
                        break
            # Fade out
            try:
                start_vol = 0
                try:
                    start_vol = int(self.spotify.sp.current_playback().get('device',{}).get('volume_percent', self.target_volume_percent))
                except Exception:
                    start_vol = self.target_volume_percent
                end_vol = max(0, int(self.volume_a_percent))  # how low A should go at the end of fade
                step = max(1, int((start_vol - end_vol) / 20))
                for vol in range(start_vol, end_vol - 1, -step):
                    spm.sp.volume(max(0, vol), device_id=device)
                    time.sleep(crossfade_ms / 1000.0 / 20.0)
            except Exception:
                pass
            # Start next at cue point if provided
            start_pos = cue_point_ms or 0
            spm.sp.start_playback(device_id=device, uris=[next_track_uri], position_ms=start_pos)
            # Fade in
            try:
                target_b = max(0, min(100, int(self.volume_b_percent)))
                step_in = max(1, int(target_b / 20))
                for vol in range(end_vol, target_b + 1, step_in):
                    spm.sp.volume(min(100, vol), device_id=device)
                    time.sleep(crossfade_ms / 1000.0 / 20.0)
            except Exception:
                pass
            return True
        except Exception:
            return False

class MoodPlaylistGenerator:
    """Handles mood-based playlist generation"""
    
    def __init__(self, spotify_manager: SpotifyManager):
        self.spotify = spotify_manager
        self.current_mood = None
        self.playlist_tracks = []
        self.adaptation_history = []
    
    def generate_playlist(self, mood: str, user_feedback: Optional[Dict] = None) -> List[Dict]:
        """Generate mood-based playlist with optional adaptation"""
        if mood not in MOOD_CONFIGS:
            st.error(f"Unknown mood: {mood}")
            return []
        
        config = MOOD_CONFIGS[mood]
        self.current_mood = mood
        
        # Get initial recommendations
        tracks = self.spotify.get_recommendations(config, limit=20)
        
        # Adapt based on user feedback if available
        if user_feedback:
            tracks = self._adapt_playlist(tracks, user_feedback)
        
        self.playlist_tracks = tracks
        return tracks
    
    def _adapt_playlist(self, tracks: List[Dict], feedback: Dict) -> List[Dict]:
        """Adapt playlist based on user feedback"""
        # Simple adaptation: adjust based on liked/disliked tracks
        liked_genres = feedback.get('liked_genres', [])
        disliked_genres = feedback.get('disliked_genres', [])
        
        # Filter tracks based on feedback
        adapted_tracks = []
        for track in tracks:
            track_genres = [artist.get('genres', []) for artist in track.get('artists', [])]
            track_genres = [genre for genres in track_genres for genre in genres]
            
            # Skip if contains disliked genres
            if any(genre in disliked_genres for genre in track_genres):
                continue
            
            # Prioritize if contains liked genres
            if any(genre in liked_genres for genre in track_genres):
                adapted_tracks.insert(0, track)
            else:
                adapted_tracks.append(track)
        
        return adapted_tracks

def render_privacy_consent():
    """Render privacy policy and consent UI"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔒 Privacy & Consent")
    
    if st.sidebar.checkbox("I agree to the privacy policy", key="privacy_consent"):
        st.sidebar.success("✅ Privacy consent recorded")
        return True
    else:
        st.sidebar.warning("⚠️ Please accept privacy policy to continue")
        return False

def render_spotify_attribution():
    """Render required Spotify attribution"""
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 10px; background-color: #1DB954; border-radius: 5px; margin: 10px 0;">
            <img src="https://developer.spotify.com/assets/branding-guidelines/icon.png" width="20" height="20" style="vertical-align: middle;">
            <span style="color: white; margin-left: 5px;">Powered by Spotify</span>
        </div>
        """, unsafe_allow_html=True)

def main():
    """Main application"""
    st.set_page_config(
        page_title="MoodMusic - Smart DJ App",
        page_icon="🎧",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #1DB954, #1ed760);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .mode-selector {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .dj-deck {
        background-color: #2d2d2d;
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .track-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin: 5px 0;
        border-left: 4px solid #1DB954;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎧 MoodMusic</h1>
        <p>Smart DJ App - Mix, Create, and Adapt</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Privacy consent
    if not render_privacy_consent():
        st.stop()
    
    # Check credentials first
    if not SPOTIPY_CLIENT_ID:
        st.error("❌ Spotify credentials not configured")
        st.markdown("### 🔧 Setup Required")
        st.markdown("""
        **Please create a `.env` file with your Spotify credentials:**
        
        ```env
        SPOTIPY_CLIENT_ID=your_client_id_here
        # Optional override; default is http://127.0.0.1:8888/callback
        # SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
        ```
        
        **To get your credentials:**
        1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
        2. Click "Create App" or select existing app
        3. Fill in app details:
           - **App name**: `MoodMusic`
           - **App description**: `Smart DJ app with mood-based playlist generation`
           - **Website**: `http://localhost:8501`
           - **Redirect URI**: `http://127.0.0.1:8888/callback` (and also add `http://localhost:8888/callback`)
        4. Click "Save"
        5. Copy your **Client ID** and **Client Secret**
        6. Create a `.env` file in this directory with the credentials above
        
        **After creating the .env file, refresh this page.**
        """)
        st.stop()
    
    # Initialize managers
    spotify_manager = SpotifyManager()
    spotify_instance = spotify_manager.get_spotify_instance()
    
    if not spotify_instance:
        st.error("❌ Spotify authentication failed")
        st.markdown("### 🔧 Troubleshooting")
        st.markdown("""
        **Common issues and solutions:**
        
        1. **Check your .env file**:
           - Make sure it's in the same directory as this app
           - Verify there are no extra spaces or quotes around the values
           - Ensure the file is named exactly `.env` (with the dot)
        
        2. **Check your Spotify app settings**:
           - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
           - Click on your app
           - Click "Edit Settings"
           - Add these redirect URIs: `http://127.0.0.1:8888/callback` and `http://localhost:8888/callback`
        
        3. **Try clearing the cache**:
           - Delete the `.spotipy_token_cache` and `.spotipy_cache` files if they exist
           - Refresh this page
        
        4. **Verify your credentials**:
           - Make sure your Client ID and Secret are correct
           - Check that you copied them without any extra characters
        """)
        
        if st.button("🗑️ Clear Cache and Retry"):
            import os
            for cache_file in [".spotipy_token_cache", ".spotipy_cache"]:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            st.rerun()
        st.stop()
    
    spotify_manager.sp = spotify_instance
    dj_interface = DJInterface(spotify_manager)
    mood_generator = MoodPlaylistGenerator(spotify_manager)
    
    # Mode selection
    st.markdown("### 🎛️ Select Mode")
    mode = st.radio(
        "Choose your experience:",
        ["🎧 DJ Mode", "🎵 Mood Mode"],
        horizontal=True
    )
    
    if mode == "🎧 DJ Mode":
        render_dj_mode(dj_interface)
    else:
        render_mood_mode(mood_generator)
    
    # Required Spotify attribution
    render_spotify_attribution()

def render_dj_mode(dj_interface: DJInterface):
    """Render DJ mixing interface"""
    st.markdown("### 🎛️ DJ Mixing Console")
    
    # Device selector for Spotify Connect playback
    devices = dj_interface.spotify.get_available_devices()
    device_names = [f"{d.get('name','Unknown')} ({d.get('type','')})" for d in devices]
    device_ids = [d.get('id') for d in devices]
    selected_device = None
    if devices:
        idx = st.selectbox("Select playback device (Spotify app must be open):", list(range(len(device_names))), format_func=lambda i: device_names[i])
        selected_device = device_ids[idx]
        st.session_state['device_id'] = selected_device
        dj_interface.active_device_id = selected_device
    else:
        st.info("Open the Spotify app on your phone/desktop and come back to see devices.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🎵 Track A")
        search_query_a = st.text_input("Search Track A:", key="search_a", placeholder="Enter artist or song name")
        if search_query_a:
            tracks_a = dj_interface.spotify.search_tracks(search_query_a, limit=10)
            if tracks_a:
                for i, track in enumerate(tracks_a):
                    with st.container():
                        col_track, col_actions = st.columns([4, 2])
                        with col_track:
                            st.write(f"**{track['name']}** - {', '.join([a['name'] for a in track['artists']])}")
                            st.write(f"Duration: {track['duration_ms'] // 1000 // 60}:{track['duration_ms'] // 1000 % 60:02d}")
                        with col_actions:
                            if st.button("Play A", key=f"playA_{i}"):
                                st.session_state['track_a'] = track
                                dj_interface.current_track = track
                                uri = track.get('uri')
                                if uri:
                                    dj_interface.spotify.start_playback_for_track(uri, selected_device)
                            if st.button("Set A", key=f"setA_{i}"):
                                st.session_state['track_a'] = track
                                dj_interface.current_track = track

        st.markdown("#### 🎵 Track B")
        search_query_b = st.text_input("Search Track B:", key="search_b", placeholder="Enter artist or song name")
        if search_query_b:
            tracks_b = dj_interface.spotify.search_tracks(search_query_b, limit=10)
            if tracks_b:
                for i, track in enumerate(tracks_b):
                    with st.container():
                        col_track, col_actions = st.columns([4, 2])
                        with col_track:
                            st.write(f"**{track['name']}** - {', '.join([a['name'] for a in track['artists']])}")
                            st.write(f"Duration: {track['duration_ms'] // 1000 // 60}:{track['duration_ms'] // 1000 % 60:02d}")
                        with col_actions:
                            if st.button("Play B", key=f"playB_{i}"):
                                st.session_state['track_b'] = track
                                dj_interface.next_track = track
                                uri = track.get('uri')
                                if uri:
                                    dj_interface.spotify.start_playback_for_track(uri, selected_device)
                            if st.button("Set B", key=f"setB_{i}"):
                                st.session_state['track_b'] = track
                                dj_interface.next_track = track
    
    with col2:
        st.markdown("#### 🎚️ Mixing Controls")
        
        # Tempo control
        tempo = st.slider("Tempo (BPM)", 60, 200, 120, key="tempo_slider")
        dj_interface.tempo = tempo
        
        # Volume control (global)
        volume = st.slider("Volume", 0.0, 1.0, 0.8, key="volume_slider")
        dj_interface.volume = volume
        dj_interface.target_volume_percent = int(volume * 100)

        col_vol_a, col_vol_b = st.columns(2)
        with col_vol_a:
            vol_a = st.slider("Track A end volume", 0, 100, 0, key="vol_a_slider")
            dj_interface.volume_a_percent = vol_a
        with col_vol_b:
            vol_b = st.slider("Track B target volume", 0, 100, int(volume * 100), key="vol_b_slider")
            dj_interface.volume_b_percent = vol_b
        
        # Crossfade control
        crossfade = st.slider("Crossfade", 0.0, 1.0, 0.2, key="crossfade_slider")
        dj_interface.crossfade_position = crossfade
        crossfade_ms = int(2000 + crossfade * 6000)  # 2s to 8s
        
        # Cue points and beat-matched transition
        st.markdown("#### 🎯 Cue & Beat-Matched Mix")
        cue_sec = st.number_input("Cue point for next track (seconds)", min_value=0, max_value=600, value=0, step=1)
        st.checkbox("Enable beat fill before transition", value=False, key="beat_fill_checkbox")
        dj_interface.enable_beat_fill = st.session_state.get('beat_fill_checkbox', False)
        if dj_interface.enable_beat_fill:
            dj_interface.beat_fill_pulses = st.slider("Beat fill pulses", 1, 8, 4, key="beat_fill_pulses")
        if st.button("Beat-Match Mix A → B", key="beat_match_btn"):
            track_a = st.session_state.get('track_a') or dj_interface.current_track
            track_b = st.session_state.get('track_b') or dj_interface.next_track
            if track_a and track_b:
                uri_b = track_b.get('uri')
                id_a = track_a.get('id') if track_a else None
                id_b = track_b.get('id') if track_b else None
                ok = dj_interface.beat_matched_transition(id_a, uri_b, id_b, st.session_state.get('device_id'), int(cue_sec * 1000), crossfade_ms)
                if ok:
                    st.success("Beat-matched transition triggered from A to B")
                else:
                    st.warning("Could not perform transition. Ensure a device is active and both tracks are set.")
        
        # Mix suggestions
        if dj_interface.current_track and dj_interface.next_track:
            st.markdown("#### 💡 Mix Suggestions")
            features1 = dj_interface.spotify.get_track_features(dj_interface.current_track['id'])
            features2 = dj_interface.spotify.get_track_features(dj_interface.next_track['id'])
            
            if features1 and features2:
                bpm_match = dj_interface.calculate_bpm_match(features1, features2)
                mix_point = dj_interface.suggest_mix_point(features2)
                
                st.write(f"BPM Compatibility: {bpm_match:.2f}")
                st.write(f"Suggested mix-in: {mix_point:.1%} into track")

def render_mood_mode(mood_generator: MoodPlaylistGenerator):
    """Render mood-based playlist interface"""
    st.markdown("### 🎵 Mood-Based Playlist Generator")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### 🎭 Select Mood")
        mood = st.selectbox("Choose your mood:", list(MOOD_CONFIGS.keys()))
        
        if mood:
            config = MOOD_CONFIGS[mood]
            st.info(f"**{config['description']}**")
            st.write(f"Valence: {config['valence']}")
            st.write(f"Energy: {config['energy']}")
            st.write(f"Tempo: {config['tempo'][0]}-{config['tempo'][1]} BPM")
            st.write(f"Genres: {', '.join(config['genres'])}")
        
        # User feedback
        st.markdown("#### 💭 Feedback")
        liked_genres = st.multiselect("Liked genres:", ["pop", "rock", "electronic", "jazz", "hip-hop", "classical"])
        disliked_genres = st.multiselect("Disliked genres:", ["pop", "rock", "electronic", "jazz", "hip-hop", "classical"])
        
        if st.button("🎵 Generate Playlist", type="primary"):
            feedback = {
                'liked_genres': liked_genres,
                'disliked_genres': disliked_genres
            }
            tracks = mood_generator.generate_playlist(mood, feedback)
            st.session_state['generated_tracks'] = tracks
            st.session_state['current_mood'] = mood
    
    with col2:
        st.markdown("#### 🎶 Generated Playlist")
        
        if 'generated_tracks' in st.session_state and st.session_state['generated_tracks']:
            tracks = st.session_state['generated_tracks']
            mood = st.session_state.get('current_mood', 'Unknown')
            
            st.success(f"Generated {len(tracks)} tracks for {mood} mood")
            
            for i, track in enumerate(tracks):
                with st.container():
                    col_track, col_play, col_info = st.columns([3, 1, 1])
                    
                    with col_track:
                        st.write(f"**{i+1}. {track['name']}**")
                        st.write(f"by {', '.join([a['name'] for a in track['artists']])}")
                    
                    with col_play:
                        if st.button("▶️", key=f"play_track_{i}"):
                            preview = track.get('preview_url')
                            track_uri = track.get('uri')
                            played = False
                            if preview:
                                st.audio(preview)
                                played = True
                            if not played and track_uri:
                                # Try device from session if set during DJ mode
                                device_id = st.session_state.get('device_id')
                                # Simple fade from whatever is playing
                                played = DJInterface(mood_generator.spotify).fade_transition(None, track_uri, device_id)
                            if played:
                                st.success(f"Playing: {track['name']}")
                            else:
                                st.warning("No preview available and no active Spotify device. Open Spotify and try again.")
                    
                    with col_info:
                        if st.button("ℹ️", key=f"info_track_{i}"):
                            features = mood_generator.spotify.get_track_features(track['id'])
                            if features:
                                st.write(f"Tempo: {features.get('tempo', 'N/A')} BPM")
                                st.write(f"Energy: {features.get('energy', 'N/A'):.2f}")
                                st.write(f"Valence: {features.get('valence', 'N/A'):.2f}")
        else:
            st.info("Select a mood and click 'Generate Playlist' to get started!")

if __name__ == "__main__":
    main()