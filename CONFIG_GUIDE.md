# MoodMusic Configuration Guide

## Quick Setup

### 1. Create Spotify App
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click "Create App"
3. Fill in the details:
   - **App name**: `MoodMusic`
   - **App description**: `Smart DJ app with mood-based playlist generation`
   - **Website**: `http://localhost:8501`
   - **Redirect URI**: `http://localhost:8501/callback`
4. Click "Save"
5. Copy your **Client ID** and **Client Secret**

### 2. Create .env File
Create a file named `.env` in the same directory as your app with this content:

```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://localhost:8501/callback
```

Replace `your_client_id_here` and `your_client_secret_here` with your actual credentials.

### 3. Run the App
```bash
python -m streamlit run app.py
```

## Troubleshooting

### Common Issues

**"Spotify credentials not configured"**
- Make sure you created the `.env` file
- Check that the file is named exactly `.env` (with the dot)
- Verify the file is in the same directory as `app.py`

**"Spotify authentication failed"**
- Check your Client ID and Secret are correct
- Make sure there are no extra spaces or quotes in the `.env` file
- Verify the redirect URI in your Spotify app settings is: `http://localhost:8501/callback`

**"Authorization page shows error"**
- Clear the `.spotipy_cache` file if it exists
- Make sure your Spotify app redirect URI matches exactly: `http://localhost:8501/callback`
- Try refreshing the page after clearing the cache

### File Structure
```
moodmusic/
├── app.py
├── simple_app.py
├── .env                    # Create this file
├── requirements.txt
└── .spotipy_cache         # Created automatically
```

## Need Help?

If you're still having issues:
1. Double-check your Spotify app settings
2. Make sure you have a Spotify Premium account
3. Try the simple version first: `python -m streamlit run simple_app.py`
4. Check that your internet connection is working

