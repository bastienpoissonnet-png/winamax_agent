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


def format_discord_embed(report: DailyReport) -> Dict[str, Any]:
    """Formats a rich Discord Embed representing the 4 daily betting sections."""
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
            "name": "📅 1. LE MATCH DU JOUR [ℹ️ AUCUN MATCH]",
            "value": "Aucune rencontre programmée aujourd'hui dans le calendrier des compétitions suivies.\n💰 **Mise conseillée : 0.00 €** *(Préservation du capital)*",
            "inline": False,
        })
    else:
        m = report.match_of_the_day
        badge_symbol = "🟡 [SECOURS]" if m.is_fallback else "🟢 [VALIDÉ]"
        lines = [
            f"**Match :** {m.match_title} *({m.competition})*",
            f"**Marché :** {m.market_name}",
            f"**Sélection :** **{m.selection_label}**",
            f"**Cote :** `{m.winamax_odds:.2f}` | **EV :** `{m.ev_pct:+.2f}%` | **Modèle :** `{m.model_true_prob_pct:.1f}%`",
            f"💰 **Mise conseillée :** **{m.stake_eur:.2f} €**",
        ]
        if m.is_fallback:
            lines.append(f"⚠️ *Choix de secours sous-optimal (EV: {m.ev_pct:+.2f}%) : mise symbolique minimale.*")
        fields.append({
            "name": f"📅 1. LE MATCH DU JOUR {badge_symbol}",
            "value": "\n".join(lines)[:1020],
            "inline": False,
        })

    # -----------------------------------------------------------------
    # Field 2 : Le Meilleur Pari Simple
    # -----------------------------------------------------------------
    if not report.top_recommendation:
        fields.append({
            "name": "🎯 2. LE MEILLEUR PARI SIMPLE [ℹ️ AUCUN PARI]",
            "value": "Aucun pari simple identifié sur le marché cette semaine.\n💰 **Mise conseillée : 0.00 €** *(Préservation du capital)*",
            "inline": False,
        })
    else:
        rec = report.top_recommendation
        badge_symbol = "🟡 [SECOURS]" if rec.is_fallback else "🟢 [VALIDÉ]"
        lines = [
            f"**Match :** {rec.match_title} *({rec.competition})*",
            f"**Marché :** {rec.market_name}",
            f"**Sélection :** **{rec.selection_label}**",
            f"**Cote :** `{rec.winamax_odds:.2f}` (Sweet Spot) | **EV :** `{rec.ev_pct:+.2f}%` | **Modèle :** `{rec.model_true_prob_pct:.1f}%`",
            f"💰 **Mise conseillée :** **{rec.stake_eur:.2f} €**",
        ]
        if rec.is_fallback:
            lines.append(f"⚠️ *Choix de secours sous-optimal (EV: {rec.ev_pct:+.2f}%) : mise symbolique minimale.*")
        fields.append({
            "name": f"🎯 2. LE MEILLEUR PARI SIMPLE {badge_symbol}",
            "value": "\n".join(lines)[:1020],
            "inline": False,
        })

    # -----------------------------------------------------------------
    # Field 3 : Le Meilleur Combiné
    # -----------------------------------------------------------------
    if not report.top_parlay:
        fields.append({
            "name": "🔗 3. LE MEILLEUR COMBINÉ [ℹ️ AUCUN COMBINÉ]",
            "value": "Nombre insuffisant de rencontres distinctes pour constituer un combiné.\n💰 **Mise combiné conseillée : 0.00 €**",
            "inline": False,
        })
    else:
        p = report.top_parlay
        badge_symbol = "🟡 [SECOURS]" if p.is_fallback else "🟢 [VALIDÉ]"
        legs_desc = []
        for i, leg in enumerate(p.legs, 1):
            short_match = leg.match_title.split(" vs ")[0] if " vs " in leg.match_title else leg.match_title
            legs_desc.append(f"• **{short_match}** : {leg.selection} @ `{leg.odds:.2f}` *(P: {leg.prob_pct:.0f}%)*")

        lines = [
            f"**Structure :** Combiné de **{p.legs_count} sélections indépendantes**",
            f"**Cote Combinée Totale :** `{p.total_odds:.2f}` | **EV :** `{p.combined_ev_pct:+.2f}%` | **Prob. :** `{p.combined_prob_pct:.1f}%`",
            f"💰 **Mise combiné conseillée :** **{p.recommended_stake:.2f} €**",
            "**Détail des jambes :**\n" + "\n".join(legs_desc),
        ]
        if p.is_fallback:
            lines.append(f"⚠️ *Combiné de secours (EV: {p.combined_ev_pct:+.2f}%) : mise symbolique minimale.*")
        fields.append({
            "name": f"🔗 3. LE MEILLEUR COMBINÉ {badge_symbol}",
            "value": "\n".join(lines)[:1020],
            "inline": False,
        })

    # -----------------------------------------------------------------
    # Field 4 : La Cote Osée
    # -----------------------------------------------------------------
    if not report.longshot_recommendation:
        fields.append({
            "name": "💣 4. LA COTE OSÉE [ℹ️ AUCUNE COTE]",
            "value": "Aucune cote osée (>= 4.00) disponible sur les marchés analysés.\n💰 **Mise Fun Bet : 0.00 €**",
            "inline": False,
        })
    else:
        ls = report.longshot_recommendation
        badge_symbol = "🟡 [SECOURS]" if ls.is_fallback else "🟢 [VALIDÉ]"
        lines = [
            f"**Match :** {ls.match_title} *({ls.competition})*",
            f"**Marché :** {ls.market_name}",
            f"**Sélection osée :** **{ls.selection_label}**",
            f"**Cote :** `{ls.winamax_odds:.2f}` (Haute cote) | **EV :** `{ls.ev_pct:+.2f}%` | **Modèle :** `{ls.model_true_prob_pct:.1f}%`",
            f"💰 **Mise Fun Bet conseillée :** **{ls.stake_eur:.2f} €** *(Micro-Kelly)*",
        ]
        if ls.is_fallback:
            lines.append(f"⚠️ *Fun Bet sous l'équilibre (EV: {ls.ev_pct:+.2f}%) : mise de précaution 1.00 €.*")
        fields.append({
            "name": f"💣 4. LA COTE OSÉE {badge_symbol}",
            "value": "\n".join(lines)[:1020],
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

