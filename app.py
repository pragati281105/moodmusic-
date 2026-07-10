import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyPKCE
from spotipy.exceptions import SpotifyException
import pandas as pd
import sqlite3
import time
import threading
from datetime import datetime
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional, Tuple
from spotipy.cache_handler import CacheFileHandler

from config import MOOD_CONFIGS, DJ_CONFIG
from track_recommender import TrackSimilarityModel
from playback_monitor import PlaybackMonitor
load_dotenv()

SPOTIPY_CLIENT_ID     = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI  = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

SCOPE = (
    "user-read-playback-state user-modify-playback-state "
    "user-read-currently-playing playlist-read-private "
    "playlist-read-collaborative user-read-email"
)

DB_PATH = "moodmusic.db"

# ─────────────────────────────────────────────────────
# GLOBAL CSS — injected once at startup
# ─────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');

/* ── Root tokens ── */
:root {
  --void:    #0A0A0F;
  --deep:    #12121C;
  --card:    #1A1A2E;
  --card2:   #16213E;
  --violet:  #8B5CF6;
  --violet2: #6D28D9;
  --cyan:    #06B6D4;
  --pink:    #EC4899;
  --emerald: #10B981;
  --amber:   #F59E0B;
  --text:    #E2E8F0;
  --muted:   #94A3B8;
  --border:  rgba(139,92,246,0.18);
}

/* ── Base reset ── */
html, body, [class*="css"] {
  font-family: 'Space Grotesk', sans-serif !important;
  background-color: var(--void) !important;
  color: var(--text) !important;
}

.main .block-container {
  padding-top: 1rem;
  padding-bottom: 2rem;
  max-width: 1400px;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--void); }
::-webkit-scrollbar-thumb { background: var(--violet2); border-radius: 3px; }

/* ════════════════════════════════════════
   HERO HEADER — animated vinyl gradient
   ════════════════════════════════════════ */
