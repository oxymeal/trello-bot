import logging
import os
from typing import *

from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, Updater

from bot import messages, models, trello
import config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

trello_app = trello.App(config.TRELLO_KEY)

updater = Updater(token=config.TELEGRAM_KEY)
dispatcher = updater.dispatcher


def start(bot: Bot, update: Update):
    bot.send_message(chat_id=update.message.chat_id,
                     text=messages.START,
                     parse_mode="Markdown")


dispatcher.add_handler(CommandHandler('start', start))


def auth(bot: Bot, update: Update, args: List[str]):
    try:
        token = args[0]
    except IndexError:
        token = None

    if not token:
        msg = messages.AUTH_URL.format(url=trello_app.auth_url())
        bot.send_message(chat_id=update.message.chat_id,
                         text=msg,
                         parse_mode="Markdown")
        return

    try:
        me = trello_app.session(token).me()
    except trello.AuthError:
        bot.send_message(chat_id=update.message.chat_id,
                         text=messages.AUTH_FAILURE)
        return

    (session, _) = models.Session.get_or_create(chat_id=update.message.chat_id)
    session.trello_token = token
    session.save()

    msg = messages.AUTH_SUCCESS.format(fullname=me.fullname)
    bot.send_message(chat_id=update.message.chat_id,
                     text=msg,
                     parse_mode="Markdown")


dispatcher.add_handler(CommandHandler('auth', auth, pass_args=True))


def status(bot: Bot, update: Update):
    (session, _) = models.Session.get_or_create(chat_id=update.message.chat_id)

    if not session.trello_token:
        bot.send_message(chat_id=update.message.chat_id,
                         text=messages.STATUS_UNAUTH)
        return

    try:
        me = trello_app.session(session.trello_token).me()
    except trello.AuthError:
        bot.send_message(chat_id=update.message.chat_id,
                         text=messages.STATUS_INVALID_TOKEN)
        return

    msg = messages.STATUS_OK.format(fullname=me.fullname)
    bot.send_message(chat_id=update.message.chat_id,
                     text=msg,
                     parse_mode="Markdown")


dispatcher.add_handler(CommandHandler('status', status))


def unauth(bot: Bot, update: Update):
    (session, _) = models.Session.get_or_create(chat_id=update.message.chat_id)

    if not session.trello_token:
        bot.send_message(chat_id=update.message.chat_id,
                         text=messages.UNAUTH_ALREADY)
        return

    session.trello_token = None
    session.save()

    bot.send_message(chat_id=update.message.chat_id,
                     text=messages.UNAUTH_SUCCESS)


dispatcher.add_handler(CommandHandler('unauth', unauth))
