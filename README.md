# Getachew Fikadu Ekub - Telegram Mini App

## Features
- Language selection: Amharic, English, Afaan Oromoo
- Vehicle listing & detail pages
- Ticket selection (≈95% randomly unavailable)
- Payment page with bank accounts
- Owner ID + Lottery Licence page
- Password-protected Admin panel (`bobmarley#123`)
- Green accent color theme

## Setup (Local Test)

1. Install dependencies:
```bash
cd getachew-ekub-bot
pip install -r requirements.txt
```

2. Run the API server:
```bash
python main.py
```

3. In another terminal, run the bot:
```bash
python bot.py
```

4. For local testing with Telegram, you need a public HTTPS URL (see Free Hosting below).

## Free Hosting Guide

### Option 1: Render.com (Recommended - Free)

1. Create account at https://render.com
2. New → Web Service
3. Connect your GitHub repo (upload this project to GitHub first)
4. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. After deploy, copy the URL (e.g. `https://getachew-ekub.onrender.com`)
6. Update `WEBAPP_URL` in `config.py` or set environment variable
7. Also run the bot as a Background Worker on Render (start command: `python bot.py`)

### Option 2: Railway.app
Similar process, very easy free tier.

### After Hosting
1. Go to @BotFather → `/mybots` → select your bot → Bot Settings → Menu Button
2. Set the Menu Button URL to your hosted WebApp URL
3. Or just use the button that appears after /start

## Admin
- Open the app → Admin tab
- Password: `bobmarley#123`
- Edit vehicle prices and bank accounts

## Important
- Keep your bot token secret
- Replace placeholder vehicle images with real ones later
- For production, add proper payment verification flow
