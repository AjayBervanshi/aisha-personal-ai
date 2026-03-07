# 💜 Aisha — All Your Questions Answered
### By the AI Dev Team — Honest & Complete Guide

---

## ❓ QUESTION 1
### "Can Aisha use AI apps without API keys — like how I use Claude.ai in the browser?"

**Short answer: No — but here's why, and the workaround.**

When you use Claude.ai, ChatGPT, or Gemini in a browser:
- You log in with your account
- Anthropic / OpenAI / Google pays for the compute on your behalf
- You're using THEIR app, not building your own

When you build Aisha:
- You ARE the app
- You need your own API key to call the AI
- Think of it like: the browser app is a restaurant, the API key is buying groceries to cook at home

**❌ You CANNOT:**
- Log into Claude.ai from Aisha's code with your Gmail
- Use ChatGPT's free tier inside your own app
- Scrape or automate the browser versions (against their terms)

**✅ You CAN (100% free workarounds):**

| AI | Free API Option | How Much Free |
|---|---|---|
| Google Gemini | API key from AI Studio | 15 req/min, 1M tokens/day — VERY generous |
| Groq (Llama 3) | API key from console.groq.com | 14,400 req/day FREE |
| Cohere | API key from cohere.com | 1,000 req/month FREE |
| Mistral | API key from console.mistral.ai | Free tier available |
| Ollama (local) | Run AI on YOUR PC, no internet | Truly unlimited, no key needed |

**Bottom line:** Gemini free tier alone is more than enough for personal use.
You will likely NEVER hit the limit chatting normally.

---

## ❓ QUESTION 2
### "Can Aisha auto-switch to another AI when free credits run out?"

**✅ YES! This is totally possible and we'll build it.**

Here's the smart fallback chain we'll implement:

```
Gemini 1.5 Flash (free, primary)
    ↓ if quota hit or error
Groq + Llama 3 (free, backup)
    ↓ if quota hit or error
Mistral (free tier backup)
    ↓ if quota hit or error
Ollama local (if installed on PC)
    ↓ if all fail
"Aisha is resting, try again in a few minutes 💜"
```

This is called a **"waterfall fallback"** — Aisha tries each AI in order
and only falls back when the current one fails. We'll add this to aisha_brain.py.

---

## ❓ QUESTION 3
### "How to host Aisha and access her from anywhere?"

**The full hosting plan (all free):**

```
┌─────────────────────────────────────────────────────┐
│              WHERE AISHA LIVES                       │
│                                                      │
│  🌐 WEB APP  →  Vercel (free)                        │
│               Your URL: aisha-ajay.vercel.app        │
│               Open from ANY browser, anywhere        │
│                                                      │
│  📱 TELEGRAM  →  Railway.app (free)                  │
│               Bot runs 24/7 in the cloud             │
│               Chat from your phone like WhatsApp     │
│                                                      │
│  🗄️  DATABASE  →  Supabase (free)                    │
│               Memory stored in the cloud             │
│               Accessible from all platforms          │
└─────────────────────────────────────────────────────┘
```

**Access methods:**

| Where you are | How to reach Aisha |
|---|---|
| 📱 Phone (anywhere) | Telegram app → open your bot |
| 📱 Phone (home screen) | Bookmark vercel URL → Add to Home Screen |
| 💻 Laptop (anywhere) | Open aisha-ajay.vercel.app in browser |
| ✈️ No internet | Offline mode shows last conversation |
| 🌍 Any country | Works everywhere — it's just a website + Telegram |

**Step-by-step hosting:**
1. Push code to GitHub (free)
2. Connect GitHub to Vercel → web app live in 2 minutes (free)
3. Connect GitHub to Railway → Telegram bot live 24/7 (free)
4. Supabase is already cloud-hosted automatically

---

## ❓ QUESTION 4
### "How to import my existing chat history from Claude, ChatGPT, Grok, Gemini?"

**Great news — all 4 allow you to export your data!**

### 📥 Export from each platform:

#### Claude (Anthropic)
1. Go to claude.ai
2. Click your profile icon → **Settings**
3. Click **"Export data"**
4. You'll get a `.zip` with all conversations as JSON files

#### ChatGPT (OpenAI)
1. Go to chatgpt.com
2. Click your profile → **Settings**
3. **Data Controls** → **Export data**
4. You'll get an email with a `.zip` — conversations are in `conversations.json`

#### Gemini (Google)
1. Go to takeout.google.com
2. Select **"Gemini Apps Activity"**
3. Click Export → you get a `.zip` with your conversation history

#### Grok (xAI/Twitter)
1. Go to x.com → Settings
2. **Your account** → **Download an archive of your data**
3. Your Grok conversations are included in the archive

