import urllib.parse

import requests

TRELLO_API_URL = 'https://trello.com/1'


class TrelloError(Exception):
    def __init__(self, session, status_code, url, text, desc="API call error"):
        self.session = session
        self.status_code = status_code
        self.url = url
        self.text = text

        maxlen = 255
        if len(self.text) > maxlen:
            display_text = self.text[:(maxlen-3)] + '...'
        else:
            display_text = self.text

        super().__init__("{desc}: {url} -> {status_code} {display_text}"
                         .format(desc=desc, url=url,
                                 status_code=status_code,
                                 display_text=display_text))

class CustomTrelloError(TrelloError):
    status_code = 0
    desc = ""

    def __init__(self, session, url, text):
        super().__init__(session, self.status_code, url, text, self.desc)

class AuthError(CustomTrelloError):
    status_code = 401
    desc = "Request was denied"

class NotFoundError(CustomTrelloError):
    status_code = 404
    desc = "URL not found"

class RequestError(CustomTrelloError):
    status_code = 400
    desc = "Invalid data"


class App:
    def __init__(self, key):
        self.key = key

    def auth_url(self):
        params = {
            'callback_method': 'fragment',
            'return_url': 'http://example.com/',
            'scope': 'read',
            'expiration': 'never',
            'name': 'Oxymeal Trello Bot',
            'key': self.key,
        }
        return TRELLO_API_URL + '/authorize?' + urllib.parse.urlencode(params)

    def session(self, token):
        return Session(self, token)


class Session:
    def __init__(self, app, token):
        self.app = app
        self.token = token

        self.members = MembersAPI(self)
        self.actions = ActionsAPI(self)
        self.webhooks = WebhooksAPI(self)

        self.boards = BoardsAPI(self)
        self.lists = ListsAPI(self)
        self.cards = CardsAPI(self)

    def _api_request(self, method, url, params=None, data=None):
        if params is None: params = {}

        params['key'] = self.app.key
        params['token'] = self.token

        r = requests.request(method, TRELLO_API_URL + url, params=params, data=data)

        if r.status_code == 400:
            raise RequestError(self, url, r.text)
        if r.status_code == 401:
            raise AuthError(self, url, r.text)
        if r.status_code == 404:
            raise NotFoundError(self, url, r.text)
        elif r.status_code != 200:
            raise TrelloError(self, r.status_code, url, r.text)

        return r.json()

    def _api_get(self, url, *, params=None):
        return self._api_request('get', url, params)

    def _api_post(self, url, *, params=None, data=None):
        return self._api_request('post', url, params, data)

    def _api_put(self, url, *, params=None, data=None):
        return self._api_request('put', url, params, data)

    def _api_delete(self, url, *, params=None):
        return self._api_request('delete', url, params)


class API:
    def __init__(self, session, model_class):
        self.session = session
        self.model_class = model_class

    @property
    def url_base(self):
        return self.model_class.url_base

    def all(self):
        json = self.session._api_get(self.url_base)
        return [self.model_class.from_dict(self.session, m) for m in json]

    def get(self, id):
        json = self.session._api_get(self.url_base + '/' + id)
        return self.model_class.from_dict(self.session, json)

    def add(self, **kwargs):
        json = self.session._api_post(self.url_base, data=kwargs)
        return self.model_class.from_dict(self.session, m)

class MembersAPI(API):
    def __init__(self, session):
        super().__init__(session, Member)

    def me(self):
        json = self.session._api_get(self.url_base + '/me')
        return Member.from_dict(self.session, json)

class ActionsAPI(API):
    def __init__(self, session):
        super().__init__(session, Action)

class WebhooksAPI(API):
    def __init__(self, session):
        super().__init__(session, Webhook)

class BoardsAPI(API):
    def __init__(self, session):
        super().__init__(session, Board)

class ListsAPI(API):
    def __init__(self, session):
        super().__init__(session, List)

class CardsAPI(API):
    def __init__(self, session):
        super().__init__(session, Card)

