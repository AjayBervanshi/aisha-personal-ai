# 🤝 Contributing to Aisha

Want to add more features to Aisha? This guide explains how the project is structured and how to extend it.

---

## 🗂️ Where Things Live

| File | What it does |
|---|---|
| `src/core/aisha_brain.py` | Main AI logic — edit this to change how Aisha thinks |
| `src/telegram/bot.py` | Telegram bot — add new commands here |
| `src/web/index.html` | Web UI — change design and features here |
| `supabase/schema.sql` | Database — add new tables here |
| `docs/SYSTEM_PROMPT.md` | Aisha's personality — tweak her character here |

---

## 💡 How to Add a New Feature

### Example: Add a "Daily Quote" command

**Step 1 — Add to Telegram bot** (`src/telegram/bot.py`):
```python
@bot.message_handler(commands=["quote"])
def cmd_quote(message):
    if not is_ajay(message): return
    response = aisha.think("Give me an inspiring quote for today, Aisha!", platform="telegram")
    bot.send_message(message.chat.id, response)
```

**Step 2 — Register the command** (in `__main__` section):
```python
telebot.types.BotCommand("/quote", "Get an inspiring quote"),
```

**Step 3 — Add to web quick actions** (`src/web/index.html`):
```html
<button class="quick-btn" onclick="sendQuick('Give me an inspiring quote!')">✨ Quote</button>
```

Done! That's how simple it is.

---

## 🧠 How to Improve Aisha's Personality

Edit the system prompt in `src/core/aisha_brain.py` in the `build_system_prompt()` function, or directly in `docs/SYSTEM_PROMPT.md`.

### Examples of personalizations:
```
# Add Ajay's specific context:
"Ajay is working on a fintech startup. He often needs help with investor pitches."

# Add a new personality quirk:
"Aisha has a habit of ending conversations with a small Hindi phrase when appropriate."

# Add a new mode:
"STUDY MODE: When Ajay is studying, be quiet and focused. Help him stay on track."
```

---

## 🗄️ How to Add a New Database Table

**Step 1 — Add to `supabase/schema.sql`:**
```sql
CREATE TABLE IF NOT EXISTS aisha_new_feature (
  id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  content     TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

**Step 2 — Run in Supabase SQL Editor**

**Step 3 — Add reading/writing in `src/core/aisha_brain.py`:**
```python
def save_new_feature(self, content: str):
    self.supabase.table("aisha_new_feature").insert({
        "content": content
    }).execute()
```

---

## 🐛 Reporting Issues

If something breaks, check the log file first:
```bash
cat aisha.log
```

Common issues and fixes are in `docs/SETUP_GUIDE.md` → Troubleshooting section.

---

## 🚀 Feature Ideas (Future Roadmap)

- [ ] 📸 **Photo analysis** — Send a photo, Aisha describes or analyzes it (Gemini Vision)
- [ ] 📊 **Finance dashboard** — Visual charts for spending (web app)
- [ ] 🌅 **Daily good morning** — Aisha sends a personalized morning message via Telegram
- [ ] 🧘 **Mood trends** — Chart showing Ajay's mood over weeks/months
- [ ] 📞 **Voice calls** — Actually call Aisha (Twilio free tier)
- [ ] 🔔 **Smart reminders** — Context-aware reminders based on schedule
- [ ] 🌐 **Web search** — Aisha can search the internet in real-time
- [ ] 🎵 **Music suggestions** — Suggest songs based on mood
- [ ] 💊 **Health tracking** — Track sleep, water, exercise
- [ ] 📰 **Daily briefing** — Morning news + weather + tasks summary

Want to build any of these? Go for it! 💜
