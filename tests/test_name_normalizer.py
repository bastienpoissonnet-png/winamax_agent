"""Unit tests verifying strict separation between Paris FC and Paris Saint-Germain."""

import pytest
from winamax_agent.ingestion.name_normalizer import canonicalize_team_name, clean_team_name
from winamax_agent.ingestion.stats_provider import FootballStatsProvider


def test_canonicalize_paris_fc_vs_psg():
    """Guarantees that Paris FC and Paris Saint-Germain are strictly distinct."""
    pfc_canonical = canonicalize_team_name("Paris FC")
    psg_canonical = canonicalize_team_name("Paris Saint-Germain")

    assert pfc_canonical == "Paris FC"
    assert psg_canonical == "Paris Saint-Germain"
    assert pfc_canonical != psg_canonical

    # Variants of Paris FC
    assert canonicalize_team_name("paris fc") == "Paris FC"
    assert canonicalize_team_name("PFC") == "Paris FC"
    assert canonicalize_team_name("pfc") == "Paris FC"
    assert canonicalize_team_name("Paris Football Club") == "Paris FC"
    assert canonicalize_team_name("Paris F.C.") == "Paris FC"

    # Variants of Paris Saint-Germain
    assert canonicalize_team_name("PSG") == "Paris Saint-Germain"
    assert canonicalize_team_name("psg") == "Paris Saint-Germain"
    assert canonicalize_team_name("Paris SG") == "Paris Saint-Germain"
    assert canonicalize_team_name("Paris Saint Germain") == "Paris Saint-Germain"
    assert canonicalize_team_name("Paris St Germain") == "Paris Saint-Germain"
    assert canonicalize_team_name("Paris Saint-Germain FC") == "Paris Saint-Germain"


def test_clean_team_name_paris_fc():
    """Verifies that clean_team_name does not strip 'fc' from Paris FC."""
    assert clean_team_name("Paris FC") == "paris fc"
    assert clean_team_name("PFC") == "paris fc"
    assert clean_team_name("Paris Football Club") == "paris fc"
    assert clean_team_name("Paris Saint-Germain") != "paris fc"


def test_stats_provider_paris_fc_never_returns_psg():
    """Guarantees that get_team_metrics('Paris FC') never returns PSG data."""
    provider = FootballStatsProvider()

    pfc_metrics = provider.get_team_metrics("Paris FC")
    psg_metrics = provider.get_team_metrics("Paris Saint-Germain")

    # Names must be strictly distinct
    assert pfc_metrics.name == "Paris FC"
    assert psg_metrics.name == "Paris Saint-Germain"
    assert pfc_metrics.name != psg_metrics.name

    # League differentiation (Ligue 2 vs Ligue 1)
    assert pfc_metrics.league == "Ligue 2"
    assert psg_metrics.league == "Ligue 1"

    # Recent form and metrics must not be shared
    assert pfc_metrics.streak_l5 == "V-N-D-V-N"
    assert psg_metrics.streak_l5 == "V-V-N-V-V"
    assert pfc_metrics.recent_form_points == 8.0
    assert psg_metrics.recent_form_points == 13.0
    assert pfc_metrics.xg_for_per_match < psg_metrics.xg_for_per_match

    # Raw name aliases must also resolve to Paris FC metrics
    pfc_alias_metrics = provider.get_team_metrics("PFC")
    assert pfc_alias_metrics.name == "Paris FC"
    assert pfc_alias_metrics.league == "Ligue 2"


def test_pitch_dynamic_paris_fc_does_not_contain_psg():
    """Verifies that pitch dynamic text generated for Paris FC mentions Paris FC, not PSG."""
    provider = FootballStatsProvider()
    pfc_metrics = provider.get_team_metrics("Paris FC", is_home=True)
    away_metrics = provider.get_team_metrics("Rodez", is_home=False)

    pitch_dynamic = provider.generate_pitch_dynamic(
        home_team="Paris FC",
        away_team="Rodez",
        home_metrics=pfc_metrics,
        away_metrics=away_metrics,
        market_key="h2h",
        selection_key="home",
    )

    assert "Paris FC" in pitch_dynamic
    assert "Paris Saint-Germain" not in pitch_dynamic
    assert "PSG" not in pitch_dynamic