class Model:
    url_base = ''

    def __init__(self, session, id):
        self.session = session
        self.id = id

    @classmethod
    def from_dict(cls, session, d):
        return Model(session, d['id'])

    def _sub_url(self, url):
        return "{base}/{id}{url}".format(base=self.url_base, id=self.id, url=url)

    def delete(self):
        self._api_delete(self.url_base + '/' + self.id)

class Member(Model):
    url_base = '/members'

    def __init__(self, session, id, username, fullname, url):
        self.session = session
        self.id = id
        self.username = username
        self.fullname = fullname
        self.url = url

    @classmethod
    def from_dict(cls, session, d):
        return Member(session,
                      d['id'],
                      d['username'],
                      d.get('fullName'),
                      d.get('url'))

    def boards(self, *, filter=None):
        params = {}

        if filter:
            if isinstance(filter, list):
                filter = ','.join(filter)
            params['filter'] = filter

        json = self.session._api_get(self._sub_url('/boards'), params=params)
        return [Board.from_dict(self.session, d) for d in json]

class Action(Model):
    url_base = '/actions'

    def __init__(self, session, id, id_member_creator, type,
                 changed_field=None, old_value=None):
        super().__init__(session, id)

        self.id_member_creator = id_member_creator
        self.type = type

        if changed_field:
            self.changed_field = changed_field
            self.old_value = old_value

    @classmethod
    def from_dict(cls, session, d):
        action = Action(session, d['id'], d['idMemberCreator'], d['type'])

        data = d['data']
        if 'board' in data:
            action.board = Board.from_dict(session, data['board'])
        if 'list' in data:
            action.list = List.from_dict(session, data['list'])
        if 'card' in data:
            action.card = Card.from_dict(session, data['card'])
            if hasattr(action, 'list'):
                action.card.id_list = action.list.id

        if 'old' in data:
            action.changed_field = list(data['old'].keys())[0]
            action.old_value = data['old'][action.changed_field]

        return action

    def member_creator(self):
        return self.session.members.get(self.id_member_creator)

class Webhook(Model):
    url_base = '/webhooks'

    def __init__(self, session, id, callback_url, id_model, description=""):
        super().__init__(session, id)

        self.callback_url = callback_url
        self.id_model = id_model
        self.description = description

    @classmethod
    def from_dict(cls, session, d):
        return Webhook(session,
                       d['id'],
                       d['callbackURL'],
                       d['idModel'],
                       d.get('description'))

class Card(Model):
    url_base = '/cards'

    def __init__(self, session, id, name, id_list, short_link=None):
        self.session = session
        self.id = id
        self.name = name
        self.id_list = id_list
        self.short_link = short_link

    @classmethod
    def from_dict(cls, session, d):
        return Card(session,
                    d['id'],
                    d['name'],
                    d.get('id_list'),
                    d.get('shortLink'))

    @property
    def url(self):
        return "https://trello.com/c/{}/".format(self.short_link)

    def list(self):
        return self.session.lists.get(self.id_list)

class Board(Model):
    url_base = '/boards'

    def __init__(self, session, id, name, desc, short_link=None):
        self.session = session
        self.id = id
        self.name = name
        self.desc = desc
        self.short_link = short_link

    @classmethod
    def from_dict(self, session, d):
        return Board(session,
                     d['id'],
                     d['name'],
                     d.get('desc'),
                     d.get('shortLink'))

    @property
    def url(self):
        return "https://trello.com/b/{}/".format(self.short_link)

    def actions(self):
        json = self.session._api_get(self._sub_url('/actions'))
        return [Action.from_dict(self.session, d) for d in json]

    def lists(self):
        json = self.session._api_get(self._sub_url('/lists'))
        return [List.from_dict(self.session, d) for d in json]


class List(Model):
    url_base = '/lists'

    def __init__(self, session, id, name):
        self.session = session
        self.id = id
        self.name = name

    @classmethod
    def from_dict(self, session, d):
        return List(session,
                     d['id'],
                     d['name'])

    def board(self):
        json = self.session._api_get(self._sub_url('/board'))
        return Board.from_dict(self.session, json)

    def cards(self):
        json = self.session._api_get(self._sub_url('/cards'))

        cs = [Card.from_dict(self.session, d) for d in json]
        for c in cs:
            c.id_list = self.id

        return cs
