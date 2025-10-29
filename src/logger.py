import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

class Logger:
    @staticmethod
    def get_logger(name: str, log_file: str = "logs/dyskownik.log", level: str = "INFO") -> logging.Logger:

        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding='utf-8',
            delay=True
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)

        if not logger.handlers:
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

        logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

        return logger
