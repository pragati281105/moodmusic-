import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import io, os, random
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
SCOPE = "user-read-private user-read-email playlist-modify-public playlist-modify-private"

# --- Mood presets ---
MOODS = {
    "Happy": {"valence": 0.9, "energy": 0.8, "tempo": "120-150"},
    "Sad": {"valence": 0.2, "energy": 0.3, "tempo": "40-100"},
    "Chill": {"valence": 0.6, "energy": 0.4, "tempo": "60-120"},
    "Focus": {"valence": 0.5, "energy": 0.4, "tempo": "60-120"},
    "Energetic": {"valence": 0.8, "energy": 0.9, "tempo": "130-180"},
}

# --- Market codes ---
LANGUAGE_MARKET_MAPPING = {
    "English (US)": "US", "English (UK)": "GB", "Hindi (India)": "IN",
    "German (Germany)": "DE", "French (France)": "FR", "Spanish (Spain)": "ES",
    "Japanese (Japan)": "JP", "Korean (Korea)": "KR", "Mandarin (Taiwan)": "TW",
    "Portuguese (Brazil)": "BR",
}

# --- Valid Spotify genre seeds ---
GENRE_SETS = [
    ["pop", "rock", "dance"],
    ["hip-hop", "rap", "r-n-b"],
    ["indie", "folk", "alternative"],
    ["electronic", "house", "techno"],
    ["latin", "reggaeton", "salsa"],
    ["k-pop", "j-pop", "anime"],
    ["jazz", "blues", "soul"],
    ["classical", "piano", "ambient"],
]
def get_audio_features(mood: str):
    return MOODS.get(mood, {"valence": 0.5, "energy": 0.5, "tempo": "90-130"})

@st.cache_resource(show_spinner=False)
def get_spotify_instance():
    if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
        st.error("❌ Spotify credentials missing. Add them to `.env` or Streamlit Secrets.")
        return None
    
    auth_manager = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SCOPE,
        cache_path=".spotipy_cache",
        show_dialog=True,
    )
    try:
        sp = spotipy.Spotify(auth_manager=auth_manager)
        sp.current_user()  # test auth
        return sp
    except Exception:
        st.error("⚠️ Authentication failed. Check Redirect URI in Spotify Dashboard.")
        st.info("It must exactly match: `http://127.0.0.1:8888/callback`")
        return None

def fetch_recommendations(sp, market_code, features):
    min_tempo, max_tempo = map(int, features["tempo"].split("-"))
    seeds = random.choice(GENRE_SETS)

    try:
        rec = sp.recommendations(
            seed_genres=seeds,
            limit=20,
            market=market_code,
            target_valence=features["valence"],
            target_energy=features["energy"],
            min_tempo=min_tempo,
            max_tempo=max_tempo,
        )
        if rec and rec.get("tracks"):
            return rec["tracks"]
    except SpotifyException:
        pass

    try:
        rec = sp.recommendations(
            seed_genres=seeds,
            limit=20,
            market=market_code,
            target_valence=features["valence"],
            target_energy=features["energy"],
        )
        if rec and rec.get("tracks"):
            return rec["tracks"]
    except SpotifyException:
        pass

    try:
        rec = sp.recommendations(seed_genres=seeds, limit=20, market=market_code)
        if rec and rec.get("tracks"):
            return rec["tracks"]
    except Exception:
        pass

    try:
        rec = sp.recommendations(seed_genres=["pop"], limit=20)
        if rec and rec.get("tracks"):
            return rec["tracks"]
    except Exception:
        pass

    return []

def create_image(mood, market):
    img = Image.new("RGB", (600, 600), color=(29, 185, 84))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()

    text_mood = f"Mood: {mood}"
    text_market = f"Language: {market}"

    bbox_mood = d.textbbox((0, 0), text_mood, font=font)
    text_width_mood = bbox_mood[2] - bbox_mood[0]
    text_height_mood = bbox_mood[3] - bbox_mood[1]

    bbox_market = d.textbbox((0, 0), text_market, font=font)
    text_width_market = bbox_market[2] - bbox_market[0]
    text_height_market = bbox_market[3] - bbox_market[1]

    y_center = (600 - text_height_mood - text_height_market - 10) / 2
    d.text(((600 - text_width_mood) / 2, y_center), text_mood, font=font, fill=(255, 255, 255))
    d.text(((600 - text_width_market) / 2, y_center + text_height_mood + 10), text_market, font=font, fill=(255, 255, 255))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()
