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

    def me(self):
        me_json = self._api_get('/members/me')
        return Member(self, me_json['id'], me_json['username'],
                      me_json['fullName'], me_json['url'])

    def boards(self):
        boards_json = self._api_get('/member/me/boards')
        return [Board(self, b['id'], b['name'], b['desc'], b['url'])
                for b in boards_json]


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
