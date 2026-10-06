"""Bankroll tracker and bet record management for Winamax Betting Agent."""

from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_BANKROLL_PATH = Path("reports/bankroll.json")
DEFAULT_INITIAL_BANKROLL = 50.0


def load_or_init_bankroll(
    filepath: Path | str = DEFAULT_BANKROLL_PATH,
    default_initial: float = DEFAULT_INITIAL_BANKROLL,
) -> Dict[str, Any]:
    """Loads existing bankroll data from JSON file or initializes default structure if missing."""
    path = Path(filepath)
    if not path.exists():
        initial_data = {
            "initial_bankroll": float(default_initial),
            "current_bankroll": float(default_initial),
            "total_profit": 0.0,
            "history": [],
        }
        save_bankroll(initial_data, path)
        logger.info(f"Initialized new bankroll file at {path} with {default_initial:.2f} €.")
        return initial_data

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Ensure mandatory keys exist
        data.setdefault("initial_bankroll", float(default_initial))
        data.setdefault("current_bankroll", data["initial_bankroll"])
        data.setdefault("total_profit", round(data["current_bankroll"] - data["initial_bankroll"], 2))
        data.setdefault("history", [])
        return data
    except Exception as e:
        logger.warning(f"Error reading bankroll file {path}: {e}. Returning default structure.")
        return {
            "initial_bankroll": float(default_initial),
            "current_bankroll": float(default_initial),
            "total_profit": 0.0,
            "history": [],
        }


def save_bankroll(data: Dict[str, Any], filepath: Path | str = DEFAULT_BANKROLL_PATH) -> None:
    """Persists bankroll tracking data to JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def record_bet(
    selection: str,
    stake: float,
    odds: float,
    status: str = "pending",
    filepath: Path | str = DEFAULT_BANKROLL_PATH,
) -> Dict[str, Any]:
    """Records a bet and updates bankroll balance, net profit and history.

    Supported statuses:
        - "pending": bet currently in play (balance unchanged, net_profit = 0.0)
        - "win": winning bet (net_profit = stake * (odds - 1.0), balance increases)
        - "loss": lost bet (net_profit = -stake, balance decreases)
    """
    normalized_status = status.strip().lower()
    if normalized_status not in ("pending", "win", "loss"):
        raise ValueError(
            f"Statut de pari invalide: '{status}'. Les statuts supportés sont: 'pending', 'win', 'loss'."
        )

    if stake <= 0:
        raise ValueError(f"La mise doit être positive (reçu: {stake} €).")
    if odds < 1.0:
        raise ValueError(f"La cote doit être >= 1.0 (reçu: {odds}).")

    data = load_or_init_bankroll(filepath=filepath)
    initial_bankroll = float(data.get("initial_bankroll", DEFAULT_INITIAL_BANKROLL))
    current_bankroll = float(data.get("current_bankroll", initial_bankroll))
    history: List[Dict[str, Any]] = data.get("history", [])

    if normalized_status == "win":
        net_profit = round(float(stake) * (float(odds) - 1.0), 2)
        current_bankroll = round(current_bankroll + net_profit, 2)
    elif normalized_status == "loss":
        net_profit = round(-float(stake), 2)
        current_bankroll = round(current_bankroll + net_profit, 2)
    else:  # pending
        net_profit = 0.0

    total_profit = round(current_bankroll - initial_bankroll, 2)

    entry = {
        "id": len(history) + 1,
        "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "selection": selection.strip(),
        "stake": round(float(stake), 2),
        "odds": round(float(odds), 2),
        "status": normalized_status,
        "net_profit": net_profit,
        "balance_after": current_bankroll,
    }
    history.append(entry)

    data["current_bankroll"] = current_bankroll
    data["total_profit"] = total_profit
    data["history"] = history

    save_bankroll(data, filepath=filepath)
    logger.info(
        f"Pari enregistré: '{selection}' @ {odds:.2f} ({normalized_status}). "
        f"Nouveau solde: {current_bankroll:.2f} € (Profit: {total_profit:+.2f} €)"
    )
    return data
