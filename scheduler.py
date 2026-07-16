"""Runs hn_scraper.scrape() on a fixed interval, in the foreground.

This makes the "recurring schedule" the README describes real: while this
process is running, it calls scrape() every INTERVAL_MINUTES and logs the
result. It does NOT run when your machine is off or this process isn't
running — for true unattended collection, wire it into your OS's own
scheduler instead (see README "Running unattended").

Usage:
    python scheduler.py                  # every 60 minutes (default)
    python scheduler.py --minutes 30     # every 30 minutes
    python scheduler.py --once           # one run, then exit (for cron/Task Scheduler)
"""
import argparse
import sys
import time
from datetime import datetime

from hn_scraper import scrape


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minutes", type=int, default=60, help="minutes between scrape runs (default: 60)")
    ap.add_argument("--once", action="store_true", help="run once and exit (use this from cron/Task Scheduler)")
    args = ap.parse_args()

    if args.once:
        scrape()
        return

    if args.minutes <= 0:
        print("ERROR: --minutes must be positive", file=sys.stderr)
        sys.exit(1)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduler started — scraping every {args.minutes} min. Ctrl+C to stop.")
    try:
        while True:
            try:
                scrape()
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] scrape() failed: {e}", file=sys.stderr)
            time.sleep(args.minutes * 60)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
