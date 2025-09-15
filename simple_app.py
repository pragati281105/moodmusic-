import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Spotify Configuration
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8501/callback")

# Minimal scopes
SCOPE = "user-read-playback-state user-modify-playback-state playlist-read-private"

# Mood configurations
MOODS = {
    "Happy": {"valence": 0.8, "energy": 0.7, "tempo": (120, 140)},
    "Focused": {"valence": 0.5, "energy": 0.4, "tempo": (80, 120)},
    "Relaxed": {"valence": 0.6, "energy": 0.3, "tempo": (60, 100)},
    "Hype": {"valence": 0.9, "energy": 0.9, "tempo": (130, 180)},
    "Sad": {"valence": 0.2, "energy": 0.3, "tempo": (60, 90)}
}

def get_spotify_auth_url():
    """Generate Spotify authorization URL"""
    auth_url = f"https://accounts.spotify.com/authorize?client_id={SPOTIPY_CLIENT_ID}&response_type=code&redirect_uri={SPOTIPY_REDIRECT_URI}&scope={SCOPE}&show_dialog=true"
    return auth_url

def get_spotify_instance():
    """Get authenticated Spotify instance"""
    if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
        return None, "Missing Spotify credentials"
    
    try:
        auth_manager = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=SCOPE,
            cache_path=".spotipy_cache",
            show_dialog=True
        )
        
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        # Test authentication
        user = sp.current_user()
        return sp, None
        
    except Exception as e:
        return None, str(e)

def main():
    st.set_page_config(
        page_title="MoodMusic - Simple Version",
        page_icon="🎧",
        layout="wide"
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
    .error-box {
        background-color: #ffebee;
        border: 1px solid #f44336;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #e8f5e8;
        border: 1px solid #4caf50;
        border-radius: 5px;
        padding: 15px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎧 MoodMusic - Simple Version</h1>
        <p>Smart DJ App - Mix, Create, and Adapt</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check credentials
    if not SPOTIPY_CLIENT_ID or not SPOTIPY_CLIENT_SECRET:
        st.error("❌ Spotify credentials not configured")
        st.markdown("""
        ### 🔧 Setup Required
        
        **Please create a `.env` file with your Spotify credentials:**
        
        ```env
        SPOTIPY_CLIENT_ID=your_client_id_here
        SPOTIPY_CLIENT_SECRET=your_client_secret_here
        SPOTIPY_REDIRECT_URI=http://localhost:8501/callback
        ```
        
        **To get your credentials:**
        1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
        2. Click "Create App" or select existing app
        3. Fill in app details:
           - **App name**: `MoodMusic`
           - **App description**: `Smart DJ app with mood-based playlist generation`
           - **Website**: `http://localhost:8501`
           - **Redirect URI**: `http://localhost:8501/callback`
        4. Click "Save"
        5. Copy your **Client ID** and **Client Secret**
        6. Create a `.env` file in this directory with the credentials above
        
        **After creating the .env file, refresh this page.**
        """)
        return
    
    # Show current configuration
    st.info(f"🔧 Using Client ID: {SPOTIPY_CLIENT_ID[:8]}...")
    st.info(f"🔧 Redirect URI: {SPOTIPY_REDIRECT_URI}")
    
    # Authentication section
    st.markdown("### 🔐 Spotify Authentication")
    
    # Check if we have a cached token
    if os.path.exists(".spotipy_cache"):
        st.success("✅ Found cached authentication token")
        sp, error = get_spotify_instance()
        
        if sp:
            st.success("✅ Successfully authenticated with Spotify!")
            
            # Show user info
            try:
                user = sp.current_user()
                st.write(f"Welcome, **{user['display_name']}**!")
                st.write(f"Email: {user['email']}")
                st.write(f"Followers: {user['followers']['total']}")
                
                # Show playlists
                playlists = sp.current_user_playlists(limit=5)
                if playlists['items']:
                    st.markdown("### 🎵 Your Recent Playlists")
                    for playlist in playlists['items']:
                        st.write(f"• **{playlist['name']}** ({playlist['tracks']['total']} tracks)")
                
                # Mood-based recommendations
                st.markdown("### 🎭 Mood-Based Recommendations")
                mood = st.selectbox("Select your mood:", list(MOODS.keys()))
                
                if st.button("🎵 Get Recommendations"):
                    with st.spinner("Finding perfect tracks..."):
                        try:
                            config = MOODS[mood]
                            recommendations = sp.recommendations(
                                seed_genres=["pop", "rock"],
                                limit=10,
                                target_valence=config['valence'],
                                target_energy=config['energy'],
                                min_tempo=config['tempo'][0],
                                max_tempo=config['tempo'][1]
                            )
                            
                            st.success(f"Found {len(recommendations['tracks'])} tracks for {mood} mood!")
                            
                            for i, track in enumerate(recommendations['tracks'], 1):
                                col1, col2, col3 = st.columns([1, 4, 1])
                                with col1:
                                    st.write(f"**{i}.**")
                                with col2:
                                    st.write(f"**{track['name']}** - {', '.join([a['name'] for a in track['artists']])}")
                                with col3:
                                    if st.button("▶️", key=f"play_{i}"):
                                        st.info(f"Playing: {track['name']}")
                            
                        except Exception as e:
                            st.error(f"Error getting recommendations: {e}")
                
            except Exception as e:
                st.error(f"Error accessing user data: {e}")
        else:
            st.error(f"❌ Authentication failed: {error}")
            st.markdown("### 🔧 Troubleshooting")
            st.markdown("""
            1. **Check your Spotify app settings**:
               - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
               - Click on your app
               - Make sure the redirect URI is: `http://localhost:8501/callback`
            
            2. **Try clearing the cache**:
               - Delete the `.spotipy_cache` file
               - Refresh this page
            
            3. **Verify your credentials**:
               - Make sure your Client ID and Secret are correct
               - Check that there are no extra spaces or characters
            """)
            
            if st.button("🗑️ Clear Cache and Retry"):
                if os.path.exists(".spotipy_cache"):
                    os.remove(".spotipy_cache")
                st.rerun()
    else:
        st.info("🔐 No cached authentication found. Please authenticate with Spotify.")
        
        # Manual authentication URL
        auth_url = get_spotify_auth_url()
        st.markdown(f"""
        ### 🔗 Manual Authentication
        
        Click the link below to authenticate with Spotify:
        
        [**Authenticate with Spotify**]({auth_url})
        
        After authentication, you'll be redirected back to this app.
        """)
        
        if st.button("🔄 Check Authentication Status"):
            st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 10px; background-color: #1DB954; border-radius: 5px; margin: 10px 0;">
        <img src="https://developer.spotify.com/assets/branding-guidelines/icon.png" width="20" height="20" style="vertical-align: middle;">
        <span style="color: white; margin-left: 5px;">Powered by Spotify</span>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
