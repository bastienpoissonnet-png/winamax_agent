"""Discord Webhook notification module for broadcasting daily betting decision reports."""

from __future__ import annotations
import os
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional
from winamax_agent.reporting.reporter import BetRecommendation, DailyReport

logger = logging.getLogger(__name__)

DISCORD_COLOR_GREEN = 0x2ECC71   # 3066993 - Sélection validée (EV > 0)
DISCORD_COLOR_YELLOW = 0xF1C40F  # 15844351 - Option de secours / défensive
DISCORD_COLOR_GRAY = 0x95A5A6    # 9807270 - Aucun pari jouable / inactif


def generate_github_issue_url(
    match: str,
    selection: str,
    stake: float,
    odds: float,
    repo_owner: str = "bastienpoissonnet-png",
    repo_name: str = "winamax_agent",
) -> str:
    """Generates a pre-filled GitHub issue creation link for bet tracking."""
    env_repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    if env_repo and "/" in env_repo:
        repo_owner, repo_name = env_repo.split("/", 1)

    title_part = f"[PARI]+{match}+{selection}".replace(" ", "+")
    body_part = f"Mise:+{stake:.2f}€+|+Cote:+{odds:.2f}".replace(" ", "+")
    return f"https://github.com/{repo_owner}/{repo_name}/issues/new?title={title_part}&body={body_part}"


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


def _format_single_table(selection: str, odds: float, ev_pct: float, prob_pct: float) -> str:
    """Formats aligned monospace text table for single bet / match of the day / longshot."""
    header = f"{'SELECTION':<26}{'COTE':<9}{'EV':<8}{'PROB':<6}".rstrip()
    sel_sub = (selection[:23] + "…") if len(selection) > 25 else selection
    odds_str = f"{odds:.2f}"
    ev_str = f"{ev_pct:+.1f}%"
    prob_str = f"{prob_pct:.1f}%"
    row = f"{sel_sub:<26}{odds_str:<9}{ev_str:<8}{prob_str:<6}".rstrip()
    return f"```\n{header}\n{row}\n```"


def _format_parlay_table(legs: list, total_odds: float, ev_pct: float, is_fallback: bool, prob_pct: float) -> str:
    """Formats aligned monospace text table for parlay legs and summary."""
    header = f"{'MATCH':<26}{'PARI':<9}{'COTE':<6}".rstrip()
    lines = [header]
    for leg in legs:
        match_sub = (leg.match_title[:23] + "…") if len(leg.match_title) > 25 else leg.match_title
        pari_sub = format_compact_selection(leg.selection)[:8]
        cote_str = f"{leg.odds:.2f}"
        lines.append(f"{match_sub:<26}{pari_sub:<9}{cote_str:<6}".rstrip())

    if is_fallback:
        summary = f"COTE TOTALE : {total_odds:.2f} | PROB : {prob_pct:.1f}%"
    else:
        summary = f"COTE TOTALE : {total_odds:.2f} | EV : {ev_pct:+.1f}%"
    lines.append(summary)
    return "```\n" + "\n".join(lines) + "\n```"


def _format_secondary_table(recommendations: list) -> str:
    """Formats aligned monospace text table for secondary opportunities."""
    header = f"{'MATCH':<24}{'PARI':<9}{'COTE':<7}{'EV':<6}".rstrip()
    lines = [header]
    for r in recommendations:
        match_sub = (r.match_title[:21] + "…") if len(r.match_title) > 23 else r.match_title
        pari_sub = format_compact_selection(r.selection_label)[:8]
        cote_str = f"{r.winamax_odds:.2f}"
        ev_str = f"{r.ev_pct:+.1f}%"
        lines.append(f"{match_sub:<24}{pari_sub:<9}{cote_str:<7}{ev_str:<6}".rstrip())
    return "```\n" + "\n".join(lines) + "\n```"


