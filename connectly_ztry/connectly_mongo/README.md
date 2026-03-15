# Connectly — MongoDB Edition 🚀

## Stack
- **Database**: MongoDB (NoSQL) — stores users, posts, messages, stories, matches
- **Media**: Files saved in `static/uploads/` — profiles, banners, posts, stories
- **AI Host**: Spark (Groq Llama 3 / Gemini / OpenAI)
- **Realtime**: Flask-SocketIO

## Quick Start

### Option A — Local MongoDB (Free)
1. Install MongoDB: https://www.mongodb.com/try/download/community
2. Start MongoDB: `mongod` (or it runs as a service)

### Option B — MongoDB Atlas (Free Cloud)
1. Sign up at https://mongodb.com/atlas (free tier = 512MB)
2. Create a cluster → Get connection string
3. Use it as MONGO_URI in your .env

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file (Windows PowerShell)
[System.IO.File]::WriteAllText("$PWD\.env", "SECRET_KEY=connectly-2024`nMONGO_URI=mongodb://localhost:27017/connectly`nGROQ_API_KEY=your_key_here`n", [System.Text.Encoding]::UTF8)

# Run
python app.py
```

Open http://localhost:5000

## Demo Users
Username: alex_dev / priya_math / jake_startup / sofia_art / raj_data
Password: demo123

## What's stored in MongoDB
- `users` — profiles, photos (filename), banners, interests, followers
- `posts` — text, images (filename), videos (filename), likes, comments
- `stories` — 24h stories with auto-delete TTL index
- `messages` — all chat messages
- `matches` — user connections with AI score
- `notifications` — likes, comments, matches, follows

## Media Storage
Images and videos are saved to:
- `static/uploads/profiles/` — profile photos
- `static/uploads/banners/`  — banner/cover photos  
- `static/uploads/posts/`    — post photos & videos
- `static/uploads/stories/`  — story photos & videos (auto-expire in 24h)
