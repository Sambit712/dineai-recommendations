# Deployment Plan: Backend on Railway & Frontend on Vercel

This document outlines the step-by-step strategy for decoupling the application and deploying the FastAPI backend to Railway and the vanilla JavaScript frontend to Vercel.

## 1. Backend Deployment (Railway)

Railway is excellent for hosting Python/FastAPI applications and will automatically detect your `requirements.txt`.

### Steps:
1. **Create a Railway Project**: Go to [Railway.app](https://railway.app), create a new project, and select **"Deploy from GitHub repo"**.
2. **Select Repo & Deploy**: Choose your repository. Railway will begin building your Python environment.
3. **Configure Environment Variables**:
   Go to your Railway project's **Variables** tab and add the following:
   * `GROQ_API_KEY`: Your Groq API key (from your `.env` file).
   * `CORS_ORIGINS`: Temporarily set to `*` to ensure successful initial deployment (you'll restrict this to your Vercel URL later).
4. **Configure Start Command** (If not auto-detected correctly):
   Go to **Settings** -> **Deploy** -> **Custom Start Command** and set it to:
   ```bash
   uvicorn src.api.app:app --host 0.0.0.0 --port $PORT
   ```
5. **Get Backend URL**: Once deployed, go to the **Settings** tab and generate/find your public domain (e.g., `https://your-app.up.railway.app`). You will need this for the frontend.

---

## 2. Frontend Configuration & Deployment (Vercel)

Vercel is optimized for static sites and frontend frameworks. Since your frontend is vanilla HTML/CSS/JS located in the `frontend/` directory, Vercel will serve it easily.

### Pre-Deployment Step (Code Update)
Before deploying to Vercel, you need to point your frontend to the new Railway backend.
1. Open `frontend/app.js`.
2. Locate the API base URL (around line 12):
   ```javascript
   const API_BASE = 'http://localhost:8000';
   ```
3. Update it to your new Railway backend URL:
   ```javascript
   const API_BASE = 'https://your-app.up.railway.app'; // Replace with actual Railway URL
   ```
4. Commit and push this change to your GitHub repository.

### Steps:
1. **Create a Vercel Project**: Go to [Vercel.com](https://vercel.com), click **"Add New..."** -> **"Project"**, and import your GitHub repository.
2. **Configure Project Settings**:
   * **Framework Preset**: Leave as "Other"
   * **Root Directory**: Click "Edit" and select the `frontend` directory.
   * **Build Command**: Leave empty (overridden).
   * **Output Directory**: Leave empty (overridden).
3. **Deploy**: Click the **Deploy** button. Vercel will serve the static files located in your `frontend` directory.
4. **Get Frontend URL**: Once deployed, Vercel will provide you with a live URL (e.g., `https://your-frontend.vercel.app`).

---

## 3. Post-Deployment Security (CORS)

Once both the frontend and backend are live, you should secure the backend by restricting CORS to only allow requests from your Vercel frontend.

1. Go back to your **Railway Project** -> **Variables**.
2. Update the `CORS_ORIGINS` variable to your Vercel frontend URL:
   ```
   CORS_ORIGINS=https://your-frontend.vercel.app
   ```
3. Railway will automatically redeploy the backend with the updated secure CORS setting.

Your decoupled application is now fully deployed and communicating securely!