.groove-header {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  padding: 2.5rem 2rem;
  margin-bottom: 1.5rem;
  background: radial-gradient(ellipse at 20% 50%, rgba(139,92,246,0.35) 0%, transparent 60%),
              radial-gradient(ellipse at 80% 30%, rgba(6,182,212,0.25) 0%, transparent 55%),
              radial-gradient(ellipse at 50% 80%, rgba(236,72,153,0.2) 0%, transparent 50%),
              linear-gradient(135deg, #12121C 0%, #0A0A0F 100%);
  border: 1px solid var(--border);
  text-align: center;
}
.groove-header::before {
  content: '';
  position: absolute;
  width: 320px; height: 320px;
  border-radius: 50%;
  top: -100px; right: -80px;
  background: conic-gradient(from 0deg, #8B5CF6, #06B6D4, #EC4899, #8B5CF6);
  opacity: 0.12;
  animation: spin 12s linear infinite;
}
.groove-header::after {
  content: '';
  position: absolute;
  width: 200px; height: 200px;
  border-radius: 50%;
  bottom: -60px; left: -40px;
  background: conic-gradient(from 180deg, #06B6D4, #8B5CF6, #10B981, #06B6D4);
  opacity: 0.1;
  animation: spin 18s linear infinite reverse;
}
@keyframes spin { to { transform: rotate(360deg); } }

.groove-title {
  font-size: 3rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #fff 30%, #8B5CF6 60%, #06B6D4 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  line-height: 1.1;
}
.groove-subtitle {
  color: var(--muted);
  font-size: 1rem;
  font-weight: 400;
  margin-top: 0.5rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

/* ── Waveform decoration ── */
.waveform {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  margin-top: 1rem;
}
.waveform span {
  display: inline-block;
  width: 3px;
  border-radius: 3px;
  background: var(--violet);
  animation: wave 1.2s ease-in-out infinite;
}
.waveform span:nth-child(1)  { height: 8px;  animation-delay: 0s; }
.waveform span:nth-child(2)  { height: 20px; animation-delay: .1s; background: var(--cyan); }
.waveform span:nth-child(3)  { height: 32px; animation-delay: .2s; }
.waveform span:nth-child(4)  { height: 14px; animation-delay: .3s; background: var(--pink); }
.waveform span:nth-child(5)  { height: 28px; animation-delay: .4s; }
.waveform span:nth-child(6)  { height: 10px; animation-delay: .5s; background: var(--cyan); }
.waveform span:nth-child(7)  { height: 22px; animation-delay: .6s; }
.waveform span:nth-child(8)  { height: 36px; animation-delay: .7s; background: var(--pink); }
.waveform span:nth-child(9)  { height: 18px; animation-delay: .8s; }
.waveform span:nth-child(10) { height: 8px;  animation-delay: .9s; background: var(--cyan); }
@keyframes wave {
  0%, 100% { transform: scaleY(1);   opacity: 0.7; }
  50%       { transform: scaleY(1.8); opacity: 1;   }
}

/* ════════════════════════════════════════
   SIDEBAR
   ════════════════════════════════════════ */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0D0D1A 0%, #0A0A0F 100%) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stMarkdown h3 {
  color: var(--violet) !important;
  font-size: 0.75rem !important;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 600;
}

/* ════════════════════════════════════════
   MODE NAV TABS
   ════════════════════════════════════════ */
.mode-nav {
  display: flex;
  gap: 8px;
  margin-bottom: 1.5rem;
  background: var(--deep);
  border-radius: 12px;
  padding: 6px;
  border: 1px solid var(--border);
}
.mode-tab {
  flex: 1;
  text-align: center;
  padding: 10px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.9rem;
  color: var(--muted);
  transition: all 0.2s ease;
  border: 1px solid transparent;
}
.mode-tab.active {
  background: linear-gradient(135deg, var(--violet2), var(--violet));
  color: white;
  border-color: rgba(139,92,246,0.5);
  box-shadow: 0 0 20px rgba(139,92,246,0.3);
}

/* ════════════════════════════════════════
   SECTION HEADERS
   ════════════════════════════════════════ */
.section-label {
  font-size: 0.65rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--violet);
  margin-bottom: 0.75rem;
}
.section-title {
  font-size: 1.4rem;
  font-weight: 700;
  color: white;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ════════════════════════════════════════
   MOOD PILL SELECTOR
   ════════════════════════════════════════ */
.mood-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 1.5rem;
}
.mood-pill {
  padding: 14px 12px;
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.95rem;
  border: 1.5px solid transparent;
  transition: all 0.25s ease;
  line-height: 1.3;
}
.mood-pill.happy   { background: rgba(245,158,11,0.12); border-color: rgba(245,158,11,0.35); color: #FCD34D; }
.mood-pill.chill   { background: rgba(6,182,212,0.12);  border-color: rgba(6,182,212,0.35);  color: #67E8F9; }
.mood-pill.workout { background: rgba(236,72,153,0.12); border-color: rgba(236,72,153,0.35); color: #F9A8D4; }
.mood-pill.focus   { background: rgba(139,92,246,0.12); border-color: rgba(139,92,246,0.35); color: #C4B5FD; }
.mood-pill.sad     { background: rgba(99,102,241,0.12); border-color: rgba(99,102,241,0.35); color: #A5B4FC; }
.mood-pill.party   { background: rgba(16,185,129,0.12); border-color: rgba(16,185,129,0.35); color: #6EE7B7; }
.mood-pill.romance { background: rgba(244,63,94,0.12);  border-color: rgba(244,63,94,0.35);  color: #FDA4AF; }
.mood-pill.sleep   { background: rgba(51,65,85,0.3);    border-color: rgba(148,163,184,0.2); color: #CBD5E1; }
.mood-pill.selected {
  box-shadow: 0 0 0 2px white, 0 0 24px rgba(139,92,246,0.5);
  transform: translateY(-2px);
}

/* ════════════════════════════════════════
   TRACK CARDS
   ════════════════════════════════════════ */
.track-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 8px;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}
.track-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, var(--violet), var(--cyan));
  border-radius: 3px 0 0 3px;
}
.track-card:hover {
  border-color: rgba(139,92,246,0.45);
  background: var(--card2);
  transform: translateX(2px);
}
.track-art {
  width: 48px; height: 48px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--violet2), var(--cyan));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.track-info { flex: 1; min-width: 0; }
.track-name {
  font-weight: 600;
  font-size: 0.9rem;
  color: white;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.track-artist {
  font-size: 0.78rem;
  color: var(--muted);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.track-badges {
  display: flex;
  gap: 5px;
  margin-top: 5px;
  flex-wrap: wrap;
}
.badge {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 20px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.badge-tempo   { background: rgba(245,158,11,0.15); color: #FCD34D; border: 1px solid rgba(245,158,11,0.3); }
.badge-energy  { background: rgba(236,72,153,0.15); color: #F9A8D4; border: 1px solid rgba(236,72,153,0.3); }
.badge-valence { background: rgba(16,185,129,0.15); color: #6EE7B7; border: 1px solid rgba(16,185,129,0.3); }
.badge-bpm     { background: rgba(6,182,212,0.15);  color: #67E8F9; border: 1px solid rgba(6,182,212,0.3);  }

/* ════════════════════════════════════════
   DJ CONSOLE
   ════════════════════════════════════════ */
.dj-console {
  background: linear-gradient(135deg, #0D0D1A 0%, #12121C 100%);
  border: 1px solid rgba(139,92,246,0.25);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 1rem;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 0 40px rgba(139,92,246,0.08);
}
.dj-deck {
  background: rgba(10,10,20,0.6);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 16px;
}
.dj-label {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  margin-bottom: 10px;
}
.dj-label.deck-a { color: var(--cyan); }
.dj-label.deck-b { color: var(--pink); }

/* ════════════════════════════════════════
   STAT CARDS / METRICS
   ════════════════════════════════════════ */
.stat-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 20px;
  text-align: center;
}
.stat-value {
  font-size: 2rem;
  font-weight: 700;
  background: linear-gradient(135deg, var(--violet), var(--cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.1;
}
.stat-label {
  font-size: 0.72rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 4px;
}

/* ════════════════════════════════════════
   NOW PLAYING BAR
   ════════════════════════════════════════ */
.now-playing-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  background: linear-gradient(90deg, rgba(139,92,246,0.12), rgba(6,182,212,0.08));
  border: 1px solid rgba(139,92,246,0.3);
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 1.2rem;
}
.now-playing-pulse {
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--emerald);
  box-shadow: 0 0 10px var(--emerald);
  animation: pulse 1.5s ease-in-out infinite;
  flex-shrink: 0;
}
@keyframes pulse {
  0%, 100% { transform: scale(1);   opacity: 1; }
  50%       { transform: scale(1.4); opacity: 0.7; }
}
.now-playing-text { font-weight: 600; font-size: 0.9rem; }
.now-playing-artist { color: var(--muted); font-size: 0.8rem; }

/* ════════════════════════════════════════
   SLIDERS & BUTTONS
   ════════════════════════════════════════ */
.stSlider [data-baseweb="slider"] { padding: 0 !important; }
.stSlider [data-baseweb="slider"] [role="slider"] {
  background: var(--violet) !important;
  border-color: var(--violet2) !important;
  box-shadow: 0 0 8px rgba(139,92,246,0.6) !important;
}
.stSlider [data-baseweb="slider"] [data-testid="stThumbValue"] {
  background: var(--violet2) !important;
  color: white !important;
  font-family: 'Space Grotesk', sans-serif !important;
}
div[data-baseweb="slider"] div[role="progressbar"] {
  background: linear-gradient(90deg, var(--violet2), var(--cyan)) !important;
}

.stButton > button {
  background: linear-gradient(135deg, var(--violet2), var(--violet)) !important;
  color: white !important;
  border: none !important;
  border-radius: 8px !important;
  font-family: 'Space Grotesk', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.85rem !important;
  padding: 0.45rem 1.1rem !important;
  transition: all 0.2s ease !important;
  box-shadow: 0 0 12px rgba(139,92,246,0.25) !important;
}
.stButton > button:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 0 20px rgba(139,92,246,0.5) !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--violet2), var(--pink)) !important;
  box-shadow: 0 0 20px rgba(236,72,153,0.3) !important;
}

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
  background: rgba(26,26,46,0.9) !important;
  border: 1px solid rgba(139,92,246,0.25) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
  font-family: 'Space Grotesk', sans-serif !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
  border-color: var(--violet) !important;
  box-shadow: 0 0 0 2px rgba(139,92,246,0.2) !important;
}

/* ── Selectbox ── */
.stSelectbox [data-baseweb="select"] > div {
  background: rgba(26,26,46,0.9) !important;
  border: 1px solid rgba(139,92,246,0.25) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
}

/* ── Multiselect ── */
.stMultiSelect [data-baseweb="select"] > div {
  background: rgba(26,26,46,0.9) !important;
  border: 1px solid rgba(139,92,246,0.25) !important;
  border-radius: 8px !important;
}

/* ── Toggle ── */
.stToggle label { color: var(--text) !important; }

/* ── Radio ── */
.stRadio [data-testid="stWidgetLabel"] { color: var(--muted) !important; }

/* ── Expander ── */
.streamlit-expanderHeader {
  background: var(--card) !important;
  border-radius: 8px !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
}

/* ── Dataframe ── */
.stDataFrame { border-radius: 10px; overflow: hidden; }
[data-testid="stDataFrameResizable"] {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
}

/* ── Alerts / info boxes ── */
.stAlert {
  border-radius: 10px !important;
  border-left: 3px solid var(--violet) !important;
  background: rgba(139,92,246,0.08) !important;
}
.stSuccess {
  border-left-color: var(--emerald) !important;
  background: rgba(16,185,129,0.08) !important;
}
.stWarning {
  border-left-color: var(--amber) !important;
  background: rgba(245,158,11,0.08) !important;
}
.stError {
  border-left-color: var(--pink) !important;
  background: rgba(236,72,153,0.08) !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] { color: var(--violet) !important; }

/* ── Metrics ── */
[data-testid="stMetric"] {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  padding: 12px 16px !important;
}
[data-testid="stMetricValue"] {
  color: var(--violet) !important;
  font-family: 'Space Grotesk', sans-serif !important;
}

/* ── Spotify attribution ── */
.spotify-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: linear-gradient(135deg, #1DB954, #1ed760);
  color: white !important;
  padding: 10px 24px;
  border-radius: 24px;
  font-weight: 600;
  font-size: 0.85rem;
  margin: 1.5rem auto 0;
  width: fit-content;
  box-shadow: 0 0 24px rgba(29,185,84,0.35);
}

/* ── Sidebar consent ── */
.privacy-box {
  background: rgba(139,92,246,0.08);
  border: 1px solid rgba(139,92,246,0.25);
  border-radius: 10px;
  padding: 12px;
  margin-top: 8px;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Checkbox ── */
.stCheckbox label { color: var(--text) !important; }

/* ── SQL highlight ── */
.sql-box {
  background: rgba(6,182,212,0.05);
  border: 1px solid rgba(6,182,212,0.2);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 1rem;
}

/* ── BPM compat bar ── */
.compat-bar {
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(90deg, var(--pink), var(--violet), var(--emerald));
  margin-top: 4px;
}

/* ── Labels in sidebar ── */
[data-testid="stSidebar"] label {
  color: var(--muted) !important;
  font-size: 0.82rem !important;
}
</style>
"""


# ─────────────────────────────────────────────────────
# Cached Spotify factory
# ─────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _get_spotify_instance():
    if not SPOTIPY_CLIENT_ID:
        return None, None
    try:
        auth_manager = SpotifyPKCE(
            client_id=SPOTIPY_CLIENT_ID,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=SCOPE,
            cache_handler=CacheFileHandler(cache_path=".spotipy_token_cache"),
            open_browser=True,
        )
        sp = spotipy.Spotify(auth_manager=auth_manager, requests_timeout=20)
        user = sp.current_user()
        return sp, user["id"]
    except Exception:
        return None, None


def check_deprecated_endpoints(sp) -> dict:
    status = {"audio_features": False, "recommendations": False}
    try:
        result = sp.audio_features("5ChkMS8OtdzJeqyybCc9R5")
        status["audio_features"] = bool(result and result[0])
    except Exception:
        pass
    try:
        result = sp.recommendations(seed_genres=["pop"], limit=1)
        status["recommendations"] = bool(result and result.get("tracks"))
    except Exception:
        pass
    return status


# ─────────────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────────────
def init_database():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tracks (
            id TEXT PRIMARY KEY,
            name TEXT, artist TEXT, album TEXT,
            duration_ms INTEGER, popularity INTEGER,
            preview_url TEXT, uri TEXT,
            tempo REAL, energy REAL, valence REAL,
            mood TEXT,
            language TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT, result_count INTEGER,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Lightweight migration: add `language` column if this DB pre-dates this feature.
    cur.execute("PRAGMA table_info(tracks)")
    existing_cols = {row[1] for row in cur.fetchall()}
    if "language" not in existing_cols:
        try:
            cur.execute("ALTER TABLE tracks ADD COLUMN language TEXT")
        except Exception:
            pass
    conn.commit()
    conn.close()


class SQLQueryManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def execute_query(self, query: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        try:
            conn    = sqlite3.connect(self.db_path)
            cur     = conn.cursor()
            q_upper = query.strip().upper()
            if q_upper.startswith("SELECT") or q_upper.startswith("WITH"):
                df = pd.read_sql_query(query, conn)
                cur.execute("INSERT INTO query_history (query, result_count) VALUES (?, ?)", (query, len(df)))
                conn.commit(); conn.close()
                return df, None
            else:
                cur.execute(query)
                conn.commit()
                affected = cur.rowcount
                cur.execute("INSERT INTO query_history (query, result_count) VALUES (?, ?)", (query, affected))
                conn.commit(); conn.close()
                return None, f"✅ Query executed. {affected} rows affected."
        except Exception as e:
            return None, f"❌ SQL Error: {e}"

    def save_track_to_db(self, track: Dict, mood: str, features: Optional[Dict] = None,
                         language: str = "Any") -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            artist_names = ", ".join([a.get("name", "Unknown") for a in track.get("artists", [])])
            album_name   = (track.get("album") or {}).get("name", "")
            cur.execute("""
                INSERT OR REPLACE INTO tracks
                    (id, name, artist, album, duration_ms, popularity,
                     preview_url, uri, tempo, energy, valence, mood, language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                track["id"], track.get("name", ""), artist_names, album_name,
                track.get("duration_ms", 0), track.get("popularity", 0),
                track.get("preview_url", ""), track.get("uri", ""),
                (features or {}).get("tempo"), (features or {}).get("energy"),
                (features or {}).get("valence"), mood, language,
            ))
            conn.commit(); conn.close()
            return True
        except Exception:
            return False

    def get_query_history(self, limit: int = 10) -> pd.DataFrame:
        try:
            conn = sqlite3.connect(self.db_path)
            df   = pd.read_sql_query(
                f"SELECT * FROM query_history ORDER BY executed_at DESC LIMIT {limit}", conn)
            conn.close()
            return df
        except Exception:
            return pd.DataFrame()

    def get_stats(self) -> Dict:
        try:
            conn = sqlite3.connect(self.db_path)
            cur  = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tracks")
            total_tracks = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM query_history")
            total_queries = cur.fetchone()[0]
            cur.execute("SELECT mood, COUNT(*) FROM tracks GROUP BY mood ORDER BY 2 DESC LIMIT 1")
            res = cur.fetchone()
            conn.close()
            return {"total_tracks": total_tracks, "total_queries": total_queries,
                    "popular_mood": res[0] if res else "N/A"}
        except Exception:
            return {}


# ─────────────────────────────────────────────────────
# Language support
# ─────────────────────────────────────────────────────
LANGUAGE_OPTIONS = ["Any", "English", "Hindi", "Tamil", "Telugu", "Malayalam", "Punjabi", "Bengali"]

LANGUAGE_SEARCH = {
    "Any":       "",
    "English":   "english",
    "Hindi":     "bollywood",
    "Tamil":     "tamil",
    "Telugu":    "telugu",
    "Malayalam": "malayalam",
    "Punjabi":   "punjabi",
    "Bengali":   "bengali",
}

LANGUAGE_ARTISTS = {
    "Hindi":     ["Arijit Singh", "Pritam", "Shreya Ghoshal"],
    "Tamil":     ["Anirudh Ravichander", "A.R. Rahman"],
    "Telugu":    ["Sid Sriram", "Thaman S"],
    "Punjabi":   ["AP Dhillon", "Karan Aujla"],
    "Malayalam": ["Sushin Shyam", "Vineeth Sreenivasan"],
    "Bengali":   ["Anupam Roy", "Rupam Islam"],
}


# ─────────────────────────────────────────────────────
# SpotifyManager
# ─────────────────────────────────────────────────────
class SpotifyManager:
    def __init__(self):
        self.sp, self.user_id = _get_spotify_instance()
        self.device_id        = None
        self._genre_seeds_cache: Optional[List[str]] = None

    def get_available_devices(self):
        if not self.sp: return []
        try:
            return self.sp.devices().get("devices", [])
        except Exception as e:
            st.error(f"Error fetching devices: {e}")
            return []

    def start_playback_for_track(self, track_uri: str, device_id: Optional[str]) -> bool:
        if not self.sp or not track_uri: return False
        try:
            if device_id:
                try: self.sp.transfer_playback(device_id=device_id, force_play=True)
                except Exception: pass
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
        if not self.sp: return []
        try:
            results = self.sp.search(q=query, type="track", limit=limit)
            return results.get("tracks", {}).get("items", [])
        except SpotifyException as e:
            if e.http_status == 429:
                st.warning("⚠️ Rate limited. Please wait a moment before searching again.")
                time.sleep(1)
            else:
                st.error(f"Search error: {e}")
            return []

    def get_track_features(self, track_id: str) -> Optional[Dict]:
        if not self.sp: return None
        if not st.session_state.get("api_status", {}).get("audio_features", True): return None
        try:
            features = self.sp.audio_features(track_id)
            return features[0] if features else None
        except Exception:
            return None

    def get_valid_genre_seeds(self) -> List[str]:
        if self._genre_seeds_cache is not None: return self._genre_seeds_cache
        try:
            seeds = self.sp.recommendation_genre_seeds()
            self._genre_seeds_cache = seeds.get("genres", [])
        except Exception:
            self._genre_seeds_cache = []
        return self._genre_seeds_cache

    def get_recommendations(self, mood_config: Dict, limit: int = 20) -> List[Dict]:
        if not self.sp: return []
        if not st.session_state.get("api_status", {}).get("recommendations", True):
            st.info("Spotify recommendations endpoint unavailable. Using search-based fallback.")
            return self._search_based_fallback(mood_config, limit)

        allowed   = set(self.get_valid_genre_seeds())
        requested = [g for g in mood_config["genres"] if g in allowed]
        if not requested:
            requested = [g for g in ["pop", "rock", "dance"] if g in allowed] or ["pop"]

        try_order = [
            dict(seed_genres=requested, target_valence=mood_config["valence"],
                 target_energy=mood_config["energy"], min_tempo=mood_config["tempo"][0],
                 max_tempo=mood_config["tempo"][1]),
            dict(seed_genres=requested, target_valence=mood_config["valence"],
                 target_energy=mood_config["energy"]),
            dict(seed_genres=requested),
            dict(seed_genres=["pop"]),
        ]

        attempts_failed = 0
        for params in try_order:
            try:
                rec    = self.sp.recommendations(limit=limit, **params)
                tracks = rec.get("tracks", [])
                if tracks:
                    if attempts_failed > 0:
                        st.info("Used relaxed filters to find matching tracks.")
                    return tracks
            except Exception:
                attempts_failed += 1

        st.warning("Spotify recommendations unavailable. Using search-based fallback.")
        return self._search_based_fallback(mood_config, limit)

    def _search_based_fallback(self, mood_config: Dict, limit: int) -> List[Dict]:
        queries = [
            " ".join(mood_config.get("genres", [])[:2]) or "pop",
            "mood " + (mood_config.get("description") or ""),
            (mood_config.get("genres") or ["pop"])[0],
        ]
        seen_ids: set = set()
        collected: List[Dict] = []
        for q in queries:
            try:
                items = self.sp.search(q=q.strip() or "pop", type="track", limit=50
                        ).get("tracks", {}).get("items", [])
                for t in items:
                    track_id = t.get("id")
                    if track_id and track_id not in seen_ids:
                        collected.append(t); seen_ids.add(track_id)
                if len(collected) >= 100: break
            except Exception:
                continue

        if not collected: return []
        if not st.session_state.get("api_status", {}).get("audio_features", True):
            return collected[:limit]

        ids = [t["id"] for t in collected]
        filtered: List[Dict] = []
        try:
            for i in range(0, len(ids), 100):
                batch    = ids[i : i + 100]
                features = self.sp.audio_features(batch) or []
                id_to_f  = {f["id"]: f for f in features if f}
                for t in collected[i : i + 100]:
                    f = id_to_f.get(t["id"])
                    if not f: continue
                    if (mood_config["tempo"][0] <= f.get("tempo", 120) <= mood_config["tempo"][1]
                            and abs(f.get("energy",  0.5) - mood_config["energy"])  <= 0.3
                            and abs(f.get("valence", 0.5) - mood_config["valence"]) <= 0.3):
                        filtered.append(t)
        except Exception:
            filtered = collected
        return filtered[:limit]

    def get_recommendations_for_language(
            self,
            mood_config: Dict,
            language: str,
            limit: int = 20
        ) -> List[Dict]:
        if not self.sp:
            return []
        lang_term = LANGUAGE_SEARCH.get(language, language.lower())
        artists = LANGUAGE_ARTISTS.get(language, [])

        description = mood_config.get("description", "")
        genres = mood_config.get("genres", [])

        # Mood-specific search words
        mood_keywords = {
            "happy": "happy upbeat feel good",
            "chill": "chill relaxing calm",
            "workout": "workout gym energetic",
            "focus": "focus concentration instrumental",
            "sad": "sad emotional heartbreak",
            "party": "party dance hits",
            "romance": "romantic love songs",
            "sleep": "sleep calm soft relaxing",
        }

        # Detect current mood from config
        current_mood = "music"

        for mood_name, cfg in MOOD_CONFIGS.items():
            if cfg is mood_config or cfg == mood_config:
                current_mood = mood_name
                break

        mood_term = mood_keywords.get(
            current_mood,
            description
        )

        queries = []

        # Strong queries: language + mood
        queries.append(f"{lang_term} {mood_term} songs")
        queries.append(f"{lang_term} {current_mood} playlist")

        # Artist + mood queries
        for artist in artists:
            queries.append(f'artist:"{artist}" {mood_term}')

        # Genre-aware query
        if genres:
            queries.append(
                f"{lang_term} {current_mood} {genres[0]}"
            )

        seen_ids = set()
        collected = []

        for query in queries:
            try:
                result = self.sp.search(
                    q=query,
                    type="track",
                    limit=50
                )

                items = result.get(
                    "tracks", {}
                ).get(
                    "items", []
                )

                for track in items:
                    track_id = track.get("id")

                    if track_id and track_id not in seen_ids:
                        collected.append(track)
                        seen_ids.add(track_id)

            except Exception:
                continue

        if not collected:
            return []

        # If audio features unavailable,
        # return search-ranked tracks
        if not st.session_state.get(
            "api_status", {}
        ).get(
            "audio_features", True
        ):
            return collected[:limit]

        filtered = []

        try:
            ids = [track["id"] for track in collected]

            for i in range(0, len(ids), 100):

                batch_ids = ids[i:i + 100]

                features_list = (
                    self.sp.audio_features(batch_ids) or []
                )

                feature_map = {
                    f["id"]: f
                    for f in features_list
                    if f
                }

                batch_tracks = collected[i:i + 100]

                for track in batch_tracks:

                    features = feature_map.get(track["id"])

                    if not features:
                        continue

                    tempo = features.get("tempo", 120)
                    energy = features.get("energy", 0.5)
                    valence = features.get("valence", 0.5)

                    tempo_match = (
                        mood_config["tempo"][0]
                        <= tempo
                        <= mood_config["tempo"][1]
                    )

                    energy_match = (
                        abs(
                            energy - mood_config["energy"]
                        ) <= 0.25
                    )

                    valence_match = (
                        abs(
                            valence - mood_config["valence"]
                        ) <= 0.25
                    )

                    if (
                        tempo_match
                        and energy_match
                        and valence_match
                    ):
                        filtered.append(track)

        except Exception:
            filtered = []

        # Use filtered results when enough exist.
        # Otherwise preserve Spotify search ranking.
        if len(filtered) >= limit:
            return filtered[:limit]

        final_tracks = filtered.copy()
        final_ids = {
            track["id"]
            for track in final_tracks
        }

        for track in collected:

            if track["id"] not in final_ids:
                final_tracks.append(track)
                final_ids.add(track["id"])

            if len(final_tracks) >= limit:
                break

        return final_tracks[:limit]
# ─────────────────────────────────────────────────────
# DJInterface
# ─────────────────────────────────────────────────────
class DJInterface:
    def __init__(self, spotify_manager: SpotifyManager):
        self.spotify               = spotify_manager
        self.current_track         = None
        self.next_track            = None
        self.tempo                 = 120.0
        self.volume                = 0.8
        self.crossfade_position    = 0.0
        self.active_device_id: Optional[str] = None
        self.target_volume_percent = 80
        self.volume_a_percent      = 0
        self.volume_b_percent      = 80
        self.enable_beat_fill      = False
        self.beat_fill_pulses      = 4

    def calculate_bpm_match(self, f1: Dict, f2: Dict) -> float:
        t1, t2 = f1.get("tempo", 120), f2.get("tempo", 120)
        return min(t1, t2) / max(t1, t2)

    def suggest_mix_point(self, features: Dict) -> float:
        energy = features.get("energy", 0.5)
        if energy < 0.4: return 0.3
        elif energy < 0.6: return 0.2
        return 0.1

    def fade_transition(self, from_uri: Optional[str], to_uri: str, device_id: Optional[str]) -> bool:
        spm = self.spotify
        if not spm or not spm.sp or not to_uri: return False
        device = device_id or self.active_device_id
        target = self.target_volume_percent

        def _run():
            try:
                for vol in range(int(self.volume * 100), 0, -5):
                    spm.sp.volume(vol, device_id=device); time.sleep(0.06)
            except Exception: pass
            spm.start_playback_for_track(to_uri, device)
            time.sleep(0.2)
            try:
                for vol in range(0, target + 1, 5):
                    spm.sp.volume(vol, device_id=device); time.sleep(0.06)
            except Exception: pass

        threading.Thread(target=_run, daemon=True).start()
        return True

    def get_audio_analysis(self, track_id: str) -> Optional[Dict]:
        if not st.session_state.get("api_status", {}).get("audio_features", True): return None
        try:
            return self.spotify.sp.audio_analysis(track_id)
        except Exception:
            return None

    def get_current_playback_position_ms(self) -> Optional[int]:
        try:
            pb = self.spotify.sp.current_playback()
            return pb.get("progress_ms") if pb else None
        except Exception:
            return None

    def find_next_beat_after(self, analysis: Dict, after_ms: int) -> Optional[int]:
        if not analysis or "beats" not in analysis: return None
        for beat in analysis["beats"]:
            ts_ms = int(beat.get("start", 0.0) * 1000)
            if ts_ms > after_ms: return ts_ms
        return None

    def beat_matched_transition(self, current_track_id, next_track_uri, next_track_id,
                                device_id, cue_point_ms, crossfade_ms=2000) -> bool:
        spm = self.spotify
        if not spm or not spm.sp or not next_track_uri: return False
        device       = device_id or self.active_device_id
        vol_a        = self.volume_a_percent
        vol_b        = max(0, min(100, int(self.volume_b_percent)))
        fill_enabled = self.enable_beat_fill
        fill_pulses  = self.beat_fill_pulses
        target_vol   = self.target_volume_percent

        def _run():
            now_ms   = self.get_current_playback_position_ms() or 0
            analysis = self.get_audio_analysis(current_track_id) if current_track_id else None
            beat_ms  = self.find_next_beat_after(analysis, now_ms) if analysis else None
            if beat_ms:
                delay = max(0, (beat_ms - now_ms) / 1000.0 - (crossfade_ms / 2000.0))
                if delay > 0: time.sleep(delay)
            if fill_enabled and fill_pulses > 0:
                try:
                    base_vol = (spm.sp.current_playback() or {}).get("device", {}).get("volume_percent", target_vol)
                except Exception:
                    base_vol = target_vol
                for _ in range(fill_pulses):
                    try:
                        spm.sp.volume(max(0, int(base_vol * 0.6)), device_id=device); time.sleep(0.08)
                        spm.sp.volume(min(100, int(base_vol)), device_id=device); time.sleep(0.08)
                    except Exception: break
            try:
                start_vol = target_vol
                step = max(1, int((start_vol - int(vol_a)) / 20))
                for v in range(start_vol, int(vol_a) - 1, -step):
                    spm.sp.volume(max(0, v), device_id=device)
                    time.sleep(crossfade_ms / 1000.0 / 20.0)
            except Exception: pass
            spm.sp.start_playback(device_id=device, uris=[next_track_uri], position_ms=cue_point_ms or 0)
            try:
                step_in = max(1, int(vol_b / 20))
                for v in range(int(vol_a), vol_b + 1, step_in):
                    spm.sp.volume(min(100, v), device_id=device)
                    time.sleep(crossfade_ms / 1000.0 / 20.0)
            except Exception: pass

        threading.Thread(target=_run, daemon=True).start()
        return True


# ─────────────────────────────────────────────────────
# MoodPlaylistGenerator
# ─────────────────────────────────────────────────────
class MoodPlaylistGenerator:
    def __init__(self, spotify_manager: SpotifyManager):
        self.spotify         = spotify_manager
        self.current_mood    = None
        self.current_language = "Any"
        self.playlist_tracks = []

    def generate_playlist(self, mood: str, user_feedback: Optional[Dict] = None,
                          language: str = "Any") -> List[Dict]:
        if mood not in MOOD_CONFIGS:
            st.error(f"Unknown mood: {mood}")
            return []
        config                = MOOD_CONFIGS[mood]
        self.current_mood     = mood
        self.current_language = language

        if language and language != "Any":
            tracks = self.spotify.get_recommendations_for_language(config, language, limit=20)
        else:
            tracks = self.spotify.get_recommendations(config, limit=20)

        if user_feedback:
            tracks = self._adapt_playlist(tracks, user_feedback)
        self.playlist_tracks = tracks
        return tracks

    def _adapt_playlist(self, tracks: List[Dict], feedback: Dict) -> List[Dict]:
        liked_genres    = set(feedback.get("liked_genres",    []))
        disliked_genres = set(feedback.get("disliked_genres", []))
        if not liked_genres and not disliked_genres: return tracks
        artist_ids = list({
            artist["id"] for track in tracks
            for artist in track.get("artists", []) if "id" in artist
        })
        id_to_genres: Dict[str, List[str]] = {}
        try:
            for i in range(0, len(artist_ids), 50):
                result = self.spotify.sp.artists(artist_ids[i : i + 50])
                for artist in result.get("artists", []) or []:
                    if artist: id_to_genres[artist["id"]] = artist.get("genres", [])
        except Exception:
            return tracks
        adapted: List[Dict] = []
        for track in tracks:
            track_genres = set(
                genre for artist in track.get("artists", [])
                for genre in id_to_genres.get(artist.get("id", ""), [])
            )
            if track_genres & disliked_genres: continue
            if track_genres & liked_genres: adapted.insert(0, track)
            else: adapted.append(track)
        return adapted


# ─────────────────────────────────────────────────────
# UI Helpers
# ─────────────────────────────────────────────────────

# Mood metadata: emoji, label, css-class
# NOTE: keys here must exactly match the (lowercase) keys in config.py's MOOD_CONFIGS,
# otherwise this dict silently filters every mood out — see render_mood_mode().
MOOD_META = {
    "happy":   ("☀️", "Happy",   "happy"),
    "chill":   ("🌊", "Chill",   "chill"),
    "workout": ("🔥", "Workout", "workout"),
    "focus":   ("🎯", "Focus",   "focus"),
    "sad":     ("🌧️", "Sad",     "sad"),
    "party":   ("🎉", "Party",   "party"),
    "romance": ("🌹", "Romance", "romance"),
    "sleep":   ("🌙", "Sleep",   "sleep"),
}


def render_hero():
    st.markdown("""
    <div class="groove-header">
        <div class="groove-title">🎧 GrooveAI</div>
        <div class="groove-subtitle">Smart DJ &nbsp;·&nbsp; Mood Music &nbsp;·&nbsp; Adaptive Mixing</div>
        <div class="waveform">
            <span></span><span></span><span></span><span></span><span></span>
            <span></span><span></span><span></span><span></span><span></span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_now_playing(spotify_manager: SpotifyManager):
    try:
        pb = spotify_manager.sp.current_playback()
        if pb and pb.get("is_playing"):
            item    = pb.get("item") or {}
            name    = item.get("name", "Unknown")
            artists = ", ".join(a["name"] for a in item.get("artists", []))
            imgs    = (item.get("album") or {}).get("images") or [{}]
            img_url = imgs[0].get("url", "")

            col_img, col_info = st.columns([1, 7])
            with col_img:
                if img_url:
                    st.image(img_url, width=52)
            with col_info:
                st.markdown(f"""
                <div class="now-playing-bar" style="margin-bottom:0">
                    <div class="now-playing-pulse"></div>
                    <div>
                        <div class="now-playing-text">{name}</div>
                        <div class="now-playing-artist">{artists}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    except Exception:
        pass


def render_track_card(i: int, track: Dict, features: Optional[Dict], mood: str,
                      show_play: bool = True, dj_interface=None, device_id=None):
    """Renders a styled track tile. Returns True if played."""
    name    = track.get("name", "Unknown")
    artists = ", ".join(a["name"] for a in track.get("artists", []))
    dur_ms  = track.get("duration_ms", 0)
    dur_str = f"{dur_ms // 60000}:{(dur_ms % 60000) // 1000:02d}"

    # Feature badges HTML
    badges = ""
    if features:
        tempo   = features.get("tempo")
        energy  = features.get("energy")
        valence = features.get("valence")
        if tempo   is not None: badges += f'<span class="badge badge-bpm">{tempo:.0f} BPM</span>'
        if energy  is not None: badges += f'<span class="badge badge-energy">NRG {int(energy*100)}%</span>'
        if valence is not None: badges += f'<span class="badge badge-valence">VIBE {int(valence*100)}%</span>'

    st.markdown(f"""
    <div class="track-card">
        <div class="track-art">🎵</div>
        <div class="track-info">
            <div class="track-name">{i+1}. {name}</div>
            <div class="track-artist">{artists} &nbsp;·&nbsp; {dur_str}</div>
            <div class="track-badges">{badges}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if show_play:
        c_play, c_info, _ = st.columns([1, 1, 5])
        played = False
        with c_play:
            if st.button("▶ Play", key=f"play_track_{i}"):
                preview   = track.get("preview_url")
                track_uri = track.get("uri")
                if preview:
                    st.audio(preview)
                    played = True
                elif track_uri and dj_interface:
                    played = dj_interface.fade_transition(None, track_uri, device_id)
                if played:
                    st.toast(f"▶ {name}", icon="🎵")
                else:
                    st.warning("No preview & no active device.")
        with c_info:
            if st.button("Features", key=f"info_track_{i}"):
                if features:
                    st.info(
                        f"🎵 {features.get('tempo', 0):.0f} BPM  |  "
                        f"⚡ Energy {features.get('energy', 0):.2f}  |  "
                        f"😊 Valence {features.get('valence', 0):.2f}"
                    )
                else:
                    st.info("Audio features unavailable for this app registration.")
        return played
    return False


def render_automix_sidebar():
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔀 AUTO-MIX")
    st.sidebar.toggle("Enable Smart Auto-Mix", key="auto_mix_enabled")
    st.sidebar.selectbox(
        "Transition strategy",
        ["smooth", "energy_up", "energy_down"],
        key="mix_strategy",
    )
    if st.session_state.get("auto_mix_enabled"):
        st.sidebar.markdown(
            '<div style="background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.4);'
            'border-radius:8px;padding:8px 12px;color:#6EE7B7;font-size:0.8rem;font-weight:600;">'
            '● AUTO-MIX ACTIVE</div>',
            unsafe_allow_html=True
        )


def render_privacy_consent() -> bool:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔒 PRIVACY")
    if st.session_state.get("privacy_consented"):
        st.sidebar.markdown(
            '<div class="privacy-box" style="color:#6EE7B7;font-size:0.8rem;font-weight:600;">'
            '✓ Consent recorded</div>',
            unsafe_allow_html=True
        )
        return True
    if st.sidebar.checkbox("I agree to the privacy policy", key="privacy_consent_checkbox"):
        st.session_state["privacy_consented"] = True
        st.sidebar.markdown(
            '<div class="privacy-box" style="color:#6EE7B7;font-size:0.8rem;font-weight:600;">'
            '✓ Consent recorded</div>',
            unsafe_allow_html=True
        )
        return True
    st.sidebar.markdown(
        '<div class="privacy-box"><span style="color:#FCD34D;font-size:0.8rem;">'
        '⚠ Accept privacy policy to continue</span></div>',
        unsafe_allow_html=True
    )
    return False


def render_spotify_attribution():
    st.markdown("---")
    st.markdown(
        '<div class="spotify-badge">🎵 &nbsp; Powered by Spotify</div>',
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────────────
# Render: DJ Mode
# ─────────────────────────────────────────────────────
def render_dj_mode(dj_interface: DJInterface):
    st.markdown('<div class="section-label">Mixing Console</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🎛️ DJ Mode</div>', unsafe_allow_html=True)

    render_now_playing(dj_interface.spotify)

    # Device selector
    devices      = dj_interface.spotify.get_available_devices()
    device_names = [f"{d.get('name','Unknown')} ({d.get('type','')})" for d in devices]
    device_ids   = [d.get("id") for d in devices]
    selected_device = None

    if devices:
        idx             = st.selectbox("🔊 Playback device:", range(len(device_names)), format_func=lambda i: device_names[i])
        selected_device = device_ids[idx]
        st.session_state["device_id"]     = selected_device
        dj_interface.active_device_id      = selected_device
    else:
        st.info("Open the Spotify app on your phone or desktop to see devices here.")

    st.markdown('<div class="dj-console">', unsafe_allow_html=True)

    col_a, col_ctrl, col_b = st.columns([5, 4, 5])

    with col_a:
        st.markdown('<div class="dj-deck">', unsafe_allow_html=True)
        st.markdown('<div class="dj-label deck-a">◈ DECK A</div>', unsafe_allow_html=True)
        search_a = st.text_input("Search Track A:", key="search_a", placeholder="Artist or title…")
        if search_a:
            tracks_a = dj_interface.spotify.search_tracks(search_a, limit=8)
            for i, track in enumerate(tracks_a):
                dur = track.get("duration_ms", 0) // 1000
                st.markdown(f'<div style="font-size:0.82rem;color:#E2E8F0;margin-bottom:2px;">'
                            f'{track["name"]} · {", ".join(a["name"] for a in track["artists"])}'
                            f'<span style="color:#94A3B8;font-size:0.72rem;"> {dur//60}:{dur%60:02d}</span></div>',
                            unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("▶ Play A", key=f"playA_{i}"):
                        st.session_state["track_a"] = track
                        dj_interface.current_track   = track
                        if track.get("uri"):
                            dj_interface.spotify.start_playback_for_track(track["uri"], selected_device)
                        st.toast(f"▶ Deck A: {track['name']}", icon="🎵")
                with c2:
                    if st.button("Cue A", key=f"setA_{i}"):
                        st.session_state["track_a"] = track
                        dj_interface.current_track   = track
                        st.toast("Cued to Deck A", icon="🎯")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="dj-deck">', unsafe_allow_html=True)
        st.markdown('<div class="dj-label deck-b">◈ DECK B</div>', unsafe_allow_html=True)
        search_b = st.text_input("Search Track B:", key="search_b", placeholder="Artist or title…")
        if search_b:
            tracks_b = dj_interface.spotify.search_tracks(search_b, limit=8)
            for i, track in enumerate(tracks_b):
                dur = track.get("duration_ms", 0) // 1000
                st.markdown(f'<div style="font-size:0.82rem;color:#E2E8F0;margin-bottom:2px;">'
                            f'{track["name"]} · {", ".join(a["name"] for a in track["artists"])}'
                            f'<span style="color:#94A3B8;font-size:0.72rem;"> {dur//60}:{dur%60:02d}</span></div>',
                            unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("▶ Play B", key=f"playB_{i}"):
                        st.session_state["track_b"] = track
                        dj_interface.next_track       = track
                        if track.get("uri"):
                            dj_interface.spotify.start_playback_for_track(track["uri"], selected_device)
                        st.toast(f"▶ Deck B: {track['name']}", icon="🎵")
                with c2:
                    if st.button("Cue B", key=f"setB_{i}"):
                        st.session_state["track_b"] = track
                        dj_interface.next_track       = track
                        st.toast("Cued to Deck B", icon="🎯")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_ctrl:
        st.markdown('<div class="dj-deck">', unsafe_allow_html=True)
        st.markdown('<div class="dj-label" style="color:#8B5CF6">⚙ CONTROLS</div>', unsafe_allow_html=True)

        dj_interface.tempo  = st.slider("Tempo (BPM)", 60, 200, 120, key="tempo_slider")
        volume              = st.slider("Master Volume", 0.0, 1.0, 0.8, key="volume_slider")
        dj_interface.volume = volume
        dj_interface.target_volume_percent = int(volume * 100)

        c1, c2 = st.columns(2)
        with c1: dj_interface.volume_a_percent = st.slider("A out%", 0, 100, 0, key="vol_a_slider")
        with c2: dj_interface.volume_b_percent = st.slider("B in%",  0, 100, int(volume*100), key="vol_b_slider")

        crossfade_sec = st.slider("Crossfade (sec)", 2, 8, 3, key="crossfade_slider")
        crossfade_ms  = crossfade_sec * 1000

        cue_sec = st.number_input("B cue point (sec)", min_value=0, max_value=600, value=0, step=1)

        dj_interface.enable_beat_fill = st.checkbox("Beat fill before transition", key="beat_fill_checkbox")
        if dj_interface.enable_beat_fill:
            dj_interface.beat_fill_pulses = st.slider("Pulses", 1, 8, 4, key="beat_fill_pulses")

        if st.button("🎯 Beat-Match A → B", key="beat_match_btn", type="primary"):
            track_a = st.session_state.get("track_a") or dj_interface.current_track
            track_b = st.session_state.get("track_b") or dj_interface.next_track
            if track_a and track_b:
                ok = dj_interface.beat_matched_transition(
                    track_a.get("id"), track_b.get("uri", ""), track_b.get("id", ""),
                    st.session_state.get("device_id"), int(cue_sec * 1000), crossfade_ms,
                )
                if ok: st.success("Beat-matched transition running in background.")
                else:  st.warning("Set both tracks and ensure a device is active.")
            else:
                st.warning("Cue both Track A and Track B first.")

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close dj-console

    # BPM compat
    track_a    = st.session_state.get("track_a") or dj_interface.current_track
    track_b    = st.session_state.get("track_b") or dj_interface.next_track
    track_a_id = (track_a or {}).get("id")
    track_b_id = (track_b or {}).get("id")
    if track_a_id and track_b_id:
        f1 = dj_interface.spotify.get_track_features(track_a_id)
        f2 = dj_interface.spotify.get_track_features(track_b_id)
        if f1 and f2:
            bpm_match = dj_interface.calculate_bpm_match(f1, f2)
            mix_pt    = dj_interface.suggest_mix_point(f2)
            color     = "#10B981" if bpm_match > 0.85 else "#F59E0B" if bpm_match > 0.7 else "#EC4899"
            st.markdown(f"""
            <div style="background:rgba(26,26,46,0.8);border:1px solid rgba(139,92,246,0.2);
                        border-radius:10px;padding:14px 18px;margin-top:1rem;">
                <div style="font-size:0.7rem;color:#94A3B8;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">
                    Mix Analysis
                </div>
                <div style="display:flex;gap:24px;align-items:center;">
                    <div>
                        <div style="font-size:1.4rem;font-weight:700;color:{color};">{bpm_match:.0%}</div>
                        <div style="font-size:0.7rem;color:#94A3B8;">BPM Compat</div>
                    </div>
                    <div>
                        <div style="font-size:1.4rem;font-weight:700;color:#8B5CF6;">{mix_pt:.0%}</div>
                        <div style="font-size:0.7rem;color:#94A3B8;">Suggested Mix-in</div>
                    </div>
                    <div style="flex:1">
                        <div class="compat-bar" style="width:{int(bpm_match*100)}%;background:{color};height:6px;border-radius:3px;"></div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif not st.session_state.get("api_status", {}).get("audio_features", True):
            st.info("BPM analysis unavailable — audio_features deprecated for this app.")


# ─────────────────────────────────────────────────────
# Render: Mood Mode
# ─────────────────────────────────────────────────────
def render_mood_mode(mood_generator: MoodPlaylistGenerator, sql_manager: SQLQueryManager, dj_interface: DJInterface):
    st.markdown('<div class="section-label">Playlist Generator</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🎵 Mood Mode</div>', unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 5])

    with col_left:
        st.markdown("**Select your vibe:**")

        available_moods = [m for m in MOOD_META if m in MOOD_CONFIGS]
        mood_options     = [MOOD_META[m][1] for m in available_moods]
        mood_keys        = available_moods

        # Defensive guard: if MOOD_META and config.py's MOOD_CONFIGS keys don't line up
        # (e.g. casing mismatch, missing moods), fail with a clear message instead of
        # crashing on mood_options[0] below.
        if not mood_options:
            st.error(
                "No moods available. `MOOD_CONFIGS` in config.py is empty or its keys "
                "don't match the expected lowercase mood names: "
                + ", ".join(MOOD_META.keys())
            )
            return

        # Render pill grid (visual only — tapping via radio below)
        pills_html = '<div class="mood-grid">'
        selected_mood_label = st.session_state.get("mood_pill_selection", mood_options[0])
        for key in available_moods:
            emoji, label, css = MOOD_META[key]
            active = "selected" if label == selected_mood_label else ""
            pills_html += f'<div class="mood-pill {css} {active}">{emoji}<br>{label}</div>'
        pills_html += "</div>"
        st.markdown(pills_html, unsafe_allow_html=True)

        # Functional selector (styled to blend in)
        selected_label = st.selectbox(
            "Mood", mood_options,
            key="mood_pill_selection",
            label_visibility="collapsed"
        )
        mood = mood_keys[mood_options.index(selected_label)]

        if mood in MOOD_CONFIGS:
            cfg = MOOD_CONFIGS[mood]
            st.markdown(f"""
            <div style="background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.2);
                        border-radius:10px;padding:12px 14px;margin:8px 0;">
                <div style="font-weight:600;color:#C4B5FD;font-size:0.85rem;margin-bottom:6px;">
                    {MOOD_META[mood][0]} {cfg.get('description','')}</div>
                <div style="font-size:0.75rem;color:#94A3B8;line-height:1.8;">
                    Valence <b style="color:#E2E8F0">{cfg['valence']}</b> &nbsp;·&nbsp;
                    Energy <b style="color:#E2E8F0">{cfg['energy']}</b><br>
                    Tempo <b style="color:#E2E8F0">{cfg['tempo'][0]}–{cfg['tempo'][1]} BPM</b><br>
                    {', '.join(cfg['genres'][:4])}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("**Language:**")
        language = st.selectbox(
            "🌍 Language",
            LANGUAGE_OPTIONS,
            key="playlist_language",
            label_visibility="collapsed",
        )
        # Clear stale playlist when mood or language selection changes
        selection_key = f"{mood}_{language}"

        if st.session_state.get("last_playlist_selection") != selection_key:
            st.session_state["generated_tracks"] = []
            st.session_state["current_mood"] = ""
            st.session_state["current_language"] = language
            st.session_state["last_playlist_selection"] = f"{mood}_{language}"
        st.markdown("**Tune your taste:**")
        liked_genres    = st.multiselect("Boost genres ↑",   ["pop","rock","electronic","jazz","hip-hop","classical"], key="liked_g")
        disliked_genres = st.multiselect("Filter genres ↓",  ["pop","rock","electronic","jazz","hip-hop","classical"], key="disliked_g")

        if st.button("✨ Generate Playlist", type="primary", use_container_width=True):
            feedback = {"liked_genres": liked_genres, "disliked_genres": disliked_genres}
            with st.spinner(f"Curating your {selected_label} playlist…"):
                tracks = mood_generator.generate_playlist(mood, feedback, language)
            st.session_state["generated_tracks"] = tracks
            st.session_state["current_mood"]     = mood
            st.session_state["current_language"] = language
            st.session_state["last_playlist_selection"] = f"{mood}_{language}"

    with col_right:
        tracks       = st.session_state.get("generated_tracks")
        current_mood = st.session_state.get("current_mood", "")
        current_lang = st.session_state.get("current_language", "Any")
        device_id    = st.session_state.get("device_id")

        if tracks:
            emoji = MOOD_META.get(current_mood, ("🎵","",""))[0]
            lang_suffix = f" &nbsp;·&nbsp; {current_lang}" if current_lang != "Any" else ""
            st.markdown(f"""
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem;">
                <div style="font-weight:700;font-size:1rem;color:white;">
                    {emoji} {current_mood.title()} Playlist{lang_suffix} &nbsp;
                    <span style="color:#94A3B8;font-weight:400;font-size:0.85rem;">{len(tracks)} tracks</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            saved_count = 0
            for track in tracks:
                features = mood_generator.spotify.get_track_features(track["id"])
                if sql_manager.save_track_to_db(track, current_mood, features, current_lang):
                    saved_count += 1

            if saved_count:
                st.toast(f"💾 {saved_count} tracks saved to database", icon="✅")

            for i, track in enumerate(tracks):
                features = mood_generator.spotify.get_track_features(track["id"])
                render_track_card(i, track, features, current_mood,
                                  show_play=True, dj_interface=dj_interface, device_id=device_id)
        else:
            st.markdown("""
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                        height:300px;text-align:center;color:#475569;">
                <div style="font-size:3rem;margin-bottom:1rem;">🎵</div>
                <div style="font-size:1rem;font-weight:600;color:#64748B;">No playlist yet</div>
                <div style="font-size:0.85rem;margin-top:6px;">Pick a mood and hit Generate</div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# Render: SQL Mode
# ─────────────────────────────────────────────────────
def render_sql_mode(sql_manager: SQLQueryManager):
    st.markdown('<div class="section-label">Database Explorer</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Analytics & SQL</div>', unsafe_allow_html=True)

    stats = sql_manager.get_stats()
    if stats:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{stats.get("total_tracks", 0)}</div>
                <div class="stat-label">Tracks Saved</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{stats.get("total_queries", 0)}</div>
                <div class="stat-label">Queries Run</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{stats.get("popular_mood", "—")}</div>
                <div class="stat-label">Top Mood</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.75rem;font-weight:600;color:#8B5CF6;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">Quick Queries</div>', unsafe_allow_html=True)
    qc1, qc2, qc3, qc4 = st.columns(4)
    with qc1:
        if st.button("Recent Tracks"):
            st.session_state["sql_current_query"] = "SELECT id, name, artist, album, mood, language, created_at FROM tracks ORDER BY created_at DESC LIMIT 50"
            st.session_state["sql_execute"] = True
    with qc2:
        if st.button("By Popularity"):
            st.session_state["sql_current_query"] = "SELECT name, artist, popularity FROM tracks ORDER BY popularity DESC LIMIT 50"
            st.session_state["sql_execute"] = True
    with qc3:
        if st.button("By Mood"):
            st.session_state["sql_current_query"] = "SELECT mood, COUNT(*) as count FROM tracks GROUP BY mood ORDER BY count DESC"
            st.session_state["sql_execute"] = True
    with qc4:
        if st.button("By Language"):
            st.session_state["sql_current_query"] = "SELECT language, COUNT(*) as count FROM tracks GROUP BY language ORDER BY count DESC"
            st.session_state["sql_execute"] = True

    st.markdown('<div class="sql-box">', unsafe_allow_html=True)
    custom_query = st.text_area(
        "SQL Query",
        value=st.session_state.get("sql_current_query", "SELECT * FROM tracks LIMIT 10"),
        height=130,
        key="sql_query_input",
        placeholder="SELECT * FROM tracks WHERE mood = 'chill' LIMIT 20",
    )
    rc1, rc2 = st.columns([2, 1])
    with rc1:
        if st.button("▶ Execute", type="primary"):
            st.session_state["sql_current_query"] = custom_query
            st.session_state["sql_execute"]       = True
    with rc2:
        if st.button("Clear"):
            st.session_state["sql_current_query"] = ""
            st.session_state["sql_execute"]       = False
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("sql_execute"):
        q = st.session_state.get("sql_current_query", custom_query)
        with st.spinner("Running query…"):
            df, err = sql_manager.execute_query(q)
        if err:
            if err.startswith("✅"): st.success(err)
            else:                    st.error(err)
        elif df is not None and not df.empty:
            st.markdown(f'<div style="color:#6EE7B7;font-size:0.82rem;margin-bottom:6px;">↳ {len(df)} rows returned</div>', unsafe_allow_html=True)
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False)
            st.download_button(
                "⬇ Download CSV", data=csv,
                file_name=f"grooveai_{datetime.now():%Y%m%d_%H%M%S}.csv",
                mime="text/csv",
            )
        elif df is not None:
            st.warning("Query returned no rows.")
        st.session_state["sql_execute"] = False

    st.markdown('<div style="margin-top:1.5rem;font-size:0.75rem;font-weight:600;color:#8B5CF6;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">Query History</div>', unsafe_allow_html=True)
    history_df = sql_manager.get_query_history(limit=10)
    if not history_df.empty:
        st.dataframe(history_df, use_container_width=True)
    else:
        st.markdown('<div style="color:#475569;font-size:0.85rem;">No queries yet.</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="GrooveAI — Smart DJ",
        page_icon="🎧",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject global CSS — first thing after page config
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("""
        <div style="padding:16px 0 8px;text-align:center;">
            <div style="font-size:1.6rem;font-weight:700;background:linear-gradient(135deg,#8B5CF6,#06B6D4);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
                🎧 GrooveAI
            </div>
            <div style="font-size:0.65rem;color:#475569;letter-spacing:0.12em;text-transform:uppercase;margin-top:2px;">
                Smart DJ System
            </div>
        </div>
        """, unsafe_allow_html=True)
        render_automix_sidebar()
        consented = render_privacy_consent()

    # Hero
    render_hero()

    if not consented:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#475569;">
            <div style="font-size:2rem;">🔒</div>
            <div style="margin-top:8px;">Accept the privacy policy in the sidebar to continue.</div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    if not SPOTIPY_CLIENT_ID:
        st.error("❌ Spotify credentials missing — add `.env` with `SPOTIPY_CLIENT_ID`.")
        st.stop()

    init_database()
    sql_manager     = SQLQueryManager()
    spotify_manager = SpotifyManager()

    if not spotify_manager.sp:
        st.error("❌ Spotify authentication failed.")
        st.markdown("Clear `.spotipy_token_cache`, verify your credentials, and reload.")
        if st.button("🗑 Clear Cache & Retry"):
            for f in [".spotipy_token_cache", ".spotipy_cache"]:
                try:
                    if os.path.exists(f): os.remove(f)
                except Exception: pass
            st.cache_resource.clear()
            st.rerun()
        st.stop()

    # API status check (once per session)
    if "api_status" not in st.session_state:
        with st.spinner("Checking Spotify API…"):
            st.session_state["api_status"] = check_deprecated_endpoints(spotify_manager.sp)

    api_status = st.session_state["api_status"]
    if not api_status["audio_features"] or not api_status["recommendations"]:
        missing = []
        if not api_status["recommendations"]:  missing.append("recommendations")
        if not api_status["audio_features"]:   missing.append("audio features")
        st.warning(
            f"⚠️ Some Spotify endpoints are unavailable ({', '.join(missing)}) — "
            f"deprecated for apps created after Nov 2024. Search-based fallbacks active."
        )

    try:
        user = spotify_manager.sp.current_user()
        if user.get("product") != "premium":
            st.warning("⚠️ Spotify Premium needed for playback control. Playlist generation & 30-sec previews still work.")
    except Exception:
        pass

    dj_interface   = DJInterface(spotify_manager)
    mood_generator = MoodPlaylistGenerator(spotify_manager)
    recommender    = TrackSimilarityModel()

    def on_track_ending(current_track_info: dict):
        sp         = spotify_manager.sp
        current_id = current_track_info["track_id"]
        device_id  = st.session_state.get("device_id")
        current_features = spotify_manager.get_track_features(current_id)
        if not current_features: return
        playlist = st.session_state.get("generated_tracks", [])
        if not playlist: return
        candidate_ids = [t["id"] for t in playlist if t.get("id") != current_id]
        candidates_with_features = []
        try:
            for i in range(0, len(candidate_ids), 100):
                batch    = candidate_ids[i:i+100]
                features = sp.audio_features(batch) or []
                id_to_f  = {f["id"]: f for f in features if f}
                for track in playlist:
                    if track.get("id") in id_to_f:
                        candidates_with_features.append({"track": track, "features": id_to_f[track["id"]]})
        except Exception:
            return
        strategy   = st.session_state.get("mix_strategy", "smooth")
        next_track = recommender.find_best_next_track(current_features, candidates_with_features, strategy=strategy)
        if not next_track: return
        dj_interface.beat_matched_transition(
            current_track_id=current_id, next_track_uri=next_track.get("uri",""),
            next_track_id=next_track.get("id",""), device_id=device_id,
            cue_point_ms=0, crossfade_ms=3000,
        )

    if st.session_state.get("auto_mix_enabled"):
        if "playback_monitor" not in st.session_state:
            monitor = PlaybackMonitor(sp=spotify_manager.sp, on_transition=on_track_ending,
                                      threshold_ms=15000, poll_interval=3.0)
            monitor.start()
            st.session_state["playback_monitor"] = monitor
    else:
        existing = st.session_state.get("playback_monitor")
        if existing:
            existing.stop()
            del st.session_state["playback_monitor"]

    # ── Mode navigation ──
    mode = st.radio(
        "mode",
        ["🎧 DJ Mode", "🎵 Mood Mode", "📊 Analytics"],
        horizontal=True,
        key="main_mode",
        label_visibility="collapsed",
    )

    st.markdown("<div style='margin-bottom:1.5rem;'></div>", unsafe_allow_html=True)

    if mode == "🎧 DJ Mode":
        render_dj_mode(dj_interface)
    elif mode == "🎵 Mood Mode":
        render_mood_mode(mood_generator, sql_manager, dj_interface)
    else:
        render_sql_mode(sql_manager)

    render_spotify_attribution()


if __name__ == "__main__":
    main()