def format_discord_embed(report: DailyReport) -> Dict[str, Any]:
    """Formats a multi-embed Discord payload representing the daily betting sections as distinct cards."""
    date_display = report.timestamp.split()[0] if " " in report.timestamp else report.timestamp

    # Check fallback status across all sections
    has_fallback = any([
        report.match_of_the_day and report.match_of_the_day.is_fallback,
        report.top_recommendation and report.top_recommendation.is_fallback,
        report.top_parlay and report.top_parlay.is_fallback,
        report.longshot_recommendation and report.longshot_recommendation.is_fallback,
    ])

    embeds: List[Dict[str, Any]] = []

    # -----------------------------------------------------------------
    # Embed 0 : Header compact
    # -----------------------------------------------------------------
    header_color = DISCORD_COLOR_YELLOW if has_fallback else (
        DISCORD_COLOR_GREEN if (report.top_recommendation or report.match_of_the_day) else DISCORD_COLOR_GRAY
    )
    bankroll_val = report.current_bankroll
    profit_val = report.total_profit
    if bankroll_val is None or profit_val is None:
        try:
            from winamax_agent.bankroll import load_or_init_bankroll
            b_data = load_or_init_bankroll()
            bankroll_val = float(b_data.get("current_bankroll", 50.0))
            profit_val = float(b_data.get("total_profit", 0.0))
        except Exception:
            bankroll_val = 50.0
            profit_val = 0.0

    embed_header = {
        "title": f"🎯 Winamax Value Agent — Rapport du {date_display}",
        "description": (
            f"📊 **Marchés scannés :** {report.total_markets_analyzed} sur {report.total_matches_analyzed} rencontres\n"
            f"✨ **Opportunités EV > 0 :** {report.positive_ev_count}\n"
            f"💼 **Solde :** {bankroll_val:.2f} € ({profit_val:+.2f} €)\n"
            f"📌 **Statut global :** {'🟡 *Attention : Présence d’options de secours*' if has_fallback else '🟢 *Toutes les opportunités sont validées (EV > 0)*'}"
        ),
        "color": header_color,
    }
    embeds.append(embed_header)

    # -----------------------------------------------------------------
    # Embed 1 : Match du Jour
    # -----------------------------------------------------------------
    if not report.match_of_the_day:
        embeds.append({
            "title": "MATCH DU JOUR [AUCUN PARI JOUABLE]",
            "description": "Aucun pari jouable aujourd'hui (cotes < 1.05 ou calendrier vide)\n💰 **Mise : 0.00 €**",
            "color": DISCORD_COLOR_GRAY,
        })
    else:
        m = report.match_of_the_day
        status_tag = "[SECOURS]" if m.is_fallback else "[VALIDÉ]"
        card_color = DISCORD_COLOR_YELLOW if m.is_fallback else DISCORD_COLOR_GREEN
        table = _format_single_table(
            selection=m.selection_label,
            odds=m.winamax_odds,
            ev_pct=m.ev_pct,
            prob_pct=m.model_true_prob_pct,
        )
        issue_link = generate_github_issue_url(
            match=m.match_title,
            selection=m.selection_label,
            stake=m.stake_eur,
            odds=m.winamax_odds,
        )
        desc_lines = [
            f"**{m.match_title}**",
            table,
        ]
        if m.is_fallback:
            desc_lines.append(f"💰 **Mise : {m.stake_eur:.2f} €** *(Option de secours)*")
        else:
            desc_lines.append(f"💰 **Mise : {m.stake_eur:.2f} €**")
        desc_lines.append(f"🔗 [Enregistrer ce pari sur GitHub]({issue_link})")
        if m.pitch_dynamic:
            desc_lines.append(f"🏟️ *{m.pitch_dynamic}*")

        embeds.append({
            "title": f"MATCH DU JOUR {status_tag}",
            "description": "\n".join(desc_lines),
            "color": card_color,
        })

    # -----------------------------------------------------------------
    # Embed 2 : Meilleur Pari Simple
    # -----------------------------------------------------------------
    if not report.top_recommendation:
        embeds.append({
            "title": "PARI SIMPLE [AUCUN PARI JOUABLE]",
            "description": "Aucun pari simple éligible cette semaine\n💰 **Mise : 0.00 €**",
            "color": DISCORD_COLOR_GRAY,
        })
    else:
        rec = report.top_recommendation
        status_tag = "[SECOURS]" if rec.is_fallback else "[VALIDÉ]"
        card_color = DISCORD_COLOR_YELLOW if rec.is_fallback else DISCORD_COLOR_GREEN
        table = _format_single_table(
            selection=rec.selection_label,
            odds=rec.winamax_odds,
            ev_pct=rec.ev_pct,
            prob_pct=rec.model_true_prob_pct,
        )
        issue_link = generate_github_issue_url(
            match=rec.match_title,
            selection=rec.selection_label,
            stake=rec.stake_eur,
            odds=rec.winamax_odds,
        )
        desc_lines = [
            f"**{rec.match_title}**",
            table,
        ]
        if rec.is_fallback:
            desc_lines.append(f"💰 **Mise : {rec.stake_eur:.2f} €** *(Option de secours)*")
        else:
            desc_lines.append(f"💰 **Mise : {rec.stake_eur:.2f} €**")
        desc_lines.append(f"🔗 [Enregistrer ce pari sur GitHub]({issue_link})")
        if rec.pitch_dynamic:
            desc_lines.append(f"🏟️ *{rec.pitch_dynamic}*")

        embeds.append({
            "title": f"PARI SIMPLE {status_tag}",
            "description": "\n".join(desc_lines),
            "color": card_color,
        })

    # -----------------------------------------------------------------
    # Embed 3 : Meilleur Combiné
    # -----------------------------------------------------------------
    if not report.top_parlay:
        embeds.append({
            "title": "COMBINÉ [AUCUN COMBINÉ]",
            "description": "Nombre insuffisant de sélections pour un combiné\n💰 **Mise : 0.00 €**",
            "color": DISCORD_COLOR_GRAY,
        })
    else:
        p = report.top_parlay
        status_tag = "[SECOURS]" if p.is_fallback else "[VALIDÉ]"
        card_color = DISCORD_COLOR_YELLOW if p.is_fallback else DISCORD_COLOR_GREEN
        table = _format_parlay_table(
            legs=p.legs,
            total_odds=p.total_odds,
            ev_pct=p.combined_ev_pct,
            is_fallback=p.is_fallback,
            prob_pct=p.combined_prob_pct,
        )
        desc_lines = [
            table,
            f"💰 **Mise conseillée : {p.recommended_stake:.2f} €**",
        ]
        if p.cross_justification:
            desc_lines.append(f"🏟️ *{p.cross_justification}*")

        embeds.append({
            "title": f"COMBINÉ {status_tag}",
            "description": "\n".join(desc_lines),
            "color": card_color,
        })

    # -----------------------------------------------------------------
    # Embed 4 : Cote Osée
    # -----------------------------------------------------------------
    if not report.longshot_recommendation:
        embeds.append({
            "title": "COTE OSÉE [AUCUNE COTE]",
            "description": "Aucune cote comprise entre 4.00 et 10.00 disponible\n💰 **Mise : 0.00 €**",
            "color": DISCORD_COLOR_GRAY,
        })
    else:
        ls = report.longshot_recommendation
        status_tag = "[SECOURS]" if ls.is_fallback else "[VALIDÉ]"
        card_color = DISCORD_COLOR_YELLOW if ls.is_fallback else DISCORD_COLOR_GREEN
        table = _format_single_table(
            selection=ls.selection_label,
            odds=ls.winamax_odds,
            ev_pct=ls.ev_pct,
            prob_pct=ls.model_true_prob_pct,
        )
        desc_lines = [
            f"**{ls.match_title}**",
            table,
        ]
        if ls.is_fallback:
            desc_lines.append(f"💰 **Mise : {ls.stake_eur:.2f} €** *(Option de secours)*")
        else:
            desc_lines.append(f"💰 **Mise : {ls.stake_eur:.2f} €**")
        if ls.pitch_dynamic:
            desc_lines.append(f"🏟️ *{ls.pitch_dynamic}*")

        embeds.append({
            "title": f"COTE OSÉE {status_tag}",
            "description": "\n".join(desc_lines),
            "color": card_color,
        })

    # -----------------------------------------------------------------
    # Embed 5 : Autres opportunités (EV > 0)
    # -----------------------------------------------------------------
    valid_secondary = [
        r for r in report.secondary_recommendations
        if not r.is_fallback and r.ev_pct > 0
    ]
    if valid_secondary:
        table = _format_secondary_table(valid_secondary[:7])
        embeds.append({
            "title": "AUTRES OPPORTUNITÉS (EV > 0)",
            "description": f"{table}\n*Sélections secondaires calculées avec espérance mathématique positive.*",
            "color": DISCORD_COLOR_GREEN,
        })

    # Footer sur la dernière carte
    if embeds:
        embeds[-1]["footer"] = {
            "text": "Winamax Value Betting Agent • Staking Kelly Fractionnaire • Jouer comporte des risques"
        }
        embeds[-1]["timestamp"] = datetime.utcnow().isoformat() + "Z"

    payload = {
        "username": "Winamax Value Agent",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/fr/thumb/f/f8/Logo_Winamax.svg/1200px-Logo_Winamax.svg.png",
        "embeds": embeds,
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
