"""Configuration management for Winamax Betting Agent."""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


def _load_env_file(filepath: Path | str = ".env") -> None:
    """Lightweight .env parser that sets os.environ without external dependencies."""
    path = Path(filepath)
    if not path.exists():
        return

    try:
        # If python-dotenv is installed, prefer it
        import dotenv
        dotenv.load_dotenv(dotenv_path=path)
        return
    except ImportError:
        pass

    # Fallback pure-Python parser
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value


@dataclass
class AgentConfig:
    """Configuration class for the sports betting decision agent."""

    odds_api_key: str = ""
    bookmaker: str = "winamax"
    competitions: List[str] = field(
        default_factory=lambda: [
            "soccer_france_ligue_one",
            "soccer_epl",
            "soccer_uefa_champs_league",
        ]
    )
    markets: List[str] = field(default_factory=lambda: ["h2h", "totals"])
    total_bankroll: float = 500.0
    kelly_fraction: float = 0.50  # 50% Fractional Kelly (Half-Kelly)
    min_stake: float = 1.0        # Plancher strict de 1 €
    max_stake: float = 20.0       # Plafond absolu strict de 20 €
    min_ev_threshold: float = 0.0 # Seuil strict EV > 0
    schedule_interval_hours: int = 6
    simulation_mode: bool = False
    output_dir: Path = field(default_factory=lambda: Path("reports"))

    @classmethod
    def from_env(cls, env_path: str = ".env") -> AgentConfig:
        """Loads configuration from environment variables and .env file."""
        _load_env_file(env_path)

        competitions_raw = os.getenv("COMPETITIONS", "")
        if competitions_raw:
            competitions = [c.strip() for c in competitions_raw.split(",") if c.strip()]
        else:
            competitions = [
                "soccer_france_ligue_one",
                "soccer_epl",
                "soccer_uefa_champs_league",
            ]

        markets_raw = os.getenv("MARKETS", "")
        if markets_raw:
            markets = [m.strip() for m in markets_raw.split(",") if m.strip()]
        else:
            markets = ["h2h", "totals"]

        sim_mode_val = os.getenv("SIMULATION_MODE", "false").lower()
        simulation_mode = sim_mode_val in ("true", "1", "yes", "t")

        api_key = os.getenv("ODDS_API_KEY", "").strip()
        # If API key is empty or placeholder, enable simulation mode gracefully
        if not api_key or api_key == "votre_cle_api_ici":
            simulation_mode = True

        return cls(
            odds_api_key=api_key,
            bookmaker=os.getenv("BOOKMAKER", "winamax").strip().lower(),
            competitions=competitions,
            markets=markets,
            total_bankroll=float(os.getenv("TOTAL_BANKROLL", "500.0")),
            kelly_fraction=float(os.getenv("KELLY_FRACTION", "0.50")),
            min_stake=float(os.getenv("MIN_STAKE", "1.0")),
            max_stake=float(os.getenv("MAX_STAKE", "20.0")),
            min_ev_threshold=float(os.getenv("MIN_EV_THRESHOLD", "0.0")),
            schedule_interval_hours=int(os.getenv("SCHEDULE_INTERVAL_HOURS", "6")),
            simulation_mode=simulation_mode,
            output_dir=Path(os.getenv("OUTPUT_DIR", "reports")),
        )
