import logging
from typing import *

from bot import models, trello, messages
from bot.base_bot import BaseBot, Context

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)


class TrelloBot(BaseBot):
    def __init__(self, telegram_key: str, trello_key: trello.App):
        self.trello = trello.App(trello_key)
        super().__init__(telegram_key)

    def wrap_context(self, ctx: Context):
        (ctx.session, _) = models.Session.get_or_create(chat_id=ctx.chat_id)

        if ctx.session.trello_token:
            ctx.trello = self.trello.session(ctx.session.trello_token)

        return ctx

    def cmd_start(self, ctx: Context):
        ctx.send_message(messages.START)

    def cmd_auth(self, ctx: Context):
        try:
            token = ctx.args[0]
        except IndexError:
            msg = messages.AUTH_URL.format(url=self.trello.auth_url())
            ctx.send_message(msg)
            return

        try:
            me = self.trello.session(token).members.me()
        except trello.AuthError:
            ctx.send_message(messages.AUTH_FAILURE)
            return

        ctx.session.trello_token = token
        ctx.session.save()

        msg = messages.AUTH_SUCCESS.format(fullname=me.fullname)
        ctx.send_message(msg)

    def cmd_status(self, ctx: Context):
        if not ctx.session.trello_token:
            ctx.send_message(messages.STATUS_UNAUTH)
            return

        try:
            me = ctx.trello.members.me()
        except trello.AuthError:
            ctx.send_message(messages.STATUS_INVALID_TOKEN)
            return

        msg = messages.STATUS_OK.format(fullname=me.fullname)
        ctx.send_message(msg)

    def cmd_unauth(self, ctx: Context):
        if not ctx.session.trello_token:
            ctx.send_message(messages.UNAUTH_ALREADY)
            return

        ctx.session.trello_token = None
        ctx.session.save()
        ctx.send_message(messages.UNAUTH_SUCCESS)
