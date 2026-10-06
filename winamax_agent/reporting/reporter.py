"""Recommendation reporting module generating structured betting advisories."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from winamax_agent.ingestion.stats_provider import MatchContext
from winamax_agent.models.value_bet import ValueOpportunity
from winamax_agent.staking.kelly import KellyResult


@dataclass
class BetRecommendation:
    """Full recommendation package for a single selected bet."""
    competition: str
    match_title: str
    kickoff: str
    market_name: str
    selection_label: str
    bookmaker: str
    winamax_odds: float
    raw_implied_prob_pct: float
    fair_bookmaker_prob_pct: float
    model_true_prob_pct: float
    edge_pct: float
    ev_pct: float
    stake_eur: float
    stake_details: str
    point_1_xg: str
    point_2_h2h_tactics: str
    point_3_context_form: str


@dataclass
class DailyReport:
    """Consolidated daily report of betting market analysis."""
    timestamp: str
    total_matches_analyzed: int
    total_markets_analyzed: int
    positive_ev_count: int
    top_recommendation: Optional[BetRecommendation] = None
    secondary_recommendations: List[BetRecommendation] = field(default_factory=list)

    def render_console(self) -> str:
        """Formats the report for direct terminal display."""
        lines = []
        bar = "=" * 80
        sep = "-" * 80

        lines.append(bar)
        lines.append(" 🎯 WINAMAX VALUE BETTING AGENT - RAPPORT QUOTIDIEN D'AIDE À LA DÉCISION")
        lines.append(f" Date d'analyse : {self.timestamp}")
        lines.append(
            f" Marchés analysés : {self.total_markets_analyzed} sur {self.total_matches_analyzed} rencontres "
            f"| Opportunités EV > 0 : {self.positive_ev_count}"
        )
        lines.append(bar)

        if not self.top_recommendation:
            lines.append("\n⚠️  AUCUNE OPPORTUNITÉ À ESPÉRANCE DE GAIN POSITIVE (EV > 0) DÉTECTÉE.")
            lines.append("    Principe quantitatif strict : La meilleure décision de gestion est de NE PAS PARIER.")
            lines.append("    Mise recommandée aujourd'hui : 0.00 €\n")
            lines.append(bar)
            return "\n".join(lines)

        rec = self.top_recommendation
        lines.append("\n🏆 RECOMMANDATION PRINCIPALE DU JOUR (MEILLEUR VALUE BET) :")
        lines.append(f"  • Match        : {rec.match_title} ({rec.competition})")
        lines.append(f"  • Coup d'envoi : {rec.kickoff}")
        lines.append(f"  • Marché       : {rec.market_name}")
        lines.append(f"  • Pari retenu  : {rec.selection_label}")
        lines.append(f"  • Cote Winamax : {rec.winamax_odds:.2f}")
        lines.append("")
        lines.append("📊 ANALYSE QUANTITATIVE & PROBABILITÉS :")
        lines.append(f"  • Probabilité brute Winamax (avec marge) : {rec.raw_implied_prob_pct:.1f}%")
        lines.append(f"  • Probabilité fair Winamax (sans marge)  : {rec.fair_bookmaker_prob_pct:.1f}%")
        lines.append(f"  • Probabilité réelle estimée (Modèle xG) : {rec.model_true_prob_pct:.1f}%")
        lines.append(f"  • Avantage estimé (Edge)                 : {rec.edge_pct:+.2f}%")
        lines.append(f"  • Espérance de gain (Expected Value - EV): {rec.ev_pct:+.2f}% (STRICTEMENT POSITIVE)")
        lines.append("")
        lines.append("💰 GESTION DE MISE & BANKROLL (STAKING) :")
        lines.append(f"  • MISE EXACTE CONSEILLÉE : {rec.stake_eur:.2f} €")
        lines.append(f"  • Justification sizing   : {rec.stake_details}")
        lines.append("")
        lines.append("🔍 JUSTIFICATION ANALYTIQUE EN 3 POINTS CLÉS :")
        lines.append(f"  1. [xG & Métriques avancées] :")
        lines.append(f"     {rec.point_1_xg}")
        lines.append(f"  2. [Confrontation directe & dynamique tactique] :")
        lines.append(f"     {rec.point_2_h2h_tactics}")
        lines.append(f"  3. [Contexte d'équipe, absences & dynamique] :")
        lines.append(f"     {rec.point_3_context_form}")

        if self.secondary_recommendations:
            lines.append("\n" + sep)
            lines.append("📋 AUTRES OPPORTUNITÉS SECONDRAIRES VALABLES (EV > 0) :")
            for i, sec in enumerate(self.secondary_recommendations, 1):
                lines.append(
                    f"  {i}. {sec.match_title} | {sec.selection_label} @ {sec.winamax_odds:.2f} "
                    f"| EV: {sec.ev_pct:+.1f}% | Modèle: {sec.model_true_prob_pct:.1f}% "
                    f"| Mise suggérée: {sec.stake_eur:.2f} €"
                )

        lines.append("\n" + bar)
        lines.append(" ⚠️ Avertissement : Les paris sportifs comportent des risques. Ce rapport est un outil")
        lines.append("    d'aide à la décision mathématique basé sur le modèle Kelly fractionnaire.")
        lines.append(bar + "\n")

        return "\n".join(lines)
