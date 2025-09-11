import argparse
import re

from utils.custom_exceptions import ArgsParseError
from utils.enums import Mode, Regex


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="TikTok Live Recorder - A tool for recording live TikTok sessions.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "-url",
        dest="url",
        help="Record a live session from the TikTok URL.",
        action="store",
    )

    parser.add_argument(
        "-user",
        dest="user",
        help="Record a live session from the TikTok username.",
        action="store",
    )

    parser.add_argument(
        "-room_id",
        dest="room_id",
        help="Record a live session from the TikTok room ID.",
        action="store",
    )

    parser.add_argument(
        "-mode",
        dest="mode",
        help=(
            "Recording mode: (manual, automatic, followers) [Default: manual]\n"
            "[manual] => Manual live recording.\n"
            "[automatic] => Automatic live recording when the user is live.\n"
            "[followers] => Automatic live recording of followed users."
        ),
        default="manual",
        action="store",
    )

    parser.add_argument(
        "-automatic_interval",
        dest="automatic_interval",
        help="Sets the interval in minutes to check if the user is live in automatic mode. [Default: 5]",
        type=int,
        default=5,
        action="store",
    )

    parser.add_argument(
        "-proxy",
        dest="proxy",
        help=(
            "Use HTTP proxy to bypass login restrictions in some countries.\n"
            "Example: -proxy http://127.0.0.1:8080"
        ),
        action="store",
    )

    parser.add_argument(
        "-output",
        dest="output",
        help=("Specify the output directory where recordings will be saved.\n"),
        action="store",
    )

    parser.add_argument(
        "-duration",
        dest="duration",
        help="Specify the duration in seconds to record the live session [Default: None].",
        type=int,
        default=None,
        action="store",
    )

    parser.add_argument(
        "-telegram",
        dest="telegram",
        action="store_true",
        help="Activate the option to upload the video to Telegram at the end "
        "of the recording.\nRequires configuring the telegram.json file",
    )

    parser.add_argument(
        "-no-update-check",
        dest="update_check",
        action="store_false",
        help=(
            "Disable the check for updates before running the program. "
            "By default, update checking is enabled."
        ),
    )

    args = parser.parse_args()

    return args


def validate_and_parse_args():
    args = parse_args()

    if not args.mode:
        raise ArgsParseError(
            "Missing mode value. Please specify the mode (manual, automatic or followers)."
        )
    if args.mode not in ["manual", "automatic", "followers"]:
        raise ArgsParseError(
            "Incorrect mode value. Choose between 'manual', 'automatic' or 'followers'."
        )

    if args.mode in ["manual", "automatic"]:
        if not args.user and not args.room_id and not args.url:
            raise ArgsParseError(
                "Missing URL, username, or room ID. Please provide one of these parameters."
            )

    if args.user:
        args.user = [u.lstrip("@").strip() for u in args.user.split(",") if u.strip()]

    if args.user and len(args.user) > 1 and (args.room_id or args.url):
        raise ArgsParseError(
            "When using multiple usernames, do not provide room_id or url."
        )

    if args.url and not re.match(str(Regex.IS_TIKTOK_LIVE), args.url):
        raise ArgsParseError(
            "The provided URL does not appear to be a valid TikTok live URL."
        )

    if (
        (args.user and args.room_id)
        or (args.user and args.url)
        or (args.room_id and args.url)
    ):
        raise ArgsParseError("Please provide only one among username, room ID, or URL.")

    # Edit: now arg.user is a list
    if args.user and len(args.user) == 1:
        args.user = args.user[0]

    if (
        (isinstance(args.user, str) and args.user and args.room_id)
        or (isinstance(args.user, str) and args.user and args.url)
        or (args.room_id and args.url)
    ):
        raise ArgsParseError("Please provide only one among username, room ID, or URL.")

    if args.automatic_interval < 1:
        raise ArgsParseError(
            "Incorrect automatic_interval value. Must be one minute or more."
        )

    if args.mode == "manual":
        mode = Mode.MANUAL
    elif args.mode == "automatic":
        mode = Mode.AUTOMATIC
    elif args.mode == "followers":
        mode = Mode.FOLLOWERS

    return args, mode