### 🧠 Once you have the exports, Aisha can:
- Load all past conversations into her memory
- Extract your preferences, goals, habits from them
- Store everything in Supabase as her long-term memories
- Reference them naturally: "Oh you mentioned this to ChatGPT last year..."

**We will build an import script** (`scripts/import_history.py`) that:
1. Reads all your exported JSON files
2. Extracts the important stuff (goals, habits, preferences, key moments)
3. Summarizes them using AI
4. Stores them in Supabase as Aisha's memories

---

## ❓ QUESTION 5
### "How to get the 5 credentials step by step?"

---

### 🔑 1. SUPABASE_URL + SUPABASE_SERVICE_KEY

**Step 1:** Go to → https://supabase.com
**Step 2:** Click "Start your project" → Sign up FREE with Google
**Step 3:** Click "New Project"
  - Name: `aisha-memory`
  - Password: Choose any strong password
  - Region: Southeast Asia (Singapore) — closest to India
**Step 4:** Wait ~2 minutes for project to create
**Step 5:** Click ⚙️ Settings (left sidebar) → API

You'll see:
```
Project URL:  https://xxxxxxxxxxxx.supabase.co   ← This is SUPABASE_URL
anon key:     eyJhbGc...                          ← This is SUPABASE_ANON_KEY  
service_role: eyJhbGc...                          ← This is SUPABASE_SERVICE_KEY
```

Copy all three and paste in your `.env` file.

---

### 🔑 2. GEMINI_API_KEY

**Step 1:** Go to → https://aistudio.google.com/app/apikey
**Step 2:** Sign in with your Google account
**Step 3:** Click "Create API key"
**Step 4:** Select "Create API key in new project"
**Step 5:** Copy the key (starts with `AIzaSy...`)

Paste as: `GEMINI_API_KEY=AIzaSy...` in your `.env`

Free limits: 15 requests/minute, 1 million tokens/day
(More than enough for personal use!)

---

### 🔑 3. TELEGRAM_BOT_TOKEN

**Step 1:** Open Telegram on your phone
**Step 2:** Search `@BotFather` in the search bar
**Step 3:** Tap Start (or send `/start`)
**Step 4:** Send: `/newbot`
**Step 5:** When asked "What's the name?", type: `Aisha`
**Step 6:** When asked for username, type: `aisha_ajay_bot`
  (If taken, try: `aisha_for_ajay_bot` or `my_aisha_bot`)
**Step 7:** BotFather gives you a token like:
  `7123456789:AAHdqTcvCH1vGWJxfSeofSs0K9tH...`

Copy it → paste as `TELEGRAM_BOT_TOKEN=` in your `.env`

---

### 🔑 4. AJAY_TELEGRAM_ID (Your personal ID)

**Step 1:** Open Telegram
**Step 2:** Search `@userinfobot`
**Step 3:** Tap Start
**Step 4:** It immediately shows your User ID like:
  ```
  Id: 987654321
  First: Ajay
  ```

Copy the number → paste as `AJAY_TELEGRAM_ID=987654321` in your `.env`

This locks Aisha so ONLY you can use her. Nobody else can access your bot.

---

### 🔑 5. GROQ_API_KEY (Free backup AI)

**Step 1:** Go to → https://console.groq.com
**Step 2:** Sign up FREE with Google or email
**Step 3:** Click "API Keys" in left sidebar
**Step 4:** Click "Create API Key" → name it "Aisha"
**Step 5:** Copy the key (starts with `gsk_...`)

Paste as `GROQ_API_KEY=gsk_...` in your `.env`

---

## 📋 YOUR .env FILE — What it should look like when done:

```env
# AI Keys
GEMINI_API_KEY=AIzaSy_your_actual_key_here
GROQ_API_KEY=gsk_your_actual_key_here

# Telegram
TELEGRAM_BOT_TOKEN=7123456789:AAHdqTcvCH1vGWJxfSeofSs0K9tH...
AJAY_TELEGRAM_ID=987654321

# Supabase
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# App
USER_NAME=Ajay
TIMEZONE=Asia/Kolkata
APP_ENV=development
```

---

## 🗺️ WHAT THE TEAM BUILDS NEXT (After You Provide Keys)

1. ✅ **AI Waterfall** — Auto-switch Gemini → Groq → Mistral → Ollama
2. ✅ **Import Script** — Load your Claude/ChatGPT/Gemini/Grok history
3. ✅ **Vercel Deploy** — Web app live with your own URL
4. ✅ **Railway Deploy** — Telegram bot running 24/7
5. ✅ **Supabase Setup** — Run schema + seed via MCP
6. ✅ **Full Test Run** — End-to-end everything working

---

*AI Dev Team — Waiting for your keys, Ajay! 💜*
