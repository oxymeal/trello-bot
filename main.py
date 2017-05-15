#!/usr/bin/env python3
import logging

import config
from bot import TrelloBot

if hasattr(config, 'LOG_FILE') and hasattr(config, 'LOG_LEVEL'):
    logging.basicConfig(
        filename=config.LOG_FILE,
        format="[{name}|{levelname}|{asctime}] {message}",
        style='{',
        datefmt="%Y-%m-%d %H:%M:%S",
        level=getattr(logging, config.LOG_LEVEL.upper()))

try:
    TrelloBot(config.TELEGRAM_KEY, config.TRELLO_KEY).run()
except Exception as e:
    logging.critical("Could not start bot: {}.".format(repr(e)))
    raise
