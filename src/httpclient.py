import requests as req

from enums import StatusCode
from logger_manager import LoggerManager


class HttpClient:

    def __init__(self, logger: LoggerManager, proxy=None):
        self.req = None
        self.logger = logger
        self.proxy = proxy
        self.configure_session()

    def configure_session(self) -> None:
        self.req = req.Session()
        self.req.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.tiktok.com/"
        })

        self.check_proxy()

    def check_proxy(self) -> None:
        if self.proxy is None:
            return

        self.logger.info(f"Testing {self.proxy}...")
        proxies = {'http': self.proxy, 'https': self.proxy}
        try:
            resp = req.get("https://ifconfig.me/ip", proxies=proxies)
            if resp.status_code == StatusCode.OK:
                self.req.proxies.update(proxies)
                self.logger.info("Proxy set up successfully")
        except req.ConnectionError as ex:
            print(ex)
            exit(1)
