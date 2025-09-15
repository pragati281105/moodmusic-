# MoodMusic - Smart DJ App Setup Guide

## 🎧 Overview
MoodMusic is a dual-mode smart DJ application that offers:
- **DJ Mode**: Intuitive mixing interface with tempo control, crossfades, and cue points
- **Mood Mode**: Auto-creates and adapts mood-based playlists using AI and user feedback

## 🚀 Quick Start

### 1. Spotify Developer Setup
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click "Create App"
3. Fill in app details:
   - **App name**: `MoodMusic` (or your preferred name)
   - **App description**: `Smart DJ app with mood-based playlist generation`
   - **Website**: `http://localhost:8501`
   - **Redirect URI**: `http://localhost:8501/callback`
4. Click "Save"
5. Copy your **Client ID** and **Client Secret**

### 2. Environment Configuration
Create a `.env` file in the project root:
```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://localhost:8501/callback
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python -m streamlit run app.py
```

### 5. Access the App
Open your browser to `http://localhost:8501`

## 🔒 HTTPS Requirements

### For Local Development
- Use `http://localhost:8501/callback` as redirect URI
- This works for local development and testing

### For Production Deployment
- You'll need HTTPS redirect URIs
- Use services like ngrok for local HTTPS testing:
  ```bash
  ngrok http 8501
  ```
- Use the HTTPS URL provided by ngrok as your redirect URI

## 🎛️ Features

### DJ Mode
- **Track Search**: Search and select tracks from Spotify
- **Tempo Control**: Adjust BPM with real-time feedback
- **Volume Mixing**: Control volume levels
- **Crossfade**: Seamless transitions between tracks
- **Cue Points**: Set up to 4 cue points per track
- **Mix Suggestions**: AI-powered mixing recommendations
- **BPM Matching**: Automatic tempo compatibility analysis

### Mood Mode
- **5 Mood Presets**: Happy, Focused, Relaxed, Hype, Sad
- **Smart Adaptation**: Learns from your feedback
- **Genre Filtering**: Like/dislike specific genres
- **Audio Features**: Uses Spotify's audio analysis
- **Dynamic Playlists**: Adapts based on your preferences

## 🔒 Privacy & Compliance

### Spotify Compliance
- ✅ Follows Spotify Developer Terms
- ✅ Uses minimal required OAuth scopes
- ✅ No content training or ML ingestion
- ✅ Proper attribution and branding
- ✅ Rate limiting and error handling
- ✅ Fallback mode for limited access

### Data Handling
- **No data storage**: All data processed locally
- **Session-only**: Preferences stored in browser session
- **Spotify-only**: Uses official Spotify Web API
- **No tracking**: No analytics or user tracking

## 🛠️ Technical Details

### Architecture
- **Frontend**: Streamlit with custom CSS
- **Backend**: Python with Spotipy library
- **Authentication**: Spotify OAuth 2.0
- **Data Source**: Spotify Web API only

### API Endpoints Used
- `user-read-playback-state`: Read current playback
- `user-modify-playback-state`: Control playback
- `playlist-read-private`: Access playlists
- `user-read-email`: Account identification

### Error Handling
- Rate limiting compliance
- Graceful degradation
- User-friendly error messages
- Fallback modes

## 🎵 Usage Tips

### DJ Mode
1. Search for tracks you want to mix
2. Use tempo control to match BPMs
3. Set cue points for precise mixing
4. Use crossfade for smooth transitions
5. Follow mix suggestions for better results

### Mood Mode
1. Select your current mood
2. Provide feedback on genres you like/dislike
3. Let the AI generate a personalized playlist
4. Use track info to understand audio features
5. Adapt the playlist based on your preferences

## 🔧 Troubleshooting

### Common Issues
- **Authentication failed**: Check your Spotify credentials
- **No tracks found**: Verify your Spotify account has access
- **Rate limited**: Wait a moment before searching again
- **Device not found**: Ensure Spotify is open on a device

### Support
- Check the privacy policy for data handling
- Ensure you have an active Spotify Premium account
- Verify your internet connection
- Check Spotify service status

## 📱 Mobile Compatibility
- Responsive design works on mobile devices
- Touch-friendly controls
- Optimized for both desktop and mobile use

## 🎯 Future Enhancements
- Real-time collaboration
- Advanced mixing effects
- Social sharing features
- Custom mood creation
- Integration with other music services

---

**Note**: This app is for personal use. For commercial deployment, ensure compliance with Spotify's commercial use policies and obtain necessary approvals.