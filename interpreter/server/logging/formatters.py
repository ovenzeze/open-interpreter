import logging
from rich.logging import RichHandler
from rich.console import Console
from .constants import LOG_CONFIG, THEME

class ServerFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(
            fmt=LOG_CONFIG['FORMAT'],
            datefmt=LOG_CONFIG['DATE_FORMAT']
        )

class ServerRichHandler(RichHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(
            console=Console(theme=THEME),
            show_time=True,
            show_path=True,
            enable_link_path=True,
            rich_tracebacks=True,
            markup=True,
            *args,
            **kwargs
        )
