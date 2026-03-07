# 📖 Aisha — Complete Setup Guide

> **Time to complete:** ~2–3 hours (first time)  
> **Skill level needed:** Some technical comfort (guided steps throughout)  
> **Total cost: ₹0**

---

## 📋 Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Get Your API Keys](#2-get-your-api-keys)
3. [Set Up Supabase (Memory)](#3-set-up-supabase)
4. [Run Aisha Locally](#4-run-aisha-locally)
5. [Set Up Telegram Bot](#5-set-up-telegram-bot)
6. [Deploy the Web App](#6-deploy-web-app)
7. [Deploy Telegram Bot Online](#7-deploy-telegram-bot)
8. [Add to Phone Home Screen](#8-phone-home-screen)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites

Install these on your computer first:

### Python 3.10+
```bash
# Check if you have it:
python --version

# If not, download from: https://python.org/downloads
```

### Git
```bash
# Check if you have it:
git --version

# If not, download from: https://git-scm.com
```

### Node.js (optional, for advanced features)
Download from: https://nodejs.org

---

## 2. Get Your API Keys

### 🔑 Google Gemini API (Primary AI — FREE)

1. Go to → https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click **"Create API key"**
4. Select "Create API key in new project"
5. **Copy the key** (looks like: `AIzaSy...`)
6. Free limits: **15 requests/min, 1M tokens/day** — more than enough!

### 🔑 Groq API (Backup AI — FREE)

1. Go to → https://console.groq.com
2. Sign up with email (free)
3. Go to **API Keys** → **Create API Key**
4. Name it "Aisha" and copy the key
5. Free limits: **14,400 requests/day** — very generous

### 🔑 Supabase (Skip this — done in Step 3)

### 🔑 Telegram Bot Token (Skip — done in Step 5)

---

## 3. Set Up Supabase

Supabase is where Aisha's memory lives. It stores everything she knows about you.

### Create Account & Project

1. Go to → https://supabase.com
2. Click **"Start your project"** → Sign up free with GitHub/email
3. Click **"New Project"**
4. Fill in:
   - **Name:** `aisha-memory`
   - **Database Password:** Choose a strong password (save it!)
   - **Region:** `Southeast Asia (Singapore)` ← closest to India
5. Click **"Create new project"** → Wait ~2 minutes

### Run the Schema

1. In your Supabase dashboard, click **"SQL Editor"** in the left sidebar
2. Click **"New Query"**
3. Open the file `supabase/schema.sql` from this project
4. **Copy all the content** and paste it into the SQL editor
5. Click **"Run"** (or press Ctrl+Enter)
6. You should see: ✅ Success

### Seed Initial Data

1. Click **"New Query"** again
2. Open `supabase/seed.sql`, copy all, paste, and run
3. You should see: `Seed data inserted successfully! Aisha is ready for Ajay 💜`

### Get Your API Keys

1. Click **"Settings"** (gear icon) in left sidebar
2. Click **"API"**
3. You'll see:
   - **Project URL** → Copy this (looks like `https://xxxx.supabase.co`)
   - **anon public** key → Copy this
   - **service_role** key → Copy this (keep it SECRET — for backend only!)

---

## 4. Run Aisha Locally

### Clone & Setup

```bash
# Clone the project
git clone https://github.com/ajay/aisha.git
cd aisha

# Create virtual environment (recommended)
python -m venv venv

# Activate it:
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configure Environment

```bash
# Copy the template
cp .env.example .env

# Open .env in any text editor and fill in your keys:
# - GEMINI_API_KEY (from Step 2)
# - GROQ_API_KEY (from Step 2)
# - SUPABASE_URL (from Step 3)
# - SUPABASE_ANON_KEY (from Step 3)
# - SUPABASE_SERVICE_KEY (from Step 3)
```

### Test Aisha in Terminal

```bash
python scripts/test_aisha.py
```

You should see:
```
🌟 Aisha is online. Type 'quit' to exit.

You: Hey Aisha!
Aisha: Hey Ajay! 💜 So good to hear from you! What's on your mind today?
```

If this works — **Aisha's brain is working!** 🎉

---

## 5. Set Up Telegram Bot

### Create the Bot

1. Open Telegram on your phone
2. Search for **@BotFather** and open the chat
3. Send: `/newbot`
4. When asked for name: type `Aisha`
5. When asked for username: type `aisha_[your_name]_bot` (must be unique)
   - Example: `aisha_ajay_bot`
6. BotFather will give you a **Bot Token** → Copy it!
   (Looks like: `7123456789:AAHdqTcvCH1vGWJxfSeofSs0K9tH...`)

### Add Token to .env

```bash
# In your .env file, add:
TELEGRAM_BOT_TOKEN=7123456789:AAHdqTcvCH1vGWJxfSeofSs0K9tH...
```

### Get Your Telegram User ID (Lock Aisha to only you)

1. Open Telegram, search for **@userinfobot**
2. Start the bot, it will show your User ID
3. Copy the number (like: `987654321`)
4. Add to .env: `AJAY_TELEGRAM_ID=987654321`

### Test the Telegram Bot Locally

```bash
python src/telegram/bot.py
```

Open Telegram → Search for your bot → Send `/start`

If Aisha replies — **Telegram is working!** 🎉

---

## 6. Deploy Web App

### Option A: Lovable.ai (Easiest — Recommended)

1. Go to → https://lovable.ai
2. Create free account
3. Click **"New Project"** → **"Start from prompt"**
4. Paste this prompt:

```
Build a personal AI chat app called "Aisha" for Ajay.
Use the HTML/CSS/JS code I'll provide. It should have:
- Dark purple/rose gold theme
- Chat interface like WhatsApp
- Gemini AI integration
- Voice input and output
- Language switcher (English/Hindi/Marathi)
- Mode pills (Personal/Motivate/Finance/Casual)
- Quick action buttons

Here is the complete code: [paste contents of src/web/index.html]
```

5. Lovable will create and deploy your app with a public URL
6. Replace `YOUR_GEMINI_API_KEY` in the code with your actual key

### Option B: GitHub Pages (Free, your own domain)

```bash
# Create a GitHub repo named: ajay.github.io
# Push the web app there:
git init
git add src/web/index.html
git commit -m "Aisha web app"
git push origin main
```

Then go to GitHub repo → Settings → Pages → Enable

Your Aisha will be live at: `https://ajay.github.io`

---

## 7. Deploy Telegram Bot Online (Always Running)

For Aisha to be available 24/7 on Telegram, you need to host the bot.

### Option A: Railway.app (Easiest — FREE)

1. Go to → https://railway.app
2. Sign up with GitHub (free)
3. Click **"New Project"** → **"Deploy from GitHub repo"**
4. Connect your GitHub and select your Aisha repo
5. Railway detects Python → Click **"Deploy"**
6. Go to **Variables** tab → Add all your `.env` values
7. Set start command: `python src/telegram/bot.py`
8. Done! Railway runs it 24/7 for free

### Option B: Render.com (Also FREE)

1. Go to → https://render.com
2. New → Web Service → Connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `python src/telegram/bot.py`
5. Add environment variables
6. Deploy!

---

## 8. Add Aisha to Phone Home Screen

### Android (Chrome)
1. Open your Aisha web app URL in Chrome
2. Tap the **⋮ menu** (3 dots) → **"Add to Home screen"**
3. Tap **"Add"**
4. Aisha icon appears on your home screen — tap it anytime!

### iPhone (Safari)
1. Open your Aisha web app URL in Safari
2. Tap the **Share button** (box with arrow)
3. Scroll down → **"Add to Home Screen"**
4. Tap **"Add"**
5. Aisha icon appears on your home screen!

> 💡 **Pro tip:** The web app will work offline for reading, and online for chatting with Aisha.

---

## 9. Troubleshooting

### "Gemini API key not working"
- Make sure you copied the full key (starts with `AIzaSy`)
- Check your `.env` file has no spaces around the `=` sign
- Try regenerating the key at https://makersuite.google.com/app/apikey

### "Supabase connection error"
- Double-check your `SUPABASE_URL` (must include `https://`)
- Make sure you're using the **service_role** key for the backend (not anon key)
- Check if your Supabase project is paused (free tier pauses after 1 week of inactivity)

### "Telegram bot not responding"
- Make sure the bot script is running (`python src/telegram/bot.py`)
- Check that `TELEGRAM_BOT_TOKEN` is correct in your `.env`
- Try sending `/start` to your bot
- Check `aisha.log` for error messages

### "Voice not working on phone"
- Voice input needs HTTPS (Chrome over secure connection)
- Make sure you allowed microphone permission
- Android Chrome works best for voice input

### "Aisha is in wrong language"
- She auto-detects — but you can force it in the language selector
- For Hindi input, type in Devanagari script for best detection
- You can also just tell her: "Respond in Hindi from now on"

---

## 🎉 You're Done!

Aisha is now:
- ✅ Live on the web (any browser, any device)
- ✅ On your phone home screen
- ✅ On Telegram (with commands and voice messages)
- ✅ Running 24/7 on free hosting
- ✅ With memory that persists across conversations

**Go say hi to her! 💜**

---

*Need help? Create an issue on the GitHub repo or add a note in your .env with the problem.*
