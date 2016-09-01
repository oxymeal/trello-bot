import logging
from typing import *

import config
from bot import models, trello, messages, trello_wh
from bot.base_bot import BaseBot, Context, Dialog

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)


class AddHookDialog(Dialog):

    def __init__(self, boards):
        self.boards = boards
        self.board_options = [ b.name for b in self.boards ]
        self.board_map = { b.name: b for b in self.boards }

        super().__init__()

    def step1(self, ctx: Context):
        try:
            board = self.board_map[ctx.text]
        except KeyError:
            ctx.send_message(messages.NOTIFY_NOBOARD)
            return False

        try:
            ctx.trello_session.webhooks.add(
                callbackURL=ctx.base_bot.wh_reciever.callback_url(ctx.chat_id),
                idModel=board.id,
            )
        except trello.TrelloError as e:
            text = str(e)
            if 'already exists' not in text:
                ctx.send_message('```' + text + '```')
                return True

        (hook, created) = models.BoardHook.get_or_create(session=ctx.session, board_id=board.id)
        if not created:
            ctx.send_message(messages.NOTIFY_ALREADY)
            return True

        ctx.send_message(messages.NOTIFY_SUCCESS)
        return True

    step1_message = messages.NOTIFY_DLG_MSG

    @property
    def step1_options(self):
        return self.board_options

    def cancel(self, ctx: Context):
        ctx.send_message(messages.NOTIFY_CANCELLED)
        return True

class ForgetHookDialog(Dialog):
    def __init__(self, hook_map):
        self.hook_map = hook_map
        self.hook_options = list(self.hook_map.keys())
        super().__init__()

    def step1(self, ctx: Context):
        try:
            hook = self.hook_map[ctx.text]
        except KeyError:
            ctx.send_message(messages.FORGET_NOBOARD)
            return False

        hook.delete_instance()
        ctx.send_message(messages.FORGET_SUCCESS)
        return True

    step1_message = messages.FORGET_DLG_MSG

    @property
    def step1_options(self):
        return self.hook_options

    def cancel(self, ctx: Context):
        ctx.send_message(messages.FORGET_CANCELLED)
        return True


def require_auth(fn):
    def wrapper(self, ctx, *args, **kwargs):
        if not ctx.session.trello_token:
            ctx.send_message(messages.MUST_AUTH)
            return
        fn(self, ctx, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    wrapper.__qualname__ = fn.__qualname__
    return wrapper


def require_admin(fn):
    def wrapper(self, ctx, *args, **kwargs):
        if ctx.session.admin_id != ctx.message.from_user.id:
            ctx.send_message(messages.FORBIDDEN)
            return
        fn(self, ctx, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    wrapper.__qualname__ = fn.__qualname__
    return wrapper


class TrelloBot(BaseBot):
    def __init__(self, telegram_key: str, trello_key: trello.App):
        super().__init__(telegram_key)

        self.trello_app = trello.App(trello_key)

        self.wh_reciever = trello_wh.WebhookReciever(
            self, config.TRELLO_WH_HOST, config.TRELLO_WH_PORT)

    def run(self):
        self.wh_reciever.start()
        super().run()

    def wrap_context(self, ctx: Context):
        (ctx.session, _) = models.Session.get_or_create(chat_id=ctx.chat_id)

        if ctx.session.trello_token:
            ctx.trello_session = self.trello_app.session(ctx.session.trello_token)

        return ctx

    def cmd_start(self, ctx: Context):
        ctx.send_message(messages.START)

    def _cmd_auth_with_token(self, ctx: Context, token: str):
        try:
            me = self.trello_app.session(token).members.me()
        except trello.AuthError:
            ctx.send_message(messages.AUTH_FAILURE)
            return

        ctx.session.trello_token = token
        ctx.session.admin_id = ctx.message.from_user.id
        ctx.session.save()

        msg = messages.AUTH_SUCCESS.format(fullname=me.fullname)
        ctx.send_message(msg)

    def _cmd_auth_group(self, ctx: Context):
        try:
            private_session = models.Session.get(chat_id=ctx.message.from_user.id)

            if not private_session.trello_token:
                raise PermissionError('no token')

            trello_session = self.trello_app.session(private_session.trello_token)
            me = trello_session.members.me()

            ctx.session.trello_token = private_session.trello_token
            ctx.session.admin_id = ctx.message.from_user.id
            ctx.session.save()

            msg = messages.AUTH_SUCCESS.format(fullname=me.fullname)
            ctx.send_message(msg)

        except (models.Session.DoesNotExist, PermissionError, trello.AuthError):
            ctx.send_message(messages.AUTH_GO_PRIVATE)

    def cmd_auth(self, ctx: Context):
        if ctx.session.trello_token:
            ctx.send_message(messages.AUTH_ALREADY)
            return

        if ctx.message.chat.type != 'private':
            self._cmd_auth_group(ctx)
            return

        try:
            self._cmd_auth_with_token(ctx, ctx.args[0])
            return
        except IndexError:
            pass

        msg = messages.AUTH_URL.format(url=self.trello_app.auth_url())
        ctx.send_message(msg)


    @require_auth
    def cmd_status(self, ctx: Context):
        try:
            me = ctx.trello_session.members.me()
        except trello.AuthError:
            ctx.send_message(messages.STATUS_INVALID_TOKEN)
            return

        admin = ctx.bot.get_chat(ctx.session.admin_id)

        msg = messages.STATUS_OK.format(fullname=me.fullname,
                                        admin=admin.first_name + ' ' + admin.last_name)
        ctx.send_message(msg)

    @require_auth
    @require_admin
    def cmd_unauth(self, ctx: Context):
        models.BoardHook.delete().where(
            models.BoardHook.session == ctx.session).execute()
        ctx.session.delete_instance()
        ctx.send_message(messages.UNAUTH_SUCCESS)

    @require_auth
    @require_admin
    def cmd_notify(self, ctx: Context):
        boards = ctx.trello_session.members.me().boards(filter='open')
        ctx.start_dialog(AddHookDialog(boards))

    @require_auth
    def cmd_list(self, ctx: Context):
        hooks = ctx.session.hooks.execute()

        hooks_msgs = []
        for h in hooks:
            try:
                b = ctx.trello_session.boards.get(h.board_id)
                bname = b.name
            except trello.NotFoundError:
                h.delete()

            msg = messages.LIST_ITEM.format(board=bname)
            hooks_msgs.append(msg)

        msg = messages.LIST.format(list='\n'.join(hooks_msgs))
        ctx.send_message(msg)

    @require_auth
    @require_admin
    def cmd_forget(self, ctx: Context):
        hooks = ctx.session.hooks.execute()
        hook_map = {}
        for h in hooks:
            b = ctx.trello_session.boards.get(h.board_id)
            hook_map[b.name] = h

        ctx.start_dialog(ForgetHookDialog(hook_map))

    def cmd_dev(self, ctx: Context):
        msg = messages.DEV.format(
            session_id=ctx.session.chat_id,
            sender_id=ctx.message.from_user.id,
            admin_id=ctx.session.admin_id,
        )
        ctx.send_message(msg)

    def cmd_help(self, ctx: Context):
        ctx.send_message(messages.HELP)
