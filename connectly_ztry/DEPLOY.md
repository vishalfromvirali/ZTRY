# ZTRY — Deploy to Render (Free)

## Step 1 — MongoDB Atlas (Free Database)

1. Go to https://mongodb.com/atlas → Sign up free
2. Create a cluster → Choose **M0 Free Tier** → Any region
3. **Database Access** → Add user → Set username + password
4. **Network Access** → Add IP → `0.0.0.0/0` (allow all — required for Render)
5. **Connect** → Drivers → Copy the connection string
   - Replace `<password>` with your actual password
   - Replace `myFirstDatabase` with `ztry`
   - Example: `mongodb+srv://vishal:mypass@cluster0.abc.mongodb.net/ztry?retryWrites=true&w=majority`

## Step 2 — Free AI Key (Optional but recommended)

### Option A — Groq (fastest, free)
1. Go to https://console.groq.com → Sign up
2. API Keys → Create key → Copy it
3. Users can type `@ztry` in chat for AI responses

### Option B — Google Gemini (free)
1. Go to https://aistudio.google.com/app/apikey
2. Create API Key → Copy it

## Step 3 — Deploy to Render

1. Push this folder to GitHub
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - **Root Directory:** `connectly_mongo`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn --config gunicorn_config.py "app:create_app('production')"`
   - **Python Version:** 3.11
5. Add Environment Variables:
   ```
   SECRET_KEY       = (click "Generate" in Render)
   MONGO_URI        = mongodb+srv://...your Atlas URI...
   GROQ_API_KEY     = gsk_... (optional)
   ```
6. Add a **Disk** (for uploaded images):
   - Name: `uploads`
   - Mount Path: `/opt/render/project/src/static/uploads`
   - Size: 1 GB (free)
7. Click **Deploy**

## Step 4 — After Deploy

Your app will be live at `https://ztry-app.onrender.com`

**Demo login:** username `alex_dev` password `demo123`

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Cannot reach MongoDB` | Check Atlas → Network Access has `0.0.0.0/0` |
| App crashes on start | Check env vars in Render dashboard |
| Images not saving | Make sure Disk is mounted at correct path |
| AI not responding | Add `GROQ_API_KEY` or `GEMINI_API_KEY` in Render env vars |
| Socket not connecting | Render free tier supports WebSocket — should work fine |

## Local Development

```bash
cd connectly_mongo
pip install -r requirements.txt
cp .env.example .env   # edit .env with your values
python app.py
```

Open http://localhost:5000
