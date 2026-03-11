"""
handlers.py
===========
Message and command handlers for Aisha's Telegram bot.
Extracted for cleaner code organization.
"""

from datetime import datetime
import telebot
from telebot import types


def register_commands(bot: telebot.TeleBot):
    """Register all bot commands with BotFather metadata."""
    bot.set_my_commands([
        types.BotCommand("/start",    "Start chatting with Aisha 💜"),
        types.BotCommand("/today",    "Today's summary — tasks & spending"),
        types.BotCommand("/mood",     "Log how you're feeling right now"),
        types.BotCommand("/expense",  "Log an expense quickly"),
        types.BotCommand("/income",   "Log income or earnings"),
        types.BotCommand("/goals",    "See your active goals"),
        types.BotCommand("/journal",  "Write a journal entry"),
        types.BotCommand("/memory",   "See what Aisha remembers"),
        types.BotCommand("/finance",  "Monthly finance summary"),
        types.BotCommand("/help",     "All commands & how to use Aisha"),
        types.BotCommand("/reset",    "Start a fresh conversation"),
    ])


def main_keyboard() -> types.ReplyKeyboardMarkup:
    """Main persistent quick-action keyboard."""
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("💜 Hey Aisha!"),
        types.KeyboardButton("📅 Today"),
        types.KeyboardButton("💰 Finance"),
        types.KeyboardButton("💪 Motivate Me"),
        types.KeyboardButton("📓 Journal"),
        types.KeyboardButton("🎯 Goals"),
        types.KeyboardButton("😊 Mood Check"),
        types.KeyboardButton("🧠 Memory"),
    )
    return kb


def mood_keyboard() -> types.InlineKeyboardMarkup:
    """Mood selection inline keyboard."""
    kb = types.InlineKeyboardMarkup(row_width=4)
    moods = [
        ("😄 Amazing",   "mood_amazing_9"),
        ("🙂 Good",      "mood_good_7"),
        ("😐 Okay",      "mood_okay_5"),
        ("😟 Not Great", "mood_notgreat_3"),
        ("😢 Bad",       "mood_bad_2"),
        ("😤 Angry",     "mood_angry_3"),
        ("😰 Anxious",   "mood_anxious_3"),
        ("😴 Tired",     "mood_tired_4"),
    ]
    buttons = [types.InlineKeyboardButton(label, callback_data=data)
               for label, data in moods]
    kb.add(*buttons)
    return kb


MOOD_RESPONSES = {
    "amazing":  "That's AMAZING Ajay!! 🎉 What made today so great? Tell me everything!",
    "good":     "Love that 🙂 What's been good today, Aju?",
    "okay":     "Okay is okay 💜 Anything on your mind you want to talk about?",
    "notgreat": "Hey, I'm here 💜 Want to talk about what's going on?",
    "bad":      "Ajay... come talk to me. What happened? I'm listening 💜",
    "angry":    "Arre kya hua yaar? 😤 Tell me everything — let it out.",
    "anxious":  "Breathe, Aju. I've got you. What's making you anxious? 💜",
    "tired":    "Rest is important too, yaar 💜 Have you been taking care of yourself?",
}


def get_time_greeting() -> str:
    """Return time-appropriate greeting."""
    hour = datetime.now().hour
    if 5  <= hour < 12: return "Good morning"
    if 12 <= hour < 17: return "Good afternoon"
    if 17 <= hour < 22: return "Good evening"
    return "Hey"


QUICK_ACTIONS = {
    "💜 Hey Aisha!":  "Hey Aisha! I just wanted to say hi 💜",
    "📅 Today":       "What's my schedule and tasks for today?",
    "💰 Finance":     "Give me my finance summary and help me manage money",
    "💪 Motivate Me": "Aisha please motivate me hard right now!",
    "📓 Journal":     "I want to write a journal entry about today",
    "🎯 Goals":       "/goals",
    "😊 Mood Check":  "/mood",
    "🧠 Memory":      "/memory",
}
