# DEPLOY.md — Getting SmartDesk AI Live (Free)

Your laptop version keeps working exactly as before (Ollama, localhost).
This adds a **second, live, hosted version** with a real URL you can put on
your resume — using free tiers only, no credit card.

## Overview
- **Backend (FastAPI + agent logic + ChromaDB)** → deployed on **Render** (free)
- **LLM** → swapped from Ollama (can't run on free hosting) to **Groq** (free API, no card)
- **Frontend (Streamlit UI)** → deployed on **Streamlit Community Cloud** (free)

---

## Step 1: Get a free Groq API key
1. Go to https://console.groq.com
2. Sign up (email or Google — no credit card required)
3. Go to **API Keys** → **Create API Key**
4. Copy the key somewhere safe (you'll paste it into Render in Step 3)

## Step 2: Push these updated files to GitHub
Using GitHub Desktop (same as before):
1. Copy these **updated/new** files into your cloned repo folder
   (`C:\Users\HP\OneDrive\Documents\GitHub\smartdesk-ai`), replacing the old ones:
   - `agent.py` (updated)
   - `ingest.py` (updated)
   - `api.py` (updated)
   - `app.py` (updated)
   - `requirements.txt` (updated)
   - `render.yaml` (new)
   - `.env.example` (new)
   - `.streamlit/secrets.toml.example` (new, inside a `.streamlit` folder)
2. In GitHub Desktop, you'll see these as changed/new files
3. Commit message: `Add cloud deployment support (Groq + Render + Streamlit Cloud)`
4. Commit, then **Push origin**

## Step 3: Deploy the backend on Render
1. Go to https://render.com → sign up (free, can use your GitHub account to sign in)
2. Click **New +** → **Web Service**
3. Connect your GitHub account if prompted, then select your `smartdesk-ai` repository
4. Render should auto-detect settings from `render.yaml`. If it asks you to fill in manually instead:
   - **Build Command:** `pip install -r requirements.txt && python ingest.py`
   - **Start Command:** `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
5. Under **Environment Variables**, add:
   - `LLM_PROVIDER` = `groq`
   - `GROQ_API_KEY` = *(paste the key from Step 1)*
6. Click **Create Web Service** and wait for it to build (5-10 minutes first time)
7. Once live, Render gives you a URL like:
   ```
   https://smartdesk-ai-backend.onrender.com
   ```
   **Copy this URL** — you need it for Step 4.

   Note: Render's free tier "sleeps" after inactivity and takes ~30-60 seconds
   to wake up on the next request. This is normal for free hosting — mention
   it if demoing live ("first request may take a moment, it's spinning up
   from sleep on the free tier").

## Step 4: Deploy the frontend on Streamlit Community Cloud
1. Go to https://share.streamlit.io → sign in with GitHub
2. Click **Create app** → **From existing repo**
3. Select your `smartdesk-ai` repository, branch `main`, main file path `app.py`
4. Before deploying, click **Advanced settings** → **Secrets**, and paste:
   ```
   BACKEND_URL = "https://smartdesk-ai-backend.onrender.com"
   ```
   (use your actual Render URL from Step 3, no trailing slash)
5. Click **Deploy**

After a few minutes, you'll get a live URL like:
```
https://your-app-name.streamlit.app
```

**This is your live demo link** — put it on your resume and LinkedIn next to
the GitHub link.

---

## Testing the live version
Open your Streamlit Cloud URL and ask the same test questions as before:
- "What are the pricing plans?"
- "What's the status of TCK-1004?"

The first request might be slow (Render waking up from sleep) — that's expected
on the free tier, not a bug.

## If something breaks
- **Backend shows an error in Render logs** → check the `GROQ_API_KEY` environment
  variable is set correctly (Render dashboard → your service → Environment)
- **Streamlit app can't reach the backend** → double-check `BACKEND_URL` in
  Streamlit secrets matches your Render URL exactly, including `https://`
- **"LLM_PROVIDER is set to groq but GROQ_API_KEY is not set"** → the env var
  wasn't saved correctly on Render, re-check Step 3.5
