import signal
import sys
import os
import multiprocessing

from utils.utils import banner, read_cookies
from utils.dependencies import check_and_install_dependencies
from utils.args_handler import validate_and_parse_args
from utils.logger_manager import logger
from utils.custom_exceptions import TikTokRecorderError

from check_updates import check_updates

from core.tiktok_recorder import TikTokRecorder

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def record_user(
    user, url, room_id, mode, interval, proxy, output, duration,
    use_telegram, cookies
):
    try:
        TikTokRecorder(
            url=url,
            user=user,
            room_id=room_id,
            mode=mode,
            automatic_interval=interval,
            cookies=cookies,
            proxy=proxy,
            output=output,
            duration=duration,
            use_telegram=use_telegram,
        ).run()
    except Exception as e:
        logger.error(f"Error in subprocess for @{user}: {e}")


def run_recordings(args, mode, cookies):
    if isinstance(args.user, list):
        processes = []
        for user in args.user:
            p = multiprocessing.Process(
                target=record_user,
                args=(
                    user,
                    args.url,
                    args.room_id,
                    mode,
                    args.automatic_interval,
                    args.proxy,
                    args.output,
                    args.duration,
                    args.telegram,
                    cookies
                )
            )
            p.start()
            processes.append(p)
        for p in processes:
            p.join()
    else:
        record_user(
            args.user,
            args.url,
            args.room_id,
            mode,
            args.automatic_interval,
            args.proxy,
            args.output,
            args.duration,
            args.telegram,
            cookies
        )


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

        cookies = read_cookies()
        run_recordings(args, mode, cookies)

    except TikTokRecorderError as ex:
        logger.error(f"Application Error: {ex}")

    except Exception as ex:
        logger.critical(f"Generic Error: {ex}", exc_info=True)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    multiprocessing.freeze_support()

    banner()
    check_and_install_dependencies()

    main()
