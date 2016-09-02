#
# common
#

MUST_AUTH = "Этот чат неавторизован. Используйте /auth, чтобы пройти авторизацию на Trello."

FORBIDDEN = "Эту команду может использовать только владелец аккаунта Trello."

#
# /start
#

START = "Доброго времени суток! Список доступных команд можно посмотреть с помощью /help"

#
# /auth
#

AUTH_URL = """
Используйте следующий url, чтобы авторизовать приложение.
После авторизации токен доступ отобразится во фрагменте url страницы.
Отправьте его сюда командой /auth

Например, /auth 1c395f7208a94024a95d

[Перейти к авторизации]({url})
"""

AUTH_SUCCESS = """
Добро пожаловать, *{fullname}*! Вы успешно авторизовались.
"""

AUTH_FAILURE = "К сожалению, токен недействителен."

AUTH_ALREADY = """
Этот чат уже авторизован.
Используйте /status, чтобы посмотреть, от чьего имени.
"""

AUTH_GO_PRIVATE = """
Пожалуйста, авторизуйтесь сначала с личном чате с ботом, используя ту же команду: /auth
"""

#
# /status
#

STATUS_INVALID_TOKEN = """
Токен авторизации для этого чата больше не действителен.

Используйте /unauth, чтобы удалить сессию, а затем /auth, чтобы пройти авторизацию заново.
"""

STATUS_OK = "Этот чат использует аккаунт Trello *{fullname}*, \
по авторизации пользователя Telegram *{admin}*"

#
# /unauth
#

UNAUTH_SUCCESS = """
Готово!
Этот чат больше не авторизован.
"""

#
# /notify
#

NOTIFY_DLG_MSG = "Выберите доску, по которой хотите получать уведомления:"

NOTIFY_NOBOARD = "Такой доски нет, пожалуйсте выберите одну из представленных досок."

NOTIFY_ALREADY = "По этой доске уведомления уже подключены."

NOTIFY_SUCCESS = "Уведомления по доске успешно подключены в этот чат."

NOTIFY_CANCELLED = "Подключение доски отменено."

#
# /list
#

LIST = """
Этот чат получает уведомления по следующим доскам:

{list}
"""

LIST_ITEM = "*{board}*"

#
# /forget
#

FORGET_DLG_MSG = "Выберите доску, которую следует отключить:"

FORGET_NOBOARD = "Такой доски нет, пожалуйсте выберите одну из представленных досок."

FORGET_SUCCESS = "Уведомления по доске успешно отключены."

FORGET_CANCELLED = "Отключение доски отменено."

#
# /dev
#

DEV = """
Сессия (=чат) *{session_id}*
Отправитель *{sender_id}*
Админ *{admin_id}*
"""

#
# /help
#

HELP = """
Доступные команды:

/auth - Авторизовать чат в Trello
/unauth - Сбросить авторизацию +
/status - Статус авторизации
/notify - Подключить доску +
/forget - Отключить доску +
/list - Список подключенных досок
/help - Помощь
/cancel - Отменить текущее действие

Команды помеченные плюсом (+) в групповых чатах могут быть вызваны только пользователем, который авторизовал бота.
"""

#
# Notifications from Trello webhooks
#

HOOK_CARD_CREATED = """
_{user_name}_ создал карточку
*{card_text}* ([ссылка]({card_url}))
в списке _{list_name}_

на доске [{board_name}]({board_url})
"""

HOOK_CARD_MOVED = """
_{user_name}_ переместил карточку
*{card_text}* ([ссылка]({card_url}))
из списка _{old_list_name}_
в список _{new_list_name}_

на доске [{board_name}]({board_url})
"""

HOOK_CARD_ARCHIVED = """
_{user_name}_ заархивировал карточку
*{card_text}* ([ссылка]({card_url}))
из списка _{list_name}_

на доске [{board_name}]({board_url})
"""

HOOK_CARD_COMMENTED = """
_{user_name}_ прокомментировал карточку
*{card_text}* ([ссылка]({card_url}))

{text}

на доске [{board_name}]({board_url})
"""

HOOK_CARD_MEMBER_ADDED = """
_{user_name}_ добавил _{other_user_name}_ к карточке
*{card_text}* ([ссылка]({card_url}))

на доске [{board_name}]({board_url})
"""

HOOK_CARD_SELF_ADDED = """
_{user_name}_ добавил себя к карточке
*{card_text}* ([ссылка]({card_url}))

на доске [{board_name}]({board_url})
"""

HOOK_CARD_MEMBER_REMOVED = """
_{user_name}_ удалил _{other_user_name}_ из карточки
*{card_text}* ([ссылка]({card_url}))

на доске [{board_name}]({board_url})
"""

HOOK_CARD_SELF_REMOVED = """
_{user_name}_ удалил себя из карточки
*{card_text}* ([ссылка]({card_url}))

на доске [{board_name}]({board_url})
"""
