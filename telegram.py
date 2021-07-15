import requests

from __init__ import config, logging

try:
    TOKEN = config['telegram']['API_TOKEN']
except AttributeError:
    logging.warning("No Telegram bot token provided!")
    TOKEN = ""


BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


def send_message(
    text: str,
    chat_id=config["telegram"]["allowed_users"][0],
    parse_mode="MarkdownV2"
):
    """Sends message to user through telegram"""
    if not TOKEN:
        return
    # TODO: Use a proper library for more sophisticated stuff
    logging.trace(f"Sending message {text}")
    return requests.post(
        BASE_URL + "/sendMessage",
        data={"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    )
