import logging

class MaxLevelFilter(logging.Filter):
    """
    Filter that only allows log records up to a specified maximum level.
    """
    def __init__(self, max_level):
        super().__init__()
        self.max_level = max_level

    def filter(self, record):
        # Only accept records whose level number is <= self.max_level
        return record.levelno <= self.max_level

class LoggerManager:

    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance.logger = None
            cls._instance.setup_logger()
        return cls._instance

    def setup_logger(self):
        if self.logger is None:
            self.logger = logging.getLogger('logger')
            self.logger.setLevel(logging.INFO)

            # 1) INFO handler
            info_handler = logging.StreamHandler()
            info_handler.setLevel(logging.INFO)
            info_format = '[*] %(asctime)s - %(message)s'
            info_datefmt = '%Y-%m-%d %H:%M:%S'
            info_formatter = logging.Formatter(info_format, info_datefmt)
            info_handler.setFormatter(info_formatter)

            # Add a filter to exclude ERROR level (and above) messages
            info_handler.addFilter(MaxLevelFilter(logging.INFO))

            self.logger.addHandler(info_handler)

            # 2) ERROR handler
            error_handler = logging.StreamHandler()
            error_handler.setLevel(logging.ERROR)
            error_format = '[!] %(asctime)s - %(message)s'
            error_datefmt = '%Y-%m-%d %H:%M:%S'
            error_formatter = logging.Formatter(error_format, error_datefmt)
            error_handler.setFormatter(error_formatter)

            self.logger.addHandler(error_handler)

    def info(self, message):
        """
        Log an INFO-level message.
        """
        self.logger.info(message)

    def error(self, message):
        """
        Log an ERROR-level message.
        """
        self.logger.error(message)


logger = LoggerManager().logger
