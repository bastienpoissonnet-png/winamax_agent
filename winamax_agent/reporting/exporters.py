"""Exporters for saving reports into Markdown and JSON files with distinct Simple and Parlay sections."""

from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from winamax_agent.reporting.reporter import DailyReport


def export_to_markdown(report: DailyReport, output_path: Path) -> Path:
    """Exports daily report as a well-formatted Markdown file with Sections A & B."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# 🎯 Rapport d'Aide à la Décision - Paris Sportifs (Winamax)")
    lines.append(f"\n*Généré le : {report.timestamp}*")
    lines.append(
        f"\n**Marchés scannés :** {report.total_markets_analyzed} sur {report.total_matches_analyzed} rencontres "
        f"| **Opportunités à valeur (EV > 0.5%) :** {report.positive_ev_count}"
    )

    # -------------------------------------------------------------
    # SECTION 1 : LE MATCH DU JOUR (COUP D'ENVOI AUJOURD'HUI)
    # -------------------------------------------------------------
    lines.append("\n---\n## 📅 Section 1 : Le Match du Jour (Uniquement aujourd'hui)")

    if not report.match_of_the_day:
        lines.append("\n> [!NOTE]\n> **Aucune rencontre programmée aujourd'hui dans le calendrier des compétitions suivies.**")
        lines.append("> Aucune sélection ne peut être analysée pour la date courante. Report sur les opportunités de la semaine.")
        lines.append("> **Mise recommandée pour aujourd'hui : 0.00 €**")
    else:
        m = report.match_of_the_day
        lines.append(f"\n> **Statut :** {m.status_badge}")
        if m.is_fallback and m.warning_message:
            lines.append(f">\n> {m.warning_message}")

        lines.append(f"\n- **Rencontre :** {m.match_title} ({m.competition})")
        lines.append(f"- **Coup d'envoi :** `{m.kickoff}` **(AUJOURD'HUI)**")
        lines.append(f"- **Marché :** {m.market_name}")
        lines.append(f"- **Sélection retenue :** **{m.selection_label}**")
        lines.append(f"- **Cote Winamax :** `{m.winamax_odds:.2f}`")

        lines.append("\n### 📊 Métriques & Probabilités")
        lines.append("| Indicateur | Valeur |")
        lines.append("| :--- | :--- |")
        lines.append(f"| Probabilité brute Winamax (avec marge) | {m.raw_implied_prob_pct:.1f}% |")
        lines.append(f"| Probabilité fair Winamax (sans marge) | {m.fair_bookmaker_prob_pct:.1f}% |")
        lines.append(f"| **Probabilité réelle estimée (Modèle)** | **{m.model_true_prob_pct:.1f}%** |")
        lines.append(f"| Avantage estimé (Edge) | {m.edge_pct:+.2f}% |")
        lines.append(f"| **Espérance de gain (Expected Value - EV)** | **{m.ev_pct:+.2f}%** |")

        lines.append("\n### 💰 Dimensionnement de la Mise")
        lines.append(f"> **Mise recommandée : {m.stake_eur:.2f} €**")
        lines.append(f">\n> *Détail : {m.stake_details}*")

        lines.append("\n### 🔍 Justification Analytique en 3 Points Clés")
        lines.append(f"1. **Métrique xG réelle :**\n   {m.point_1_xg}")
        lines.append(f"2. **Dynamique tactique et confrontations :**\n   {m.point_2_h2h_tactics}")
        lines.append(f"3. **Forme récente et contexte :**\n   {m.point_3_context_form}")

    # -------------------------------------------------------------
    # SECTION 2 : LE MEILLEUR PARI SIMPLE (SWEET SPOT 1.50 - 3.00)
    # -------------------------------------------------------------
    lines.append("\n---\n## 🎯 Section 2 : Le Meilleur Pari Simple (Sweet Spot 1.50 - 3.00 sur la semaine)")

    if not report.top_recommendation:
        lines.append("\n> [!NOTE]\n> **Aucun pari simple identifié sur le marché cette semaine.**")
        lines.append("> En gestion quantitative de bankroll, il est impératif de préserver son capital.")
        lines.append("> **Mise recommandée simples : 0.00 €**")
    else:
        rec = report.top_recommendation
        lines.append(f"\n> **Statut :** {rec.status_badge}")
        if rec.is_fallback and rec.warning_message:
            lines.append(f">\n> {rec.warning_message}")

        lines.append(f"\n- **Rencontre :** {rec.match_title} ({rec.competition})")
        lines.append(f"- **Coup d'envoi :** `{rec.kickoff}`")
        lines.append(f"- **Marché :** {rec.market_name}")
        lines.append(f"- **Sélection retenue :** **{rec.selection_label}**")
        lines.append(f"- **Cote Winamax :** `{rec.winamax_odds:.2f}` (Sweet Spot [1.50 - 3.00])")

        lines.append("\n### 📊 Métriques & Probabilités")
        lines.append("| Indicateur | Valeur |")
        lines.append("| :--- | :--- |")
        lines.append(f"| Probabilité brute Winamax (avec marge) | {rec.raw_implied_prob_pct:.1f}% |")
        lines.append(f"| Probabilité fair Winamax (sans marge) | {rec.fair_bookmaker_prob_pct:.1f}% |")
        lines.append(f"| **Probabilité réelle estimée (Modèle)** | **{rec.model_true_prob_pct:.1f}%** |")
        lines.append(f"| Avantage estimé (Edge) | {rec.edge_pct:+.2f}% |")
        lines.append(f"| **Espérance de gain (Expected Value - EV)** | **{rec.ev_pct:+.2f}%** |")

        lines.append("\n### 💰 Dimensionnement de la Mise")
        lines.append(f"> **Mise recommandée : {rec.stake_eur:.2f} €**")
        lines.append(f">\n> *Détail : {rec.stake_details}*")

        lines.append("\n### 🔍 Justification Analytique en 3 Points Clés")
        lines.append(f"1. **Métrique xG réelle :**\n   {rec.point_1_xg}")
        lines.append(f"2. **Confrontation directe et dynamique tactique :**\n   {rec.point_2_h2h_tactics}")
        lines.append(f"3. **Forme récente et contexte :**\n   {rec.point_3_context_form}")

    # -------------------------------------------------------------
    # SECTION 3 : LE MEILLEUR COMBINÉ DU JOUR (1.80 - 4.00)
    # -------------------------------------------------------------
    lines.append("\n---\n## 🔗 Section 3 : Le Meilleur Combiné (2 à 3 Sélections - Cote 1.80 à 4.00)")

    if not report.top_parlay:
        lines.append("\n> [!NOTE]\n> **Nombre insuffisant de rencontres distinctes pour constituer un combiné.**")
        lines.append("> **Mise recommandée combiné : 0.00 €**")
    else:
        p = report.top_parlay
        lines.append(f"\n> **Statut :** {p.status_badge}")
        if p.is_fallback and p.warning_message:
            lines.append(f">\n> {p.warning_message}")

        lines.append(f"\n- **Structure :** **Combiné de {p.legs_count} sélections indépendantes**")
        lines.append(f"- **COTE COMBINÉE TOTALE :** `{p.total_odds:.2f}` (Cible [1.80 - 4.00])")
        lines.append(f"- **Probabilité combinée estimée :** `{p.combined_prob_pct:.1f}%`")
        lines.append(f"- **Espérance de gain combinée (EV) :** `{p.combined_ev_pct:+.2f}%`")

        lines.append("\n### 📋 Détail des Sélections Combinées")
        lines.append("| Jambe | Rencontre | Compétition | Marché & Sélection | Cote | Prob. Modèle |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for idx, leg in enumerate(p.legs, 1):
            lines.append(
                f"| {idx} | {leg.match_title} | {leg.competition} | **{leg.selection}** | `{leg.odds:.2f}` | {leg.prob_pct:.1f}% |"
            )

        lines.append("\n### 💰 Gestion de Mise Combiné")
        lines.append(f"> **Mise combiné recommandée : {p.recommended_stake:.2f} €**")
        lines.append(f">\n> *{p.stake_details}*")

        lines.append("\n### 🔍 Justification Croisée & Indépendance Statistique")
        lines.append(f"> {p.cross_justification}")

    # -------------------------------------------------------------
    # SECTION 4 : LA « COTE OSÉE » (FUN BET COTE >= 4.00)
    # -------------------------------------------------------------
    lines.append("\n---\n## 💣 Section 4 : La « Cote Osée » (Fun Bet - Cote >= 4.00)")

    if not report.longshot_recommendation:
        lines.append("\n> [!NOTE]\n> **Aucune cote osée (>= 4.00) disponible sur les marchés analysés.**")
        lines.append("> **Mise recommandée Fun Bet : 0.00 €**")
    else:
        ls = report.longshot_recommendation
        lines.append(f"\n> **Statut :** {ls.status_badge}")
        if ls.is_fallback and ls.warning_message:
            lines.append(f">\n> {ls.warning_message}")

        lines.append(f"\n- **Rencontre :** {ls.match_title} ({ls.competition})")
        lines.append(f"- **Coup d'envoi :** `{ls.kickoff}`")
        lines.append(f"- **Marché :** {ls.market_name}")
        lines.append(f"- **Sélection osée :** **{ls.selection_label}**")
        lines.append(f"- **COTE OSÉE :** `{ls.winamax_odds:.2f}` (Plafond de risque maîtrisé)")

        lines.append("\n### 📊 Analyse de l'Edge Spéculatif")
        lines.append("| Indicateur | Valeur |")
        lines.append("| :--- | :--- |")
        lines.append(f"| Probabilité sans marge bookmaker | {ls.fair_bookmaker_prob_pct:.1f}% |")
        lines.append(f"| **Probabilité estimée (Modèle)** | **{ls.model_true_prob_pct:.1f}%** |")
        lines.append(f"| Avantage estimé (Edge) | {ls.edge_pct:+.2f}% |")
        lines.append(f"| **Espérance mathématique (EV)** | **{ls.ev_pct:+.2f}%** |")

        lines.append("\n### 💰 Gestion de Mise (Micro-Kelly / Secours)")
        lines.append(f"> **Mise Fun Bet recommandée : {ls.stake_eur:.2f} €** (Plafond strict 5.00 €)")
        lines.append(f">\n> *{ls.stake_details}*")

        lines.append("\n### 🔍 Justification du Fun Bet")
        lines.append(f"1. **Métrique xG :** {ls.point_1_xg}")
        lines.append(f"2. **Schéma tactique :** {ls.point_2_h2h_tactics}")
        lines.append(f"3. **Contexte d'équipe :** {ls.point_3_context_form}")

    # -------------------------------------------------------------
    # OPPORTUNITÉS SECONDAIRES
    # -------------------------------------------------------------
    if report.secondary_recommendations or report.secondary_parlays:
        lines.append("\n---\n## 📋 Opportunités Secondaires Valables (EV > 0)")
        if report.secondary_recommendations:
            lines.append("\n### Paris Simples Alternatifs")
            lines.append("| Match | Sélection | Cote | EV | Prob. Modèle | Mise Suggérée |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for sec in report.secondary_recommendations:
                lines.append(
                    f"| {sec.match_title} | {sec.selection_label} | `{sec.winamax_odds:.2f}` | "
                    f"`{sec.ev_pct:+.1f}%` | {sec.model_true_prob_pct:.1f}% | **{sec.stake_eur:.2f} €** |"
                )

        if report.secondary_parlays:
            lines.append("\n### Combinés Alternatifs")
            lines.append("| Sélections | Cote Totale | EV Combinée | Prob. Cumulée | Mise Suggérée |")
            lines.append("| :--- | :--- | :--- | :--- | :--- |")
            for sp in report.secondary_parlays[:2]:
                combo_desc = " + ".join(f"{l.match_title.split(' vs ')[0]} ({l.selection.split(' (')[0]})" for l in sp.legs)
                lines.append(
                    f"| {combo_desc} | `{sp.total_odds:.2f}` | `{sp.combined_ev_pct:+.1f}%` | {sp.combined_prob_pct:.1f}% | **{sp.recommended_stake:.2f} €** |"
                )

    lines.append("\n---\n*Avertissement : Les paris sportifs sont soumis aux aléas. Gestion rigoureuse obligatoire.*")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def export_to_json(report: DailyReport, output_path: Path) -> Path:
    """Exports daily report as structured JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(report)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path
