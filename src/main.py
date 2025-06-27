# print banner
from utils.utils import banner

banner()

# check and install dependencies
from utils.dependencies import check_and_install_dependencies

check_and_install_dependencies()

from check_updates import check_updates

import sys
import os
import multiprocessing

from utils.args_handler import validate_and_parse_args
from utils.utils import read_cookies
from utils.logger_manager import logger

from core.tiktok_recorder import TikTokRecorder
from utils.enums import TikTokError
from utils.custom_exceptions import LiveNotFound, ArgsParseError, \
    UserLiveException, IPBlockedByWAF, TikTokException

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def record_user(user, args, mode, cookies):
    try:
        logger.info(f"Starting recording for user: {user}")
        TikTokRecorder(
            url=None,
            user=user,
            room_id=None,
            mode=mode,
            automatic_interval=args.automatic_interval,
            cookies=cookies,
            proxy=args.proxy,
            output=args.output,
            duration=args.duration,
            use_telegram=args.telegram,
        ).run()
    except Exception as ex:
        logger.error(f"Error for user {user}: {ex}")

def main():
    try:
        args, mode = validate_and_parse_args()

        # check for updates
        if args.update_check is True:
            logger.info("Checking for updates...\n")
            if check_updates():
                exit()
        else:
            logger.info("Skipped update check\n")

        # read cookies from file
        cookies = read_cookies()

        if isinstance(args.user, list):
            processes = []
            for user in args.user:
                p = multiprocessing.Process(
                    target=record_user,
                    args=(user, args, mode, cookies)
                )
                p.start()
                processes.append(p)
            for p in processes:
                p.join()
        else:
            TikTokRecorder(
                url=args.url,
                user=args.user,
                room_id=args.room_id,
                mode=mode,
                automatic_interval=args.automatic_interval,
                cookies=cookies,
                proxy=args.proxy,
                output=args.output,
                duration=args.duration,
                use_telegram=args.telegram,
            ).run()

    except ArgsParseError as ex:
        logger.error(ex)

    except LiveNotFound as ex:
        logger.error(ex)

    except IPBlockedByWAF:
        logger.error(TikTokError.WAF_BLOCKED)

    except UserLiveException as ex:
        logger.error(ex)

    except TikTokException as ex:
        logger.error(ex)

    except Exception as ex:
        logger.error(ex)


if __name__ == "__main__":
    main()
