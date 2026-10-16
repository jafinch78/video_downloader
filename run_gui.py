"""Entry point shared by the windowed EXE and its isolated worker."""
import sys

if __name__ == '__main__':
    if '--worker' in sys.argv[1:]:
        from video_downloader.worker import main
        sys.exit(main(sys.argv[2:]))
    else:
        from video_downloader.gui import main
        main()
