MOOD_CONFIGS = {
    "happy": {
        "description": "Upbeat, energetic and positive tracks",
        "valence": 0.8,
        "energy": 0.8,
        "tempo": (110, 140),
        "genres": ["pop", "dance", "electronic"]
    },
    "sad": {
        "description": "Emotional and mellow tracks",
        "valence": 0.2,
        "energy": 0.3,
        "tempo": (60, 100),
        "genres": ["acoustic", "piano", "indie"]
    },
    "chill": {
        "description": "Relaxed and laid-back vibes",
        "valence": 0.5,
        "energy": 0.4,
        "tempo": (70, 110),
        "genres": ["lofi", "ambient", "chill"]
    },
    "workout": {
        "description": "High-energy workout music",
        "valence": 0.7,
        "energy": 0.95,
        "tempo": (120, 160),
        "genres": ["electronic", "hip-hop", "dance"]
    },
    "focus": {
        "description": "Music for concentration and productivity",
        "valence": 0.5,
        "energy": 0.5,
        "tempo": (80, 120),
        "genres": ["classical", "ambient", "instrumental"]
    },
    "party": {
        "description": "High-energy tracks to get the room moving",
        "valence": 0.85,
        "energy": 0.9,
        "tempo": (115, 150),
        "genres": ["dance", "pop", "hip-hop"]
    },
    "romance": {
        "description": "Warm, intimate tracks for slow moments",
        "valence": 0.6,
        "energy": 0.35,
        "tempo": (65, 100),
        "genres": ["r-n-b", "soul", "acoustic"]
    },
    "sleep": {
        "description": "Soft, slow tracks to wind down",
        "valence": 0.4,
        "energy": 0.15,
        "tempo": (50, 80),
        "genres": ["ambient", "piano", "sleep"]
    }
}

DJ_CONFIG = {
    "default_crossfade_ms": 3000,
    "default_cue_point_ms": 0,
    "max_playlist_size": 20
}