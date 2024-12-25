from utils.dependencies import check_and_install_dependencies
from utils.utils import banner

# print banner
banner()

# check and install dependencies
check_and_install_dependencies()

import sys
import os

from utils.args_handler import validate_and_parse_args
from utils.utils import read_cookies
from utils.logger_manager import logger
from check_updates import check_updates
from http_utils.http_client import HttpClient
from core.tiktokbot import TikTok
from utils.custom_exceptions import LiveNotFound, ArgsParseError, \
    CountryBlacklisted, UserNotLiveException, AccountPrivate, \
    IPBlockedByWAF, LiveRestriction


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    # check for updates
    if check_updates():
        exit()

    try:
        args, mode = validate_and_parse_args()

        # read cookies from file
        cookies = read_cookies()

        TikTok(
            httpclient=HttpClient(cookies=cookies, proxy=args.proxy),
            output=args.output,
            mode=mode,
            url=args.url,
            user=args.user,
            room_id=args.room_id,
            use_ffmpeg=args.ffmpeg,
            duration=args.duration,
            convert=args.auto_convert,
            cookies=cookies
        ).run()

    except ArgsParseError as ex:
        logger.error(ex)

    except LiveNotFound as ex:
        logger.error(ex)

    except LiveRestriction as ex:
        logger.error(ex)

    except AccountPrivate as ex:
        logger.error(ex)

    except UserNotLiveException as ex:
        logger.error(ex)

    except CountryBlacklisted as ex:
        logger.error(ex)

    except IPBlockedByWAF as ex:
        logger.error(ex)

    except Exception as ex:
        logger.error(ex)


if __name__ == "__main__":
    main()
