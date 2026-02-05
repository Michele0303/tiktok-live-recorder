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

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance.logger = None  # Initialize the attribute
            cls._instance._init_logger_if_needed()  # Ensure logger is set up
        return cls._instance

    def _init_logger_if_needed(self):
        if self.logger is None:
            self.logger = logging.getLogger("logger")
            self.logger.setLevel(logging.INFO)  # Default to INFO

            # Add a basic stream handler if no handlers are present
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter("[*] %(asctime)s - %(message)s")
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)

    def setup_logger(self, verbose: bool = False):
        self._init_logger_if_needed()  # Ensure base logger exists

        # Clear existing handlers to prevent duplicates if called multiple
        # times
        if self.logger.handlers:
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)

        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)

        # 1) INFO / DEBUG handler
        info_debug_level = logging.DEBUG if verbose else logging.INFO
        info_handler = logging.StreamHandler()
        info_handler.setLevel(info_debug_level)
        info_format = "[*] %(asctime)s - %(message)s"
        info_datefmt = "%Y-%m-%d %H:%M:%S"
        info_formatter = logging.Formatter(info_format, info_datefmt)
        info_handler.setFormatter(info_formatter)

        # Add a filter to exclude ERROR level (and above) messages
        if not verbose:  # Only apply filter if not verbose
            info_handler.addFilter(MaxLevelFilter(logging.INFO))

        self.logger.addHandler(info_handler)

        # 2) ERROR handler
        error_handler = logging.StreamHandler()
        error_handler.setLevel(logging.ERROR)
        error_format = "[!] %(asctime)s - %(message)s"
        error_datefmt = "%Y-%m-%d %H:%M:%S"
        error_formatter = logging.Formatter(error_format, error_datefmt)
        error_handler.setFormatter(error_formatter)

        self.logger.addHandler(error_handler)

    # Existing info, error methods ...

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
