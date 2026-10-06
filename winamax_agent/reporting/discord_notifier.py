"""Discord Webhook notification module for broadcasting daily betting decision reports."""

from __future__ import annotations
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, Optional
from winamax_agent.reporting.reporter import DailyReport

logger = logging.getLogger(__name__)

DISCORD_COLOR_GREEN = 0x2ECC71  # 3066993 - All selections validated EV > 0
DISCORD_COLOR_YELLOW = 0xF1C40F # 15844351 - Contains fallback / defensive recommendations


def format_compact_selection(label: str) -> str:
    """Formats verbose selection label into compact shorthand (e.g. 1X, X2, 1, N, 2, Over 2.5)."""
    # Double Chance
    if "(1X)" in label or "1X" in label:
        return "1X"
    if "(X2)" in label or "X2" in label:
        return "X2"
    if "(12)" in label or "12" in label:
        return "12"
    # 1X2
    if "(1)" in label:
        return "1"
    if "(2)" in label:
        return "2"
    if "(N)" in label or "Match Nul" in label:
        return "N"
    # Totals
    if "Over 1.5" in label or "Plus de 1.5" in label:
        return "+1.5 buts"
    if "Under 1.5" in label or "Moins de 1.5" in label:
        return "-1.5 buts"
    if "Over 2.5" in label or "Plus de 2.5" in label:
        return "+2.5 buts"
    if "Under 2.5" in label or "Moins de 2.5" in label:
        return "-2.5 buts"
    if "Over 3.5" in label or "Plus de 3.5" in label:
        return "+3.5 buts"
    if "Under 3.5" in label or "Moins de 3.5" in label:
        return "-3.5 buts"
    return label


