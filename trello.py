import urllib.parse

import requests

TRELLO_API_URL = 'https://trello.com/1'


class AuthError(Exception):
    def __init__(self, session):
        self.session = session
        super().__init__("Request was denied; app key = {}, token = {}".format(
            self.session.app.key, self.session.token))


class UnknownStatusError(Exception):
    def __init__(self, session, status_code, text):
        self.session = session
        self.status_code = status_code
        self.text = text

        if len(self.text) > 12:
            display_text = self.text[:9] + '...'
        else:
            display_text = self.text

        super().__init__("Unknown response status {}: {}", self.status_code,
                         display_text)


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

    def _api_get(self, url, params=None):
        if params is None: params = {}

        params['key'] = self.app.key
        params['token'] = self.token

        r = requests.get(TRELLO_API_URL + url, params=params)

        if r.status_code == 401:
            raise AuthError(self)
        elif r.status_code != 200:
            raise UnknownStatusError(self, r.status_code, r.text)

        return r.json()

    def boards(self):
        boards_json = self._api_get('/member/me/boards')
        return [Board(self, b['id'], b['name'], b['desc'], b['url'])
                for b in boards_json]

    def me(self):
        me_json = self._api_get('/members/me')
        return Member(self, me_json['id'], me_json['username'],
                      me_json['fullName'], me_json['url'])


class Member:
    def __init__(self, session, id, username, fullname, url):
        self.session = session
        self.id = id
        self.username = username
        self.fullname = fullname
        self.url = url


class Board:
    def __init__(self, session, id, name, desc, url):
        self.session = session
        self.id = id
        self.name = name
        self.desc = desc
        self.url = url

    def lists(self):
        lists_json = self.session._api_get('/boards/{}/lists'.format(self.id))
        return [List(self.session, l['id'], l['name']) for l in lists_json]


class List:
    def __init__(self, session, id, name):
        self.session = session
        self.id = id
        self.name = name
