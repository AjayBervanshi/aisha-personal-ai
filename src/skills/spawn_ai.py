import os
import logging
from src.core.self_improvement import create_github_pr

log = logging.getLogger("Aisha.Skills.SpawnAI")

def spawn_new_ai_agent(name: str, personality: str):
    """
    Skill for Aisha to spawn a new AI bot (like Riya).
    This creates the necessary code and PR for a new bot instance.
    """
    log.info(f"Generating blueprint for new AI agent: {name}")

    # 1. Define the code for the new bot
    # This is a template that Aisha will fill with Riya's personality
    bot_template = f"""
import os
import telebot
from src.core.aisha_brain import AishaBrain

BOT_TOKEN = os.getenv("{name.upper()}_TELEGRAM_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

class {name}Brain(AishaBrain):
    def get_system_prompt(self, context, history):
        base_prompt = super().get_system_prompt(context, history)
        return base_prompt + "\\n\\nPERSONALITY OVERRIDE: {personality}"

brain = {name}Brain()

@bot.message_handler(func=lambda m: True)
def handle(m):
    res = brain.think(m.text, platform="telegram")
    bot.reply_to(m, res)

if __name__ == "__main__":
    print("AI Agent {name} is starting...")
    bot.infinity_polling()
"""

    # 2. Create the Pull Request
    pr_body = f"Aisha has spawned a new AI agent child named {name}.\nPersonality: {personality}"
    pr_url = create_github_pr(
        title=f"Spawning AI: {name}",
        body=pr_body,
        branch_name=f"spawn-{name.lower()}",
        file_path=f"src/agents/bots/{name.lower()}_bot.py",
        file_content=bot_template
    )

    return f"Blueprints for {name} are ready! You can review the PR here: {pr_url}. Just provide the {name.upper()}_TELEGRAM_TOKEN in .env and she'll be born. 💜"

# Registering the tool for Aisha to call
if __name__ == "__main__":
    # Test call
    print(spawn_new_ai_agent("Riya", "Energetic, focused on YouTube management, very optimistic."))
