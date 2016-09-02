from multiprocessing import Process

from flask import Flask, abort, request

from bot import trello, messages
from bot.models import BoardHook, Session

app = Flask(__name__)

class WebhookReciever:
    update_url = '/webhook_update/<chat_id>'

    def __init__(self, trello_bot, host, port):
        self.bot = trello_bot
        self.app = self.bot.trello_app
        self.host = host
        self.port = port

        self.flask = Flask(__name__)
        self.flask.add_url_rule(self.update_url, view_func=self.webhook_update,
                                methods=['POST', 'HEAD'])

        self.flask_process = None

    def callback_url(self, chat_id):
        return "http://{host}:{port}{url}".format(
            host=self.host,
            port=self.port,
            url=self.update_url.replace('<chat_id>', str(chat_id)))

    @staticmethod
    def _action_to_msg(action):
        user = action.member_creator()
        board = action.board
        list = getattr(action, 'list', None)
        card = action.card
        msg = None

        if action.type == 'createCard':
            msg = messages.HOOK_CARD_CREATED.format(
                user_name=user.fullname,
                card_text=card.name,
                card_url=card.url,
                list_name=list.name,
                board_name=board.name,
                board_url=board.url,
            )
        elif action.type == 'updateCard' and action.changed_field == 'idList':
            old_list = action.list_before
            new_list = action.list_after

            msg = messages.HOOK_CARD_MOVED.format(
                user_name=user.fullname,
                card_text=card.name,
                card_url=card.url,
                old_list_name=old_list.name,
                new_list_name=new_list.name,
                board_name=board.name,
                board_url=board.url,
            )
        elif action.type == 'updateCard' and action.changed_field == 'closed':
            msg = messages.HOOK_CARD_ARCHIVED.format(
                user_name=user.fullname,
                card_text=card.name,
                card_url=card.url,
                list_name=list.name,
                board_name=board.name,
                board_url=board.url,
            )
        elif action.type == 'commentCard':
            msg = messages.HOOK_CARD_COMMENTED.format(
                user_name=user.fullname,
                card_text=card.name,
                card_url=card.url,
                text=action.text,
                board_name=board.name,
                board_url=board.url,
            )
        elif action.type == 'addMemberToCard':
            if action.member.id == user.id:
                msg = messages.HOOK_CARD_SELF_ADDED.format(
                    user_name=user.fullname,
                    card_text=card.name,
                    card_url=card.url,
                    board_name=board.name,
                    board_url=board.url,
                )
            else:
                msg = messages.HOOK_CARD_MEMBER_ADDED.format(
                    user_name=user.fullname,
                    other_user_name=action.member.fullname,
                    card_text=card.name,
                    card_url=card.url,
                    board_name=board.name,
                    board_url=board.url,
                )
        elif action.type == 'removeMemberFromCard':
            if action.member.id == user.id:
                msg = messages.HOOK_CARD_SELF_REMOVED.format(
                    user_name=user.fullname,
                    card_text=card.name,
                    card_url=card.url,
                    board_name=board.name,
                    board_url=board.url,
                )
            else:
                msg = messages.HOOK_CARD_MEMBER_REMOVED.format(
                    user_name=user.fullname,
                    other_user_name=action.member.fullname,
                    card_text=card.name,
                    card_url=card.url,
                    board_name=board.name,
                    board_url=board.url,
                )

        return msg

    def webhook_update(self, chat_id):
        if request.method == 'HEAD':
            return "OK"

        try:
            session = Session.get(Session.chat_id == chat_id)
        except Session.DoesNotExist:
            abort(404, 'No session with that chat id is found')

        data = request.json
        if not data:
            abort(400, 'Request must contain json data')

        try:
            id_model = data["model"]["id"]
        except (KeyError, TypeError):
            abort(400, '.model.id field is required')

        for h in session.hooks:
            if h.board_id == id_model:
                hook = h
                break
        else:
            # Trello will automatically delete the webhook,
            # when they recieve status 410.
            # Source: https://developers.trello.com/apis/webhooks
            abort(410, 'Such hook does not exist')

        trello_session = self.app.session(session.trello_token)

        try:
            action = trello.Action.from_dict(trello_session, data['action'])
        except (KeyError, TypeError) as e:
            abort(400, '.action object is invalid')

        msg = self._action_to_msg(action)

        # If None was returned, then this type of actions is not supported.
        if not msg:
            return "OK"

        self.bot.send_message(chat_id=chat_id, text=msg)
        return "OK"

    def start(self):
        self.flask_process = Process(target=self.flask.run,
                                     kwargs={'host': self.host, 'port': self.port})
        self.flask_process.start()

    def stop(self):
        if not self.flask_process:
            return

        self.flask_process.terminate()
        self.flask_process = None
