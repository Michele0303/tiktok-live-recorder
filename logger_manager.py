import logging


class LoggerManager:

    def __init__(self):
        self.logger = None
        self.setup_logger()

    def setup_logger(self):
        """
        Set up logging handlers with the specified log level.
        """
        # Create an instance of Logger with the name 'logger' (you can choose a meaningful name)
        self.logger = logging.getLogger('logger')
        self.logger.setLevel(logging.INFO)  # Set the log level of the Logger to INFO

        # Create a handler for INFO level messages
        info_handler = logging.StreamHandler()
        info_handler.setLevel(logging.INFO)
        info_format = '[*] %(asctime)s - %(levelname)s - %(message)s'
        info_datefmt = '%Y-%m-%d %H:%M:%S'
        info_formatter = logging.Formatter(info_format, info_datefmt)
        info_handler.setFormatter(info_formatter)

        '''
        # Create a handler for ERROR level messages
        error_handler = logging.StreamHandler()
        error_handler.setLevel(logging.ERROR)
        error_format = '[-] %(asctime)s - %(levelname)s - %(message)s'
        error_datefmt = '%Y-%m-%d %H:%M:%S'
        error_formatter = logging.Formatter(error_format, error_datefmt)
        error_handler.setFormatter(error_formatter)
        '''

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