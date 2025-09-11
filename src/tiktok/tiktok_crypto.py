import json
import time
from typing import Dict, Any
from urllib.parse import urlencode

from .encryption.xbogus import sign_xbogus
from .encryption.xgnarly import sign_xgnarly


def sign_params(data: Dict[str, Any], user_agent: str) -> str:
    """
    Sign TikTok API parameters with X-Bogus and X-Gnarly signatures

    Args:
        data: Dictionary containing:
            - params: Dictionary of query parameters
            - url: Base API URL
            - body: Optional request body (for POST requests)
        user_agent: User-Agent string to use for signing

    Returns:
        Fully signed URL with X-Bogus and X-Gnarly parameters
    """
    # Build query string from parameters
    query_string = urlencode(data["params"])

    # Handle request body
    body = ""
    if "body" in data and data["body"]:
        body = json.dumps(data["body"])

    # Generate current timestamp
    current_timestamp = int(time.time())

    # Generate X-Bogus signature
    x_bogus = sign_xbogus(query_string, body, user_agent, current_timestamp)

    # Generate X-Gnarly signature
    x_gnarly = sign_xgnarly(
        query_string,  # query string
        body,  # POST body
        user_agent,  # user-agent
        0,  # envcode
        "5.1.1",  # version
    )

    # Build final signed URL
    signed_url = f"{data['url']}/?{query_string}&X-Bogus={x_bogus}&X-Gnarly={x_gnarly}"

    return signed_url
