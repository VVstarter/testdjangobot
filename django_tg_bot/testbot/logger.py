import logging

logging.basicConfig(
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    level='INFO',
    datefmt='%Y-%m-%d%H:%M:%S'
)

tg_logger = logging.getLogger('TG_BOT')
