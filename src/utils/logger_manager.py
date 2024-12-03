import logging

class LoggerManager:

    _instance = None  # Singleton instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            cls._instance.logger = None
            cls._instance.setup_logger()
        return cls._instance

    def setup_logger(self):
        """
        Set up logging handlers with the specified log level.
        """
        if self.logger is None:
            # Create an instance of Logger with the name 'logger'
            self.logger = logging.getLogger('logger')
            self.logger.setLevel(logging.INFO)

            # Create a handler for INFO level messages
            info_handler = logging.StreamHandler()
            info_handler.setLevel(logging.INFO)
            info_format = '[*] %(asctime)s - %(levelname)s - %(message)s'
            info_datefmt = '%Y-%m-%d %H:%M:%S'
            info_formatter = logging.Formatter(info_format, info_datefmt)
            info_handler.setFormatter(info_formatter)

            self.logger.addHandler(info_handler)

    def info(self, message):
        """
        Log an info message.
        """
        self.logger.info(message)

    def error(self, message):
        """
        Log an error message.
        """
        self.logger.error(message)


logger = LoggerManager().logger
