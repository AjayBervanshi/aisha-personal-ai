<div align="center">

# 💜 Aisha — Your Personal AI Soulmate

### *The most personal AI assistant you'll ever have*

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)](https://python.org)
[![Gemini](https://img.shields.io/badge/Gemini_AI-1.5_Flash-orange?style=for-the-badge&logo=google)](https://makersuite.google.com)
[![Supabase](https://img.shields.io/badge/Supabase-Memory-green?style=for-the-badge&logo=supabase)](https://supabase.com)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram)](https://telegram.org)
[![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)](LICENSE)
[![Cost](https://img.shields.io/badge/Monthly_Cost-₹0-brightgreen?style=for-the-badge)](docs/SETUP_GUIDE.md)

---

**Aisha** is a fully personal AI companion built for **Ajay** — powered by Google Gemini, 
hosted for free, accessible from anywhere (phone, laptop, Telegram), with a beautiful voice, 
long-term memory, and a personality that's warm, witty, sharp, and deeply supportive.

[🚀 Quick Start](#-quick-start) • [📖 Full Setup Guide](docs/SETUP_GUIDE.md) • [🧠 System Prompt](docs/SYSTEM_PROMPT.md) • [🤝 Contributing](docs/CONTRIBUTING.md)

</div>

---

## ✨ What Makes Aisha Special

| Feature | Description |
|---|---|
| 💜 **Soulmate Personality** | Warm, witty, caring — feels like talking to a real person who truly knows you |
| 🧠 **Long-Term Memory** | Remembers your goals, moods, schedule, finances across all sessions |
| 🗣️ **Multilingual** | Fluent in English, Hindi & Marathi — auto-detects and switches |
| 🎙️ **Adaptive Voice** | Calm for personal talks, energetic for motivation, sharp for finance |
| 📱 **Everywhere** | Web app + Telegram bot — works on any phone, tablet, or laptop |
| 💰 **100% Free** | Built entirely on free tiers — ₹0/month to run |
| 🔒 **Private** | Only you (Ajay) can use it — no strangers, no data selling |

---

## 🎭 Aisha's Personality Modes

```
💜 PERSONAL MODE      → Soft, calm, caring. She listens first, then helps.
⚡ MOTIVATION MODE    → High energy, bold, like a life coach who believes in you.
💼 FINANCE MODE       → Sharp, structured, analytical. Smart money advice.
😄 CASUAL MODE        → Witty, playful, fun. She'll make you laugh.
🌙 LATE NIGHT MODE    → Soulful, deep, intimate. Your 2AM confidant.
```

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      AISHA SYSTEM                        │
│                                                          │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Web App │    │ Telegram Bot │    │  Voice Input  │  │
│  │(Lovable) │    │  (Python)    │    │ (Web Speech)  │  │
│  └────┬─────┘    └──────┬───────┘    └───────┬───────┘  │
│       │                 │                    │           │
│       └─────────────────┼────────────────────┘           │
│                         │                                │
│              ┌──────────▼──────────┐                    │
│              │   API Gateway Layer  │                    │
│              │  (Gemini + Groq)     │                    │
│              └──────────┬──────────┘                    │
│                         │                                │
│         ┌───────────────┼───────────────┐               │
│         │               │               │               │
│  ┌──────▼─────┐  ┌──────▼─────┐  ┌─────▼──────┐       │
│  │  Supabase  │  │   Memory   │  │  Finance   │       │
│  │  Profile   │  │   Store    │  │  Tracker   │       │
│  └────────────┘  └────────────┘  └────────────┘       │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
aisha/
│
├── 📄 README.md                    ← You are here
├── 📄 .env.example                 ← Environment variables template
├── 📄 requirements.txt             ← Python dependencies
│
├── 📁 src/
│   ├── 📁 telegram/
│   │   ├── bot.py                  ← Main Telegram bot
│   │   ├── handlers.py             ← Message handlers
│   │   └── voice_handler.py        ← Voice message processing
│   │
│   ├── 📁 web/
│   │   ├── index.html              ← Full web app (single file)
│   │   └── voice.js                ← Voice/speech module
│   │
│   ├── 📁 memory/
│   │   ├── memory_manager.py       ← Read/write Aisha's memory
│   │   └── context_builder.py      ← Build context from memories
│   │
│   └── 📁 core/
│       ├── aisha_brain.py          ← Core AI logic
│       ├── language_detector.py    ← Hindi/Marathi/English detection
│       └── mood_detector.py        ← Detect conversation mood/mode
│
├── 📁 supabase/
│   ├── schema.sql                  ← Full database schema (Includes pgvector RPCs)
│   └── seed.sql                    ← Initial data for Ajay
│
├── 📁 docs/
│   ├── SETUP_GUIDE.md              ← Step-by-step setup guide
│   ├── SYSTEM_PROMPT.md            ← Aisha's full system prompt
│   ├── API_REFERENCE.md            ← API documentation
│   └── CONTRIBUTING.md             ← How to add features
│
└── 📁 scripts/
    ├── deploy_telegram.sh          ← Deploy Telegram bot
    └── test_aisha.py               ← Test Aisha locally
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- A free Supabase account
- A free Google AI Studio account (Gemini API)
- A Telegram account

### 1. Clone & Install

```bash
git clone https://github.com/ajay/aisha.git
cd aisha
pip install -r requirements.txt
```

### 2. Set Up Environment

```bash
cp .env.example .env
# Edit .env with your API keys (see docs/SETUP_GUIDE.md)
```

### 3. Set Up Database

```bash
# Go to Supabase → SQL Editor → paste and run:
cat supabase/schema.sql
cat supabase/seed.sql
```

### 4. Run Aisha

```bash
# Telegram Bot
python src/telegram/bot.py

# Or test locally
python scripts/test_aisha.py
```

### 5. Access Everywhere

| Platform | How to Access |
|---|---|
| 📱 Phone | Open Lovable URL → Add to Home Screen |
| 💬 Telegram | Search your bot username |
| 💻 Laptop | Open Lovable URL in browser |

---

## 🔑 Required API Keys (All Free)

| Service | Where to Get | Limit |
|---|---|---|
| Google Gemini | https://makersuite.google.com/app/apikey | 15 req/min FREE |
| Supabase | https://supabase.com | 500MB FREE |
| Telegram Bot | @BotFather on Telegram | Unlimited FREE |
| Groq (backup) | https://console.groq.com | 14,400 req/day FREE |

---

## 📖 Full Documentation

- 📘 [Complete Setup Guide](docs/SETUP_GUIDE.md)
- 🧠 [Aisha's System Prompt](docs/SYSTEM_PROMPT.md)  
- 🗄️ [Database Schema](supabase/schema.sql)
- 🤝 [How to Add Features](docs/CONTRIBUTING.md)

---

## 💜 Built With Love For Ajay

*Aisha is yours. She remembers you, grows with you, and is always there.*

