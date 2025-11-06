#!/usr/bin/env python3
"""
Scheduler for Meraki to Snipe-IT sync using APScheduler.

This module runs the sync job on a scheduled interval. It's more reliable than Docker cron
and provides better logging and error handling.

Usage:
    python scheduler.py                    # Run with default 1-hour interval
    python scheduler.py --interval 30      # Run every 30 minutes
    python scheduler.py --help             # Show help message

Can also be run via:
    - Docker: docker run -it --env-file .env merakitosnipeit:latest python scheduler.py
    - Systemd timer
    - Kubernetes CronJob
"""

import logging
import argparse
import sys
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from main import SyncStatistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_sync_job():
    """Executes the main sync job."""
    logger.info("=" * 70)
    logger.info("SCHEDULED SYNC JOB STARTED")
    logger.info("=" * 70)
    try:
        import main
        # Run the main sync logic by importing and executing it
        # This reuses all the sync code from main.py
        exec(open('main.py').read())
    except Exception as e:
        logger.error(f"Sync job failed: {str(e)}", exc_info=True)
    logger.info("=" * 70)
    logger.info("SCHEDULED SYNC JOB COMPLETED")
    logger.info("=" * 70)


def create_scheduler(interval_minutes=60, cron_expression=None):
    """
    Creates and configures an APScheduler instance.

    Args:
        interval_minutes (int): How often to run the job in minutes (default 60).
        cron_expression (str): Optional cron expression for more complex schedules.
                              Example: "0 * * * *" for every hour
                              Example: "0 0,12 * * *" for noon and midnight

    Returns:
        BackgroundScheduler: Configured scheduler instance.
    """
    scheduler = BackgroundScheduler()

    if cron_expression:
        # Use cron schedule
        logger.info(f"Scheduling sync with cron expression: {cron_expression}")
        scheduler.add_job(
            run_sync_job,
            CronTrigger.from_crontab(cron_expression),
            id='meraki_snipeit_sync',
            name='Meraki to Snipe-IT Sync (Cron)',
            replace_existing=True
        )
    else:
        # Use interval schedule
        logger.info(f"Scheduling sync every {interval_minutes} minutes")
        scheduler.add_job(
            run_sync_job,
            IntervalTrigger(minutes=interval_minutes),
            id='meraki_snipeit_sync',
            name='Meraki to Snipe-IT Sync (Interval)',
            replace_existing=True
        )

    # Add a listener to log scheduler events
    def job_listener(event):
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.debug(f"Job {event.job_id} completed successfully")

    scheduler.add_listener(job_listener)
    return scheduler


def main():
    """Main entry point for the scheduler."""
    parser = argparse.ArgumentParser(
        description="Scheduler for Meraki to Snipe-IT sync using APScheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scheduler.py                    # Run every hour (default)
  python scheduler.py --interval 30      # Run every 30 minutes
  python scheduler.py --cron "0 * * * *" # Run every hour (cron expression)
  python scheduler.py --cron "0 0,12 * * *" # Run at noon and midnight
        """
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Interval in minutes between sync runs (default: 60)'
    )

    parser.add_argument(
        '--cron',
        type=str,
        help='Cron expression for schedule (e.g., "0 * * * *" for hourly)'
    )

    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run the sync job once and exit (useful for testing)'
    )

    args = parser.parse_args()

    logger.info("Starting Meraki to Snipe-IT Scheduler")
    logger.info(f"Python version: {sys.version}")

    if args.run_once:
        logger.info("Running sync job once and exiting...")
        run_sync_job()
        return 0

    # Create and start the scheduler
    scheduler = create_scheduler(
        interval_minutes=args.interval,
        cron_expression=args.cron
    )

    try:
        scheduler.start()
        logger.info("Scheduler started. Press Ctrl+C to exit.")

        # Keep the scheduler running
        while True:
            pass

    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler stopped.")
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
