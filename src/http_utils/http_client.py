import requests

from utils.enums import StatusCode
from utils.logger_manager import logger
from utils.utils import is_termux


class HttpClient:
    def __init__(self, proxy=None, cookies=None):
        self.req = None
        self.req_stream = requests

        self.proxy = proxy
        self.cookies = cookies
        self.headers = {
            "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Accept-Language": "en-US",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.127 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,application/json,text/plain,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Priority": "u=0, i",
            "Referer": "https://www.tiktok.com/",
            "Origin": "https://www.tiktok.com",
        }

        self.configure_session()

    def configure_session(self) -> None:
        self.req_stream = requests.Session()

        if is_termux():
            self.req = self.req_stream
        else:
            from curl_cffi import Session, CurlSslVersion, CurlOpt

            self.req = Session(
                impersonate="chrome136",
                http_version="v1",
                curl_options={CurlOpt.SSLVERSION: CurlSslVersion.TLSv1_2},
            )

        self.req.headers.update(self.headers)
        self.req_stream.headers.update(self.headers)

        if self.cookies is not None:
            self.req.cookies.update(self.cookies)
            self.req_stream.cookies.update(self.cookies)

        self.check_proxy()

    def check_proxy(self) -> None:
        if self.proxy is None:
            return

        logger.info(f"Testing {self.proxy}...")
        proxies = {"http": self.proxy, "https": self.proxy}

        response = requests.get("https://ifconfig.me/ip", proxies=proxies, timeout=10)

        if response.status_code == StatusCode.OK:
            self.req.proxies.update(proxies)
            logger.info("Proxy set up successfully")
