from telegram import Bot, Update
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from typing import *


class Context:
    def __init__(self, base_bot, bot: Bot, update: Update, args: List[str]=None):
        self.base_bot = base_bot
        self.bot = bot
        self.update = update
        self.args = args or []

    @property
    def message(self):
        return self.update.message

    @property
    def chat_id(self):
        return self.update.message.chat_id

    @property
    def text(self):
        return self.update.message.text

    def start_dialog(self, dialog):
        self.base_bot._start_dialog_for(self.chat_id, dialog)
        dialog.send_current_step(self)

    def _options_to_reply_markup(self, options: List[List[str]]):
        keyboard = []

        for row in options:
            if isinstance(row, str):
                row = [row]
            keyboard.append([{'text': o} for o in row])

        return {
            'keyboard': keyboard,
            'one_time_keyboard': True,
        }

    def send_message(self, text: str, *, options: List[List[str]]=None):
        if options:
            reply_markup = self._options_to_reply_markup(options)
        else:
            reply_markup = {'hide_keyboard': True}

        self.bot.send_message(chat_id=self.update.message.chat_id,
                              text=text,
                              parse_mode="Markdown",
                              reply_markup=reply_markup)


class Dialog:
    def __init__(self):
        self.steps = []
        for key in dir(self):
            if not key.startswith('step'): continue

            try:
                num = int(key[4:])
            except (ValueError, TypeError):
                continue

            step_func = getattr(self, key)
            self.steps.append((num, step_func))

        self.steps = sorted(self.steps, key=lambda s: s[0])
        self.steps = [s[1] for s in self.steps]

    def cancel(self, ctx: Context):
        return False

    @property
    def current_step(self):
        return self.steps[0]

    def is_finished(self):
        return len(self.steps) == 0

    def send_current_step(self, ctx):
        step = self.current_step

        options = getattr(step, 'options', None)
        msg = getattr(step, 'message', "...")

        ctx.send_message(msg, options=options)

    def progress(self, ctx):
        """
        Progresses the dialog.
        Returns True if the dialog is finished, False otherwise.
        """
        if self.is_finished():
            raise Exception(
                "Dialog.progress has been called after dialog is finished.")

        if self.current_step(ctx):
            self.steps = self.steps[1:]

        if self.is_finished():
            return True

        self.send_current_step(ctx)
        return False


class BaseBot:
    def __init__(self, key: str):
        self._key = key
        self.updater = Updater(token=self._key)
        self.dispatcher = self.updater.dispatcher

        self.dialogs = {}

    def wrap_context(self, ctx: Context):
        return ctx

    def _wrap_cmd(self, handler):
        def wrapper(bot: Bot, update: Update, args: List[str]=None):
            ctx = Context(self, bot, update, args)
            ctx = self.wrap_context(ctx)
            handler(ctx)

        return wrapper

    def cmd_cancel(self, ctx: Context):
        try:
            dialog = self.dialogs[ctx.chat_id]
            if dialog.cancel(ctx):
                del self.dialogs[ctx.chat_id]
        except KeyError:
            pass

    def _start_dialog_for(self, chat_id, dialog):
        self.dialogs[chat_id] = dialog

    def msg(self, ctx: Context):
        pass

    def _msg_handler(self, bot: Bot, update: Update):
        ctx = Context(self, bot, update)
        ctx = self.wrap_context(ctx)

        if ctx.chat_id in self.dialogs:
            dialog = self.dialogs[ctx.chat_id]

            if dialog.progress(ctx):
                del self.dialogs[ctx.chat_id]

            return

        self.msg(ctx)

    def _error_handler(self, bot: Bot, update: Update, error):
        raise error

    def run(self):
        for key in dir(self):
            if not key.startswith('cmd_'): continue

            cmd_name = key[4:]
            handler = self._wrap_cmd(getattr(self, key))

            self.dispatcher.add_handler(CommandHandler(
                cmd_name, handler, pass_args=True))

        self.dispatcher.add_error_handler(self._error_handler)
        self.dispatcher.add_handler(MessageHandler([Filters.text], self._msg_handler))

        self.updater.start_polling()
