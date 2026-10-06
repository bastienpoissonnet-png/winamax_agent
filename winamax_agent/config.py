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
                # Strip inline comments if value is not quoted
                value = value.strip()
                if not (value.startswith('"') and value.endswith('"')) and not (value.startswith("'") and value.endswith("'")):
                    value = value.split("#")[0].strip()
                else:
                    value = value.strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value


@dataclass
class AgentConfig:
    """Configuration class for the sports betting decision agent."""

    odds_api_key: str = ""
    football_data_api_key: str = ""
    discord_webhook_url: str = ""
    bookmaker: str = "winamax"
    competitions: List[str] = field(
        default_factory=lambda: [
            "soccer_uefa_nations_league",
            "soccer_france_ligue_one",
            "soccer_epl",
            "soccer_spain_la_liga",
            "soccer_italy_serie_a",
            "soccer_germany_bundesliga",
            "soccer_uefa_champs_league",
            "soccer_uefa_europa_league",
        ]
    )
    markets: List[str] = field(default_factory=lambda: ["h2h", "totals"])
    total_bankroll: float = 500.0
    kelly_fraction: float = 0.50  # 50% Fractional Kelly (Half-Kelly)
    min_stake: float = 1.0        # Plancher strict de 1 €
    max_stake: float = 20.0       # Plafond absolu strict de 20 €
    min_ev_threshold: float = 0.005 # Seuil d'EV minimale (+0.5% d'edge)
    # Plage de cotes Sweet Spot (1.50 - 3.00)
    min_odds: float = 1.50        # Plancher de cote (rejeter < 1.50)
    max_odds: float = 3.00        # Plafond de cote (rejeter > 3.00)
    min_prob_threshold: float = 0.40 # Probabilité minimale pour cotes jusqu'à 3.00
    min_prob_low_odds: float = 0.60  # Probabilité minimale pour cotes < 1.70
    max_realistic_edge: float = 0.07 # Plafond d'edge réaliste (+7% max)
    # Paramètres du générateur de combinés intelligents (2-3 sélections)
    parlay_min_prob: float = 0.60    # Seuil de probabilité unitaire (P >= 60%)
    parlay_min_odds: float = 1.80    # Cote combinée minimale
    parlay_max_odds: float = 4.00    # Cote combinée maximale
    parlay_max_stake: float = 15.0   # Plafond Kelly combiné (15.0 € max)
    parlay_kelly_fraction: float = 0.35 # Kelly fractionnaire pour combinés
    # Paramètres de la « Cote Osée » (Fun Bet à forte cote)
    longshot_min_odds: float = 4.00   # Seuil de cote osée (>= 4.00)
    longshot_max_odds: float = 15.00  # Plafond de cote pour éviter l'absurde
    longshot_max_stake: float = 5.00  # Plafond strict pour fun bet (5.00 € max)
    longshot_min_stake: float = 1.00  # Plancher de 1.00 €
    longshot_kelly_fraction: float = 0.15 # Micro-Kelly (15%) pour absorber la variance
    fallback_stake: float = 1.00      # Mise de secours bridée (1.00 € max recommandé)
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
                "soccer_uefa_nations_league",
                "soccer_france_ligue_one",
                "soccer_epl",
                "soccer_spain_la_liga",
                "soccer_italy_serie_a",
                "soccer_germany_bundesliga",
                "soccer_uefa_champs_league",
                "soccer_uefa_europa_league",
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
            football_data_api_key=os.getenv("FOOTBALL_DATA_API_KEY", "").strip(),
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", "").strip(),
            bookmaker=os.getenv("BOOKMAKER", "winamax").strip().lower(),
            competitions=competitions,
            markets=markets,
            total_bankroll=float(os.getenv("TOTAL_BANKROLL", "500.0")),
            kelly_fraction=float(os.getenv("KELLY_FRACTION", "0.50")),
            min_stake=float(os.getenv("MIN_STAKE", "1.0")),
            max_stake=float(os.getenv("MAX_STAKE", "20.0")),
            min_ev_threshold=float(os.getenv("MIN_EV_THRESHOLD", "0.005")),
            min_odds=float(os.getenv("MIN_ODDS", "1.50")),
            max_odds=float(os.getenv("MAX_ODDS", "3.00")),
            min_prob_threshold=float(os.getenv("MIN_PROB_THRESHOLD", "0.40")),
            min_prob_low_odds=float(os.getenv("MIN_PROB_LOW_ODDS", "0.60")),
            max_realistic_edge=float(os.getenv("MAX_REALISTIC_EDGE", "0.07")),
            parlay_min_prob=float(os.getenv("PARLAY_MIN_PROB", "0.60")),
            parlay_min_odds=float(os.getenv("PARLAY_MIN_ODDS", "1.80")),
            parlay_max_odds=float(os.getenv("PARLAY_MAX_ODDS", "4.00")),
            parlay_max_stake=float(os.getenv("PARLAY_MAX_STAKE", "15.0")),
            parlay_kelly_fraction=float(os.getenv("PARLAY_KELLY_FRACTION", "0.35")),
            longshot_min_odds=float(os.getenv("LONGSHOT_MIN_ODDS", "4.00")),
            longshot_max_odds=float(os.getenv("LONGSHOT_MAX_ODDS", "15.00")),
            longshot_max_stake=float(os.getenv("LONGSHOT_MAX_STAKE", "5.00")),
            longshot_min_stake=float(os.getenv("LONGSHOT_MIN_STAKE", "1.00")),
            longshot_kelly_fraction=float(os.getenv("LONGSHOT_KELLY_FRACTION", "0.15")),
            fallback_stake=float(os.getenv("FALLBACK_STAKE", "1.00")),
            schedule_interval_hours=int(os.getenv("SCHEDULE_INTERVAL_HOURS", "6")),
            simulation_mode=simulation_mode,
            output_dir=Path(os.getenv("OUTPUT_DIR", "reports")),
        )