def format_discord_embed(report: DailyReport) -> Dict[str, Any]:
    """Formats a rich Discord Embed representing the daily betting sections."""
    date_display = report.timestamp.split()[0] if " " in report.timestamp else report.timestamp

    # Determine embed color: yellow if any section is in fallback mode, green if all validated
    has_fallback = any([
        report.match_of_the_day and report.match_of_the_day.is_fallback,
        report.top_recommendation and report.top_recommendation.is_fallback,
        report.top_parlay and report.top_parlay.is_fallback,
        report.longshot_recommendation and report.longshot_recommendation.is_fallback,
    ])
    embed_color = DISCORD_COLOR_YELLOW if has_fallback else DISCORD_COLOR_GREEN

    fields = []

    # -----------------------------------------------------------------
    # Field 1 : Le Match du Jour
    # -----------------------------------------------------------------
    if not report.match_of_the_day:
        fields.append({
            "name": "MATCH DU JOUR [AUCUN PARI JOUABLE]",
            "value": "Aucun pari jouable aujourd'hui (cotes < 1.05 ou calendrier vide)\n• Mise : 0.00 €",
            "inline": False,
        })
    else:
        m = report.match_of_the_day
        status_tag = "[SECOURS]" if m.is_fallback else "[VALIDÉ]"
        lines = [
            f"{m.match_title}",
            f"• Pari : {m.selection_label} @ {m.winamax_odds:.2f}",
        ]
        if m.is_fallback:
            lines.append(f"• Mise : {m.stake_eur:.2f} € (Option de secours)")
        else:
            lines.append(f"• Mise : {m.stake_eur:.2f} € | EV : {m.ev_pct:+.1f}%")
        fields.append({
            "name": f"MATCH DU JOUR {status_tag}",
            "value": "\n".join(lines),
            "inline": False,
        })

    # -----------------------------------------------------------------
    # Field 2 : Le Meilleur Pari Simple
    # -----------------------------------------------------------------
    if not report.top_recommendation:
        fields.append({
            "name": "PARI SIMPLE [AUCUN PARI JOUABLE]",
            "value": "Aucun pari simple éligible cette semaine\n• Mise : 0.00 €",
            "inline": False,
        })
    else:
        rec = report.top_recommendation
        status_tag = "[SECOURS]" if rec.is_fallback else "[VALIDÉ]"
        lines = [
            f"{rec.match_title}",
            f"• Pari : {rec.selection_label} @ {rec.winamax_odds:.2f}",
        ]
        if rec.is_fallback:
            lines.append(f"• Mise : {rec.stake_eur:.2f} € (Option de secours)")
        else:
            lines.append(f"• Mise : {rec.stake_eur:.2f} € | EV : {rec.ev_pct:+.1f}%")
        fields.append({
            "name": f"PARI SIMPLE {status_tag}",
            "value": "\n".join(lines),
            "inline": False,
        })

    # -----------------------------------------------------------------
    # Field 3 : Le Meilleur Combiné
    # -----------------------------------------------------------------
    if not report.top_parlay:
        fields.append({
            "name": "COMBINÉ [AUCUN COMBINÉ]",
            "value": "Nombre insuffisant de sélections pour un combiné\n• Mise : 0.00 €",
            "inline": False,
        })
    else:
        p = report.top_parlay
        status_tag = "[SECOURS]" if p.is_fallback else "[VALIDÉ]"
        lines = [
            f"Cote totale : {p.total_odds:.2f} | Prob : {p.combined_prob_pct:.1f}%",
        ]
        for leg in p.legs:
            lines.append(f"• {leg.selection} @ {leg.odds:.2f}")
        if p.is_fallback:
            lines.append(f"• Mise : {p.recommended_stake:.2f} €")
        else:
            lines.append(f"• Mise : {p.recommended_stake:.2f} € | EV : {p.combined_ev_pct:+.1f}%")
        fields.append({
            "name": f"COMBINÉ {status_tag}",
            "value": "\n".join(lines),
            "inline": False,
        })

    # -----------------------------------------------------------------
    # Field 4 : La Cote Osée
    # -----------------------------------------------------------------
    if not report.longshot_recommendation:
        fields.append({
            "name": "COTE OSÉE [AUCUNE COTE]",
            "value": "Aucune cote comprise entre 4.00 et 10.00 disponible\n• Mise : 0.00 €",
            "inline": False,
        })
    else:
        ls = report.longshot_recommendation
        status_tag = "[SECOURS]" if ls.is_fallback else "[VALIDÉ]"
        lines = [
            f"{ls.match_title}",
            f"• Pari : {ls.selection_label} @ {ls.winamax_odds:.2f}",
        ]
        if ls.is_fallback:
            lines.append(f"• Mise : {ls.stake_eur:.2f} € (Option de secours)")
        else:
            lines.append(f"• Mise : {ls.stake_eur:.2f} € | EV : {ls.ev_pct:+.1f}%")
        fields.append({
            "name": f"COTE OSÉE {status_tag}",
            "value": "\n".join(lines),
            "inline": False,
        })

    # -----------------------------------------------------------------
    # Field 5 : Autres Opportunités Détectées (EV > 0)
    # -----------------------------------------------------------------
    valid_secondary = [
        r for r in report.secondary_recommendations
        if not r.is_fallback and r.ev_pct > 0
    ]
    if valid_secondary:
        sec_lines = []
        for sec in valid_secondary:
            short_sel = format_compact_selection(sec.selection_label)
            sec_lines.append(
                f"• {sec.match_title} : {short_sel} @ {sec.winamax_odds:.2f} ({sec.ev_pct:+.1f}% EV)"
            )
        fields.append({
            "name": "AUTRES OPPORTUNITÉS (EV > 0)",
            "value": "\n".join(sec_lines),
            "inline": False,
        })

    embed = {
        "title": f"🎯 Winamax Value Agent — Rapport du {date_display}",
        "description": (
            f"📊 **Marchés scannés :** {report.total_markets_analyzed} sur {report.total_matches_analyzed} rencontres\n"
            f"✨ **Opportunités EV > 0 :** {report.positive_ev_count}\n"
            f"📌 **Statut global :** {'🟡 *Attention : Présence d’options de secours*' if has_fallback else '🟢 *Toutes les opportunités sont validées (EV > 0)*'}"
        ),
        "color": embed_color,
        "fields": fields,
        "footer": {
            "text": "Winamax Value Betting Agent • Staking Kelly Fractionnaire • Jouer comporte des risques"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    payload = {
        "username": "Winamax Value Agent",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/fr/thumb/f/f8/Logo_Winamax.svg/1200px-Logo_Winamax.svg.png",
        "embeds": [embed],
    }

    return payload


def send_discord_report(
    report: DailyReport,
    webhook_url: Optional[str] = None,
    timeout: int = 10,
) -> bool:
    """Dispatches formatted DailyReport to a Discord Webhook.

    Returns:
        bool: True if delivered successfully, False otherwise (silent fallback if webhook_url missing).
    """
    if not webhook_url or not webhook_url.strip() or "votre_" in webhook_url:
        logger.debug("Discord webhook URL is not configured or empty. Notification skipped.")
        return False

    url = webhook_url.strip()
    payload = format_discord_embed(report)
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    try:
        # Prefer requests if available, fallback to urllib.request
        try:
            import requests
            resp = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json", "User-Agent": "WinamaxBettingAgent/2.0"},
                timeout=timeout,
            )
            if resp.status_code in (200, 204):
                logger.info("Rapport d'aide à la décision transmis avec succès sur Discord.")
                return True
            else:
                logger.warning(
                    f"Échec d'envoi Discord (HTTP {resp.status_code}): {resp.text[:200]}"
                )
                return False
        except ImportError:
            # Zero-dependency standard library fallback
            req = urllib.request.Request(
                url,
                data=payload_bytes,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "User-Agent": "WinamaxBettingAgent/2.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status in (200, 204):
                    logger.info("Rapport d'aide à la décision transmis avec succès sur Discord (via urllib).")
                    return True
                else:
                    logger.warning(f"Réponse inattendue de Discord: HTTP {response.status}")
                    return False

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        logger.warning(f"Erreur HTTP lors de l'envoi Discord ({e.code}): {error_body[:200]}")
        return False
    except Exception as e:
        logger.warning(f"Impossible d'envoyer la notification Discord: {e}")
        return False

