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
from utils.custom_exceptions import TikTokRecorderError

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def record_user(args, mode, cookies):
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

def run_recordings(args, mode, cookies):
    if isinstance(args.user, list):
        processes = []
        for user in args.user:
            args.user = user # set argument user to string for TikTokRecorder to use
            
            p = multiprocessing.Process(
                target=record_user,
                args=(args, mode, cookies)
            )
            p.start()
            processes.append(p)
        for p in processes:
            p.join()
    else:
        record_user(args, mode, cookies)


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

        run_recordings(args, mode, cookies)

    except TikTokRecorderError as ex:
        logger.error(f"Application Error: {ex}")

    except Exception as ex:
        logger.critical(f"Generic Error: {ex}", exc_info=True)


if __name__ == "__main__":
    main()
