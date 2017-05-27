import logging
from typing import *

import config
from bot import models, trello, messages, trello_wh
from bot.base_bot import BaseBot, Context, Dialog

logger = logging.getLogger(__name__)


def user_display(user):
    return "{}:{}".format(user.id, user.username)


def chat_display(chat):
    return "chat:{}".format(chat.id)


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
            logger.info(
                "{user} attempted to run command {name} in {chat} unauthorized".format(
                    user=user_display(ctx.message.from_user),
                    chat=chat_display(ctx.message.chat),
                    name=fn.__name__))
            ctx.send_message(messages.MUST_AUTH)
            return
        fn(self, ctx, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    wrapper.__qualname__ = fn.__qualname__
    return wrapper


def require_admin(fn):
    def wrapper(self, ctx, *args, **kwargs):
        if ctx.session.admin_id != ctx.message.from_user.id:
            logger.info(
                "{user} attempted to run command {name} in {chat} being non-admin".format(
                    user=user_display(ctx.message.from_user),
                    chat=chat_display(ctx.message.chat),
                    name=fn.__name__))
            ctx.send_message(messages.FORBIDDEN)
            return
        fn(self, ctx, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    wrapper.__qualname__ = fn.__qualname__
    return wrapper


class TrelloBot(BaseBot):
    def __init__(self, telegram_key: str, trello_key: trello.App):
        logger.debug("Create new instance of TrelloBot.")
        logger.debug("...Init BaseBot.")
        super().__init__(telegram_key)

        logger.debug("...Init trello.App.")
        self.trello_app = trello.App(trello_key)

        logger.debug("...Init trello_wh.WebhookReciever.")
        self.wh_reciever = trello_wh.WebhookReciever(
            self, config.TRELLO_WH_HOST, config.TRELLO_WH_PORT)

    def run(self):
        logger.info("Run the TrelloBot.")
        logger.debug("...Start WebhookReciever.")
        self.wh_reciever.start()
        logger.debug("...Run the BaseBot.")
        super().run()

    def send_message(self, chat_id: int, text: str, *args, **kwargs):
        try:
            super().send_message(chat_id, text, *args, **kwargs)
        except Exception as e:
            logger.error(
                "Message sending to chat id {} failed: {}. Message text: {}; other params: {}, {}.".format(
                    chat_id, repr(e), repr(text), repr(args), repr(kwargs)))

    def wrap_context(self, ctx: Context):
        (ctx.session, _) = models.Session.get_or_create(chat_id=ctx.chat_id)

        if ctx.session.trello_token:
            ctx.trello_session = self.trello_app.session(ctx.session.trello_token)

        return ctx

    def _log_command(self, ctx: Context, cmdname: str):
        message = "/{cmdname} command was issued by {user} in {chat}"
        logger.info(message.format(
            cmdname=cmdname,
            user=user_display(ctx.message.from_user),
            chat=chat_display(ctx.message.chat)))

    def _start_dialog_logged(self, ctx: Context, dialog: Dialog):
        logger.info("Start dialog {dialog} with {user} in {chat}.".format(
            dialog=type(dialog).__name__,
            user=user_display(ctx.message.from_user),
            chat=chat_display(ctx.message.chat)))
        ctx.start_dialog(dialog)

    def cmd_start(self, ctx: Context):
        self._log_command(ctx, "start")
        ctx.send_message(messages.START)

    def _cmd_auth_with_token(self, ctx: Context, token: str):
        logger.debug("...Run auth with a token.")

        logger.debug("...Retrieve account's information with token.")
        try:
            me = self.trello_app.session(token).members.me()
        except trello.AuthError as e:
            logger.error("Could not authorize with a token: " + repr(e))
            ctx.send_message(messages.AUTH_FAILURE)
            return

        logger.info("...Authorized as '{}'.".format(me.fullname))
        logger.debug("...Set {user} admin the {chat}".format(
            user=user_display(ctx.message.from_user),
            chat=chat_display(ctx.message.chat)))
        ctx.session.trello_token = token
        ctx.session.admin_id = ctx.message.from_user.id
        ctx.session.save()

        msg = messages.AUTH_SUCCESS.format(fullname=me.fullname)
        ctx.send_message(msg)

    def _cmd_auth_group(self, ctx: Context):
        logger.debug("...Run auth within a group.")
        try:
            logger.debug("...Try to retrieve private session's trello token.")
            private_session = models.Session.get(chat_id=ctx.message.from_user.id)

            if not private_session.trello_token:
                raise PermissionError('no token')

            logger.debug("...Try to retrieve account info using found token.")
            trello_session = self.trello_app.session(private_session.trello_token)
            me = trello_session.members.me()

            logger.info("...Authorized as '{}'.".format(me.fullname))
            logger.debug("...Set {user} admin the {chat}".format(
                user=user_display(ctx.message.from_user),
                chat=chat_display(ctx.message.chat)))
            ctx.session.trello_token = private_session.trello_token
            ctx.session.admin_id = ctx.message.from_user.id
            ctx.session.save()

            msg = messages.AUTH_SUCCESS.format(fullname=me.fullname)
            ctx.send_message(msg)

        except (models.Session.DoesNotExist, PermissionError, trello.AuthError) as e:
            logger.info("...Private session not authorized: " + repr(e))
            ctx.send_message(messages.AUTH_GO_PRIVATE)

    def cmd_auth(self, ctx: Context):
        self._log_command(ctx, "auth")

        if ctx.session.trello_token:
            logger.debug("...Already authorized.")
            ctx.send_message(messages.AUTH_ALREADY)
            return

        if ctx.message.chat.type != 'private':
            self._cmd_auth_group(ctx)
            return

        try:
            self._cmd_auth_with_token(ctx, ctx.args[0])
            return
        except IndexError as e:
            logger.debug("...Auth with token failed: " + repr(e))
            pass

        logger.debug("...Return auth url.")
        msg = messages.AUTH_URL.format(url=self.trello_app.auth_url())
        ctx.send_message(msg)


    @require_auth
    def cmd_status(self, ctx: Context):
        self._log_command(ctx, "status")

        try:
            logger.debug("...Try to retrieve account info.")
            me = ctx.trello_session.members.me()
        except trello.AuthError as e:
            logger.info("...Command failed: " + repr(e))
            ctx.send_message(messages.STATUS_INVALID_TOKEN)
            return

        logger.debug("...Retrieve admin of {chat}.".format(
            chat=chat_display(ctx.message.chat)))
        admin = ctx.bot.get_chat(ctx.session.admin_id)

        msg = messages.STATUS_OK.format(fullname=me.fullname,
                                        admin=admin.first_name + ' ' + admin.last_name)
        ctx.send_message(msg)

    @require_auth
    @require_admin
    def cmd_unauth(self, ctx: Context):
        self._log_command(ctx, "unauth")

        logger.debug("...Delete board hooks.")
        models.BoardHook.delete().where(
            models.BoardHook.session == ctx.session).execute()
        logger.debug("...Delete chat session.")
        ctx.session.delete_instance()
        ctx.send_message(messages.UNAUTH_SUCCESS)

    @require_auth
    @require_admin
    def cmd_notify(self, ctx: Context):
        self._log_command(ctx, "notify")

        boards = ctx.trello_session.members.me().boards(filter='open')
        logger.debug("...Found {} boards.".format(len(boards)))
        self._start_dialog_logged(ctx, AddHookDialog(boards))

    @require_auth
    def cmd_list(self, ctx: Context):
        self._log_command(ctx, "list")

        hooks = ctx.session.hooks.execute()
        logger.debug("...Found {} hooks.".format(len(hooks)))

        hooks_msgs = []
        for h in hooks:
            try:
                b = ctx.trello_session.boards.get(h.board_id)
                bname = b.name
            except trello.NotFoundError:
                logger.warn(
                    "...Could not load board {} for hook {}. Deleting it.".format(
                        h.board_id, h.id))
                h.delete()
                continue

            msg = messages.LIST_ITEM.format(board=bname)
            hooks_msgs.append(msg)

        logger.debug(
            "...Formed {} hook item messages.".format(len(hooks_msgs)))
        msg = messages.LIST.format(list='\n'.join(hooks_msgs))
        ctx.send_message(msg)

    @require_auth
    @require_admin
    def cmd_forget(self, ctx: Context):
        self._log_command(ctx, "forget")

        hooks = ctx.session.hooks.execute()
        logger.debug("...Found {} hooks.".format(len(hooks)))

        hook_map = {}
        for h in hooks:
            try:
                b = ctx.trello_session.boards.get(h.board_id)
            except trello.NotFoundError:
                logger.warn(
                    "...Could not load board {} for hook {}. Deleting it.".format(
                        h.board_id, h.id))
                h.delete()
                continue

            hook_map[b.name] = h

        self._start_dialog_logged(ctx, ForgetHookDialog(hook_map))

    def cmd_dev(self, ctx: Context):
        self._log_command(ctx, "dev")
        msg = messages.DEV.format(
            session_id=ctx.session.chat_id,
            sender_id=ctx.message.from_user.id,
            admin_id=ctx.session.admin_id,
        )
        ctx.send_message(msg)

    def cmd_help(self, ctx: Context):
        self._log_command(ctx, "help")
        ctx.send_message(messages.HELP)