st.set_page_config(page_title="MoodMusic", page_icon="🎧", layout="wide")
st.markdown("""
    <style>
    body {
        background: linear-gradient(135deg, #ffe6f0, #ffffff);
        font-family: 'Segoe UI', sans-serif;
    }
    .main-title {
        text-align: center;
        font-size: 3rem !important;
        font-weight: bold;
        color: #1DB954;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        text-align: center;
        font-size: 1.2rem;
        color: #333333;
        margin-bottom: 2rem;
    }
    .stButton>button {
        background-color: #1DB954;
        color: white;
        border-radius: 10px;
        padding: 0.6em 1.2em;
        border: none;
        font-size: 1rem;
        font-weight: 500;
        transition: 0.3s;
    }
    .stButton>button: hover {
        background-color: #14833b;
        transform: scale(1.03);
    }
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
""", unsafe_allow_html=True)
st.markdown("<h1 class='main-title'>🎧 MoodMusic</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Turn your emotions into the perfect Spotify playlist</p>", unsafe_allow_html=True)
st.write("---")
for key in ["tracks", "mood", "market_display"]:
    if key not in st.session_state:
        st.session_state[key] = None
col1, col2 = st.columns(2)
with col1:
    mood_options = ["Select a mood"] + list(MOODS.keys())
    selected_mood = st.selectbox("✨ Pick a mood preset:", mood_options)
    user_mood_input = st.text_input("✍️ Or type your custom mood (e.g., 'study', 'party'):")

with col2:
    selected_language = st.selectbox(
        "🌍 Choose your language:",
        options=["Select a language"] + list(LANGUAGE_MARKET_MAPPING.keys())
    )
if st.button("🎶 Generate Playlist", use_container_width=True):
    final_mood = selected_mood if selected_mood != "Select a mood" else user_mood_input.strip()
    if not final_mood:
        st.warning("⚠️ Please enter or select a mood.")
    elif not selected_language or selected_language == "Select a language":
        st.warning("⚠️ Please select a language.")
    else:
        market_code = LANGUAGE_MARKET_MAPPING[selected_language]
        with st.spinner("🎶 Finding the perfect songs..."):
            sp = get_spotify_instance()
            if sp:
                audio_features = get_audio_features(final_mood)
                tracks = fetch_recommendations(sp, market_code, audio_features)
                if not tracks:
                    st.warning("No tracks found. Try another mood/language.")
                else:
                    st.session_state["tracks"] = tracks
                    st.session_state["mood"] = final_mood
                    st.session_state["market_display"] = selected_language
            else:
                st.error("❌ Could not authenticate with Spotify. Check your credentials.")
if st.session_state["tracks"]:
    st.write("---")
    st.header(f"🎶 Tracks for **{st.session_state['mood']}**")
    df = pd.DataFrame([{
        "Track": t["name"],
        "Artist(s)": ", ".join(a["name"] for a in t["artists"]),
        "Link": t["external_urls"]["spotify"],
    } for t in st.session_state["tracks"]])
    st.dataframe(df, hide_index=True, use_container_width=True)
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download as CSV",
            csv_data,
            file_name=f"{st.session_state['mood']}_playlist.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col2:
        image_data = create_image(st.session_state["mood"], st.session_state["market_display"])
        st.download_button(
            "⬇️ Download Cover",
            image_data,
            file_name=f"{st.session_state['mood']}_cover.png",
            mime="image/png",
            use_container_width=True
        )
    if st.button("🎵 Create in Spotify", use_container_width=True):
        sp = get_spotify_instance()
        with st.spinner("🪄 Creating playlist in your Spotify account..."):
            if sp:
                try:
                    user_id = sp.current_user()["id"]
                    playlist = sp.user_playlist_create(
                        user=user_id,
                        name=f"MoodMusic - {st.session_state['mood']} ({st.session_state['market_display']})",
                        public=True
                    )
                    uris = [t["uri"] for t in st.session_state["tracks"] if "uri" in t]
                    if uris:
                        sp.user_playlist_add_tracks(user_id, playlist["id"], uris)
                        st.success("✅ Playlist created!")
                        st.markdown(f"[Open in Spotify]({playlist['external_urls']['spotify']})")
                except Exception as e:
                    st.error(f"Error creating playlist: {e}")
            else:
                st.error("❌ Could not authenticate with Spotify. Check your credentials.")
