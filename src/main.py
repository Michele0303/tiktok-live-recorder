import sys
import os
import multiprocessing

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def record_user(
    user,
    url,
    room_id,
    mode,
    interval,
    proxy,
    output,
    duration,
    use_telegram,
    cookies,
    ffmpeg_encode,
    app_logger,
    keep_flv,
):
    from core.tiktok_recorder import TikTokRecorder
    # Do not import logger here, use app_logger passed as argument

    try:
        return TikTokRecorder(
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
            ffmpeg_encode=ffmpeg_encode,
            app_logger=app_logger, # Pass app_logger to TikTokRecorder
            keep_flv=keep_flv,
        ).run()
    except Exception as e:
        app_logger.error(f"{e}")
        return False # Indicate no clean exit


def run_recordings(args, mode, cookies, app_logger) -> bool: # Added return type annotation
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
                    cookies,
                    args.ffmpeg_encode,
                    app_logger,
                    args.keep_flv,
                ),
            )
            p.start()
            processes.append(p)
        try:
            for p in processes:
                p.join()
            return False # No explicit signal to exit the whole program
        except KeyboardInterrupt:
            app_logger.info("\n[!] Ctrl-C detected. Terminating all recording processes.")
            for p in processes:
                if p.is_alive():
                    p.terminate()
            return True # Signal main to exit
    else:
        should_exit = record_user(
            user=args.user,
            url=args.url,
            room_id=args.room_id,
            mode=mode,
            interval=args.automatic_interval,
            proxy=args.proxy,
            output=args.output,
            duration=args.duration,
            use_telegram=args.telegram,
            cookies=cookies,
            ffmpeg_encode=args.ffmpeg_encode,
            app_logger=app_logger,
            keep_flv=args.keep_flv,
        )
        return should_exit


def main():
    from utils.args_handler import validate_and_parse_args
    from utils.utils import read_cookies
    from utils.logger_manager import LoggerManager # Import LoggerManager
    from utils.custom_exceptions import TikTokRecorderError
    from check_updates import check_updates
    from utils.dependencies import check_and_install_dependencies # New import
    from utils.utils import banner # New import

    # print the banner
    banner()

    # check and install dependencies
    check_and_install_dependencies()

    # Initialize logger with default settings (verbose=False) so it's available for early exceptions
    logger_manager_instance = LoggerManager()
    logger_manager_instance.setup_logger(verbose=False)
    app_logger = logger_manager_instance.logger

    try:
        # validate and parse command line arguments
        args, mode = validate_and_parse_args()

        # Re-configure logger if verbose flag is set
        if args.verbose:
             logger_manager_instance.setup_logger(verbose=True)
             app_logger = logger_manager_instance.logger # Refresh reference (though instance is same)

        # Handle repair mode
        if args.repair:
            from utils.video_management import VideoManagement
            app_logger.info(f"Starting manual repair for file: {args.repair}")
            
            if not os.path.exists(args.repair):
                app_logger.error(f"File not found: {args.repair}")
                exit(1)

            # Force re-encode (ffmpeg_encode=True) to fix corruption
            result = VideoManagement.convert_flv_to_mp4(args.repair, ffmpeg_encode=True)
            
            if result:
                app_logger.info(f"Repair successful. Output file: {result}")
            else:
                app_logger.error("Repair failed.")
            
            exit(0)

        # check for updates
        if args.update_check is True:
            app_logger.info("Checking for updates...\n")
            if check_updates():
                exit()
        else:
            app_logger.info("Skipped update check\n")

        # read cookies from the config file
        cookies = read_cookies()

        # run the recordings based on the parsed arguments
        should_exit_program = run_recordings(args, mode, cookies, app_logger) # Pass the logger
        if should_exit_program:
            app_logger.info("Program terminated by user request.")
            exit()

    except TikTokRecorderError as ex:
        app_logger.error(f"Application Error: {ex}")

    except Exception as ex:
        app_logger.critical(f"Generic Error: {ex}", exc_info=True)


if __name__ == "__main__":
    # set up signal handling for graceful shutdown
    multiprocessing.freeze_support()

    # run
    main()
