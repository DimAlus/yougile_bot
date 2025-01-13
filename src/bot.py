import telebot
from config import config

_bot = telebot.TeleBot(config["bot"]["token"])


def send_message(mess: str, chat: str = "messages"):
  chats = config["bot"]["chats"]
  _bot.send_message(
    chats.get(chat, chats["errors"])["id"], 
    mess, 
    message_thread_id=chats.get(chat, chats["errors"])["thread"], 
    parse_mode='html'
  )


