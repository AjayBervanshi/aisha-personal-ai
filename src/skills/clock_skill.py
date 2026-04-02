import logging
import datetime
import pytz
from telegram import Update
from telegram.ext import ContextTypes

logging.basicConfig(level=logging.INFO)

def get_current_time(time_zone: str) -> str:
    """
    Retrieves the current time in the specified time zone.

    Args:
    time_zone (str): The time zone for which to retrieve the current time.

    Returns:
    str: The current time in the specified time zone.
    """
    try:
        current_time = datetime.datetime.now(pytz.timezone(time_zone))
        return current_time.strftime("%H:%M:%S")
    except pytz.UnknownTimeZoneError:
        logging.error(f"Unknown time zone: {time_zone}")
        return "Unknown time zone"

def display_clock(update: Update, context: ContextTypes) -> None:
    """
    Displays a digital clock in the chat interface.

    Args:
    update (Update): The update object containing information about the chat.
    context (ContextTypes): The context object containing information about the bot.
    """
    try:
        time_zone = "UTC"  # default time zone
        current_time = get_current_time(time_zone)
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Current time: {current_time}")
    except Exception as e:
        logging.error(f"Error displaying clock: {e}")

if __name__ == "__main__":
    print(get_current_time("US/Pacific"))