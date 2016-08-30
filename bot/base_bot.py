from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, Updater

from typing import *


class Context:
    def __init__(self, bot: Bot, update: Update, args: List[str]=None):
        self.bot = bot
        self.update = update
        self.args = args or []

    @property
    def chat_id(self):
        return self.update.message.chat_id

    def send_message(self, text: str):
        self.bot.send_message(chat_id=self.update.message.chat_id,
                              text=text,
                              parse_mode="Markdown")


class BaseBot:
    def __init__(self, key: str):
        self._key = key
        self.updater = Updater(token=self._key)
        self.dispatcher = self.updater.dispatcher

    def wrap_context(self, ctx: Context):
        return ctx

    def _wrap_cmd(self, handler):
        def wrapper(bot: Bot, update: Update, args: List[str]=None):
            ctx = Context(bot, update, args)
            ctx = self.wrap_context(ctx)
            handler(ctx)

        return wrapper

    def run(self):
        for key in dir(self):
            if not key.startswith('cmd_'): continue

            cmd_name = key[4:]
            handler = self._wrap_cmd(getattr(self, key))

            self.dispatcher.add_handler(CommandHandler(
                cmd_name, handler, pass_args=True))

        self.updater.start_polling()
