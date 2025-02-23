import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

class DailyRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename):
        super().__init__(
            filename=filename,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
