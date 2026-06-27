# Deployment Plan: Railway (Full Stack)

This document outlines the step-by-step strategy for deploying the complete DineAI application (FastAPI backend + Vanilla JS frontend) to Railway in a single deployment.

## Why a Single Deployment?

The backend is already configured to serve the frontend static files from the `frontend/` directory. By deploying everything together on Railway:
- You avoid CORS issues.
- You don't need to hardcode API URLs in the frontend (it uses relative paths).
- You only have to manage one hosting platform.

## Deployment Steps (Railway)

1. **Create a Railway Project**: Go to [Railway.app](https://railway.app), create a new project, and select **"Deploy from GitHub repo"**.
2. **Select Repo & Deploy**: Choose your repository. Railway will begin building your Python environment.
3. **Configure Environment Variables**:
   Go to your Railway project's **Variables** tab and add the following:
   * `GROQ_API_KEY`: Your Groq API key (from your `.env` file).
4. **Configure Start Command** (If not auto-detected correctly):
   Go to **Settings** -> **Deploy** -> **Custom Start Command** and set it to:
   ```bash
   uvicorn src.api.app:app --host 0.0.0.0 --port $PORT
   ```
5. **Get Application URL**: Once deployed, go to the **Settings** tab and find your public domain under **Networking** -> **Public Networking** (e.g., `https://your-app.up.railway.app`).

Once deployed, simply visit your generated Railway URL in your browser. The frontend will load and automatically communicate with the backend on the same server!
