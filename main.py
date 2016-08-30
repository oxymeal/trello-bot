#!/usr/bin/env python3
import config
from bot import TrelloBot

TrelloBot(config.TELEGRAM_KEY, config.TRELLO_KEY).run()
