"""Exporters for saving reports into Markdown and JSON files."""

from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from winamax_agent.reporting.reporter import DailyReport


def export_to_markdown(report: DailyReport, output_path: Path) -> Path:
    """Exports daily report as a well-formatted Markdown file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# 🎯 Rapport d'Aide à la Décision - Paris Sportifs (Winamax)")
    lines.append(f"\n*Généré le : {report.timestamp}*")
    lines.append(
        f"\n**Marchés scannés :** {report.total_markets_analyzed} sur {report.total_matches_analyzed} rencontres "
        f"| **Opportunités à valeur (EV > 0) :** {report.positive_ev_count}"
    )

    if not report.top_recommendation:
        lines.append("\n> [!NOTE]\n> **Aucune opportunité à espérance de gain positive détectée.**")
        lines.append("> En gestion quantitative de bankroll, il est impératif de préserver son capital.")
        lines.append("> **Mise recommandée aujourd'hui : 0.00 €**")
    else:
        rec = report.top_recommendation
        lines.append("\n## 🏆 Meilleure Opportunité du Jour (Value Bet)")
        lines.append(f"\n- **Rencontre :** {rec.match_title} ({rec.competition})")
        lines.append(f"- **Coup d'envoi :** `{rec.kickoff}`")
        lines.append(f"- **Marché :** {rec.market_name}")
        lines.append(f"- **Sélection recommandée :** **{rec.selection_label}**")
        lines.append(f"- **Cote Winamax :** `{rec.winamax_odds:.2f}`")

        lines.append("\n### 📊 Métriques & Probabilités")
        lines.append("| Indicateur | Valeur |")
        lines.append("| :--- | :--- |")
        lines.append(f"| Probabilité brute Winamax (avec marge bookmaker) | {rec.raw_implied_prob_pct:.1f}% |")
        lines.append(f"| Probabilité fair Winamax (sans marge) | {rec.fair_bookmaker_prob_pct:.1f}% |")
        lines.append(f"| **Probabilité réelle estimée (Modèle xG/Poisson)** | **{rec.model_true_prob_pct:.1f}%** |")
        lines.append(f"| Avantage estimé (Edge) | {rec.edge_pct:+.2f}% |")
        lines.append(f"| **Espérance de gain (Expected Value - EV)** | **{rec.ev_pct:+.2f}%** |")

        lines.append("\n### 💰 Dimensionnement de la Mise (Kelly 50%)")
        lines.append(f"> **Mise recommandée : {rec.stake_eur:.2f} €**")
        lines.append(f">\n> *Détail : {rec.stake_details}*")

        lines.append("\n### 🔍 Justification Analytique en 3 Points Clés")
        lines.append(f"1. **Chiffres xG et création d'occasions :**\n   {rec.point_1_xg}")
        lines.append(f"2. **Confrontation directe et dynamique tactique :**\n   {rec.point_2_h2h_tactics}")
        lines.append(f"3. **Contexte d'équipe, absences et dynamique :**\n   {rec.point_3_context_form}")

        if report.secondary_recommendations:
            lines.append("\n## 📋 Opportunités Secondaires")
            lines.append("| Match | Sélection | Cote | EV | Prob. Modèle | Mise Suggérée |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for sec in report.secondary_recommendations:
                lines.append(
                    f"| {sec.match_title} | {sec.selection_label} | {sec.winamax_odds:.2f} | "
                    f"{sec.ev_pct:+.1f}% | {sec.model_true_prob_pct:.1f}% | {sec.stake_eur:.2f} € |"
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
