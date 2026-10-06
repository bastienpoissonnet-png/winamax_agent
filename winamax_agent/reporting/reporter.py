"""Recommendation reporting module generating structured betting advisories for Singles & Parlays."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from winamax_agent.models.parlays import ParlayOpportunity


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
    pitch_dynamic: str = ""
    is_fallback: bool = False
    status_badge: str = "🟢 OPPORTUNITÉ VALIDÉE (EV > 0)"
    warning_message: str = ""

    def __post_init__(self):
        if self.is_fallback:
            if not self.status_badge or self.status_badge == "🟢 OPPORTUNITÉ VALIDÉE (EV > 0)":
                self.status_badge = "🟡 CHOIX DE SECOURS (SOUS-OPTIMAL / RECOMMANDATION PAR DÉFAUT)"
        else:
            if not self.status_badge:
                self.status_badge = "🟢 OPPORTUNITÉ VALIDÉE (EV > 0)"



@dataclass
class DailyReport:
    """Consolidated daily report of betting market analysis (4 distinct sections)."""
    timestamp: str
    total_matches_analyzed: int
    total_markets_analyzed: int
    positive_ev_count: int
    # Section 1 : Le Match du Jour (uniquement les matchs d'aujourd'hui)
    match_of_the_day: Optional[BetRecommendation] = None
    # Section 2 : Le Meilleur Pari Simple (Sweet spot 1.50 - 3.00 sur la semaine)
    top_recommendation: Optional[BetRecommendation] = None
    secondary_recommendations: List[BetRecommendation] = field(default_factory=list)
    # Section 3 : Le Meilleur Combiné (2 à 3 sélections, 1.80 - 4.00)
    top_parlay: Optional[ParlayOpportunity] = None
    secondary_parlays: List[ParlayOpportunity] = field(default_factory=list)
    # Section 4 : La « Cote Osée » (Cote >= 4.00, Micro-Kelly)
    longshot_recommendation: Optional[BetRecommendation] = None
    # Bankroll tracking
    current_bankroll: Optional[float] = None
    total_profit: Optional[float] = None

    def render_console(self) -> str:
        """Formats the report for direct terminal display across 4 distinct sections."""
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

        # -------------------------------------------------------------
        # SECTION 1 : LE MATCH DU JOUR (COUP D'ENVOI AUJOURD'HUI)
        # -------------------------------------------------------------
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(" 📅 SECTION 1 : LE MATCH DU JOUR (COUP D'ENVOI AUJOURD'HUI)")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        if not self.match_of_the_day:
            lines.append("  ℹ️  Aucune rencontre programmée aujourd'hui dans le calendrier — préservation du capital.")
            lines.append("     Mise recommandée pour aujourd'hui : 0.00 €.")
        else:
            m = self.match_of_the_day
            lines.append(f"  Statut : {m.status_badge}")
            if m.is_fallback and m.warning_message:
                lines.append(f"  {m.warning_message}\n")
            lines.append(f"  • Match        : {m.match_title} ({m.competition})")
            lines.append(f"  • Coup d'envoi : {m.kickoff} (AUJOURD'HUI)")
            lines.append(f"  • Marché       : {m.market_name}")
            lines.append(f"  • Sélection    : {m.selection_label}")
            lines.append(f"  • Cote Winamax : {m.winamax_odds:.2f}")
            if m.pitch_dynamic:
                lines.append(f"  • Dynamique terrain : {m.pitch_dynamic}")
            lines.append("")
            lines.append("📊 ANALYSE QUANTITATIVE :")
            lines.append(f"  • Probabilité fair Winamax (sans marge) : {m.fair_bookmaker_prob_pct:.1f}%")
            lines.append(f"  • Probabilité réelle estimée (Modèle)   : {m.model_true_prob_pct:.1f}%")
            lines.append(f"  • Avantage estimé (Edge)                : {m.edge_pct:+.2f}%")
            lines.append(f"  • Espérance de gain (Expected Value)    : {m.ev_pct:+.2f}%")
            lines.append("")
            lines.append("💰 GESTION DE MISE & BANKROLL :")
            lines.append(f"  • MISE CONSEILLÉE : {m.stake_eur:.2f} €")
            lines.append(f"  • Sizing détails  : {m.stake_details}")
            lines.append("")
            lines.append("🔍 JUSTIFICATION EN 3 POINTS CLÉS :")
            lines.append(f"  1. [xG réels] : {m.point_1_xg}")
            lines.append(f"  2. [Dynamique tactique & H2H] : {m.point_2_h2h_tactics}")
            lines.append(f"  3. [Forme récente] : {m.point_3_context_form}")

        # -------------------------------------------------------------
        # SECTION 2 : LE MEILLEUR PARI SIMPLE (SWEET SPOT 1.50 - 3.00)
        # -------------------------------------------------------------
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(" 🎯 SECTION 2 : LE MEILLEUR PARI SIMPLE (SWEET SPOT 1.50 - 3.00 SUR LA SEMAINE)")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        if not self.top_recommendation:
            lines.append("  ℹ️  Aucun pari simple éligible sur le marché cette semaine.")
            lines.append("     Mise recommandée pour les simples : 0.00 € (préservation du capital).")
        else:
            rec = self.top_recommendation
            lines.append(f"  Statut : {rec.status_badge}")
            if rec.is_fallback and rec.warning_message:
                lines.append(f"  {rec.warning_message}\n")
            lines.append(f"  • Match        : {rec.match_title} ({rec.competition})")
            lines.append(f"  • Coup d'envoi : {rec.kickoff}")
            lines.append(f"  • Marché       : {rec.market_name}")
            lines.append(f"  • Sélection    : {rec.selection_label}")
            lines.append(f"  • Cote Winamax : {rec.winamax_odds:.2f}")
            if rec.pitch_dynamic:
                lines.append(f"  • Dynamique terrain : {rec.pitch_dynamic}")
            lines.append("")
            lines.append("📊 ANALYSE QUANTITATIVE :")
            lines.append(f"  • Probabilité fair Winamax (sans marge) : {rec.fair_bookmaker_prob_pct:.1f}%")
            lines.append(f"  • Probabilité réelle estimée (Modèle)   : {rec.model_true_prob_pct:.1f}%")
            lines.append(f"  • Avantage estimé (Edge)                : {rec.edge_pct:+.2f}%")
            lines.append(f"  • Espérance de gain (Expected Value)    : {rec.ev_pct:+.2f}%")
            lines.append("")
            lines.append("💰 GESTION DE MISE & BANKROLL :")
            lines.append(f"  • MISE CONSEILLÉE : {rec.stake_eur:.2f} €")
            lines.append(f"  • Sizing détails  : {rec.stake_details}")
            lines.append("")
            lines.append("🔍 JUSTIFICATION EN 3 POINTS CLÉS :")
            lines.append(f"  1. [xG réels] : {rec.point_1_xg}")
            lines.append(f"  2. [Dynamique tactique & H2H] : {rec.point_2_h2h_tactics}")
            lines.append(f"  3. [Forme récente] : {rec.point_3_context_form}")

        # -------------------------------------------------------------
        # SECTION 3 : LE MEILLEUR COMBINÉ DU JOUR (2-3 SÉLECTIONS, 1.80 - 4.00)
        # -------------------------------------------------------------
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(" 🔗 SECTION 3 : LE MEILLEUR COMBINÉ DU JOUR (2 À 3 MATCHS - COTE 1.80 À 4.00)")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        if not self.top_parlay:
            lines.append("  ℹ️  Nombre insuffisant de matchs distincts pour constituer un combiné.")
            lines.append("     Mise recommandée combiné : 0.00 €.")
        else:
            p = self.top_parlay
            lines.append(f"  Statut : {p.status_badge}")
            if p.is_fallback and p.warning_message:
                lines.append(f"  {p.warning_message}\n")
            lines.append(f"  • Nombre de sélections : {p.legs_count} matchs DISTINCTS (Indépendance statistique)")
            lines.append(f"  • COTE COMBINÉE TOTALE : {p.total_odds:.2f}")
            lines.append(f"  • Probabilité combinée : {p.combined_prob_pct:.1f}%")
            lines.append(f"  • EV Combinée          : {p.combined_ev_pct:+.2f}%")
            lines.append(f"  • MISE COMBINÉ SUGGÉRÉE: {p.recommended_stake:.2f} €")
            lines.append(f"  • Sizing détails       : {p.stake_details}")
            lines.append("")
            lines.append("📋 DÉTAIL DES SÉLECTIONS DU COMBINÉ :")
            for i, leg in enumerate(p.legs, 1):
                lines.append(
                    f"    {i}. {leg.match_title} ({leg.competition}) | {leg.selection} @ {leg.odds:.2f} "
                    f"[P_indiv: {leg.prob_pct:.1f}%]"
                )
            lines.append("")
            lines.append("🔍 JUSTIFICATION CROISÉE :")
            lines.append(f"    {p.cross_justification}")

        # -------------------------------------------------------------
        # SECTION 4 : LA « COTE OSÉE » (FUN BET - COTE >= 4.00)
        # -------------------------------------------------------------
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(" 💣 SECTION 4 : LA « COTE OSÉE » (FUN BET - COTE >= 4.00 - SIZING MICRO-KELLY)")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        if not self.longshot_recommendation:
            lines.append("  ℹ️  Aucune cote osée (>= 4.00) disponible sur les marchés analysés.")
            lines.append("     Mise recommandée : 0.00 €.")
        else:
            ls = self.longshot_recommendation
            lines.append(f"  Statut : {ls.status_badge}")
            if ls.is_fallback and ls.warning_message:
                lines.append(f"  {ls.warning_message}\n")
            lines.append(f"  • Match        : {ls.match_title} ({ls.competition})")
            lines.append(f"  • Coup d'envoi : {ls.kickoff}")
            lines.append(f"  • Marché       : {ls.market_name}")
            lines.append(f"  • Sélection    : {ls.selection_label}")
            lines.append(f"  • COTE OSÉE    : {ls.winamax_odds:.2f} (Haute rémunération)")
            if ls.pitch_dynamic:
                lines.append(f"  • Dynamique terrain : {ls.pitch_dynamic}")
            lines.append("")
            lines.append("📊 ANALYSE QUANTITATIVE & ESTIMATION DE L'EDGE :")
            lines.append(f"  • Probabilité bookmaker (sans marge)    : {ls.fair_bookmaker_prob_pct:.1f}%")
            lines.append(f"  • Probabilité réelle estimée (Modèle)   : {ls.model_true_prob_pct:.1f}%")
            lines.append(f"  • Avantage estimé (Edge)                : {ls.edge_pct:+.2f}%")
            lines.append(f"  • Espérance de gain (Expected Value)    : {ls.ev_pct:+.2f}%")
            lines.append("")
            lines.append("💰 GESTION DE MISE ULTRA-SÉCURISÉE (MICRO-KELLY) :")
            lines.append(f"  • MISE FUN BET : {ls.stake_eur:.2f} € (Plafond strict 5.00 €)")
            lines.append(f"  • Sizing détails : {ls.stake_details}")
            lines.append("")
            lines.append("🔍 JUSTIFICATION DU FUN BET :")
            lines.append(f"  1. [xG réels] : {ls.point_1_xg}")
            lines.append(f"  2. [Dynamique tactique & H2H] : {ls.point_2_h2h_tactics}")
            lines.append(f"  3. [Forme récente] : {ls.point_3_context_form}")


        # -------------------------------------------------------------
        # OPPORTUNITÉS SECONDAIRES
        # -------------------------------------------------------------
        if self.secondary_recommendations or self.secondary_parlays:
            lines.append("\n" + sep)
            lines.append("📋 SÉLECTIONS SECONDAIRES VALABLES (EV > 0) :")
            if self.secondary_recommendations:
                lines.append("  [Paris Simples] :")
                for i, sec in enumerate(self.secondary_recommendations[:3], 1):
                    lines.append(
                        f"    {i}. {sec.match_title} | {sec.selection_label} @ {sec.winamax_odds:.2f} "
                        f"| EV: {sec.ev_pct:+.1f}% | Modèle: {sec.model_true_prob_pct:.1f}% | Mise: {sec.stake_eur:.2f} €"
                    )
            if self.secondary_parlays:
                lines.append("  [Combinés Alternatifs] :")
                for j, sp in enumerate(self.secondary_parlays[:2], 1):
                    legs_str = " + ".join(f"{l.match_title.split(' vs ')[0]} ({l.selection.split(' (')[0]})" for l in sp.legs)
                    lines.append(
                        f"    {j}. [{sp.legs_count} sélections] {legs_str} @ {sp.total_odds:.2f} "
                        f"| EV: {sp.combined_ev_pct:+.1f}% | P: {sp.combined_prob_pct:.1f}% | Mise: {sp.recommended_stake:.2f} €"
                    )

        lines.append("\n" + bar)
        lines.append(" ⚠️ Avertissement : Les paris sportifs comportent des risques. Ce rapport est un outil")
        lines.append("    d'aide à la décision mathématique basé sur le modèle Kelly fractionnaire.")
        lines.append(bar + "\n")

        return "\n".join(lines)
