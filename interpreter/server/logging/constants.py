from rich.theme import Theme

LOG_CONFIG = {
    'LEVELS': {
        'DEBUG': 'dim blue',
        'INFO': 'cyan',
        'WARNING': 'yellow',
        'ERROR': 'bold red',
        'CRITICAL': 'bold white on red'
    },
    'FORMAT': '[%(asctime)s] %(levelname)-8s [%(name)s:%(lineno)d] %(message)s',
    'DATE_FORMAT': '%Y-%m-%d %H:%M:%S'
}

THEME = Theme({k: v for k, v in LOG_CONFIG['LEVELS'].items()})
