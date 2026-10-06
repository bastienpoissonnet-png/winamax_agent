"""Scheduler runner for recurring execution of the Winamax betting agent."""

from __future__ import annotations
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional
from winamax_agent.agent import WinamaxBettingAgent
from winamax_agent.config import AgentConfig
from winamax_agent.reporting.exporters import export_to_json, export_to_markdown

logger = logging.getLogger(__name__)


class AgentScheduler:
    """Handles scheduled periodic execution of the quantitative agent."""

    def __init__(self, agent: WinamaxBettingAgent, interval_hours: int = 6):
        self.agent = agent
        self.interval_seconds = interval_hours * 3600
        self._running = False

    def run_cycle(self) -> None:
        """Executes a single evaluation cycle and saves artifacts."""
        logger.info(f"--- Starting analysis cycle at {datetime.now().isoformat()} ---")
        try:
            report = self.agent.run_daily_analysis()

            # Render to console
            print(report.render_console())

            # Export reports to files
            today_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            md_path = self.agent.config.output_dir / f"report_{today_str}.md"
            json_path = self.agent.config.output_dir / f"report_{today_str}.json"
            latest_md = self.agent.config.output_dir / "latest_report.md"
            latest_json = self.agent.config.output_dir / "latest_report.json"

            export_to_markdown(report, md_path)
            export_to_markdown(report, latest_md)
            export_to_json(report, json_path)
            export_to_json(report, latest_json)

            logger.info(f"Reports saved to {md_path} and {latest_md}")
        except Exception as e:
            logger.error(f"Error during analysis cycle: {e}", exc_info=True)

    def start_loop(self) -> None:
        """Starts infinite loop sleeping between intervals."""
        self._running = True

        def _signal_handler(sig, frame):
            logger.info("Termination signal received. Stopping scheduler...")
            self._running = False
            sys.exit(0)

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        logger.info(
            f"Scheduler started. Running every {self.interval_seconds / 3600:.1f} hours. "
            f"Press Ctrl+C to stop."
        )

        while self._running:
            self.run_cycle()
            logger.info(
                f"Cycle completed. Next analysis scheduled in "
                f"{self.interval_seconds / 3600:.1f} hours."
            )
            # Sleep in chunks to remain responsive to SIGINT
            sleep_remaining = self.interval_seconds
            while self._running and sleep_remaining > 0:
                chunk = min(5, sleep_remaining)
                time.sleep(chunk)
                sleep_remaining -= chunk
