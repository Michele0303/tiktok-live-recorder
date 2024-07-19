import argparse
import os
import re
import json

import logger_manager

from enums import Mode, Info, Regex
from custom_exceptions import LiveNotFound, ArgsParseError, CountryBlacklisted, \
    UserNotLiveException, AccountPrivate, IPBlockedByWAF, LiveRestriction
from http_client import HttpClient
from tiktokbot import TikTok


def banner() -> None:
    """
    Prints a banner with the name of the tool and its version number.
    """
    print(Info.BANNER)


def read_cookies():
    """
    Loads the config file and returns it.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'cookies.json')
    with open(config_path, 'r') as f:
        return json.load(f)


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="TikTok Live Recorder - A tool for recording live TikTok sessions.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "-url",
        dest="url",
        help="Record a live session from the TikTok URL.",
        action='store'
    )

    parser.add_argument(
        "-user",
        dest="user",
        help="Record a live session from the TikTok username.",
        action='store'
    )

    parser.add_argument(
        "-room_id",
        dest="room_id",
        help="Record a live session from the TikTok room ID.",
        action='store'
    )

    parser.add_argument(
        "-mode",
        dest="mode",
        help=(
            "Recording mode: (manual, automatic) [Default: manual]\n"
            "[manual] => Manual live recording.\n"
            "[automatic] => Automatic live recording when the user is live."
        ),
        default="manual",
        action='store'
    )

    parser.add_argument(
        "-proxy",
        dest="proxy",
        help=(
            "Use HTTP proxy to bypass login restrictions in some countries.\n"
            "Example: -proxy http://127.0.0.1:8080"
        ),
        action='store'
    )

    parser.add_argument(
        "-output",
        dest="output",
        help="Specify the output directory where recordings will be saved.",
        action='store'
    )

    parser.add_argument(
        "-ffmpeg",
        dest="ffmpeg",
        help="Enable recording via ffmpeg, allows real-time conversion to MP4 format.",
        action="store_const",
        const=True
    )

    parser.add_argument(
        "-duration",
        dest="duration",
        help="Specify the duration in seconds to record the live session [Default: None].",
        type=int,
        default=None,
        action='store'
    )

    parser.add_argument(
        "--auto-convert",
        dest="auto_convert",
        help="Enable automatic video conversion after recording [Default: False].",
        action='store_true'
    )

    args = parser.parse_args()

    return args


def main():

    # print banner
    banner()

    # setup logging
    logger = logger_manager.LoggerManager()

    try:
        args = parse_args()

        if not args.user and not args.room_id and not args.url:
            raise ArgsParseError("Missing URL, username, or room ID. Please provide one of these parameters.")

        if not args.mode:
            raise ArgsParseError("Missing mode value. Please specify the mode (manual or automatic).")
        if args.mode and args.mode not in ["manual", "automatic"]:
            raise ArgsParseError("Incorrect mode value. Choose between 'manual' and 'automatic'.")

        if args.url and not re.match(str(Regex.IS_TIKTOK_LIVE), args.url):
            raise LiveNotFound("The provided URL does not appear to be a valid TikTok live URL.")

        if args.user and args.room_id:
            raise ArgsParseError("Please enter either the username or the room ID, not both.")
        if args.user and args.url:
            raise ArgsParseError("Please enter either the username or the URL, not both.")
        if args.room_id and args.url:
            raise ArgsParseError("Please enter either the room ID or the URL, not both.")

        url = args.url
        user = args.user
        room_id = args.room_id
        if args.mode == "manual":
            mode = Mode.MANUAL
        else:
            mode = Mode.AUTOMATIC

        use_ffmpeg = False
        if args.ffmpeg:
            use_ffmpeg = True
        elif mode == Mode.AUTOMATIC:
            raise ArgsParseError("To use automatic mode, add -ffmpeg flag.")

        # read cookies from file
        cookies = read_cookies()

        TikTok(
            httpclient=HttpClient(logger, cookies=cookies, proxy=args.proxy),
            output=args.output,
            mode=mode,
            logger=logger,
            url=url,
            user=user,
            room_id=room_id,
            use_ffmpeg=use_ffmpeg,
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


if __name__ == '__main__':
    main()
