"""Team name normalization across The Odds API, Football-Data.org, and Understat."""

from __future__ import annotations
import re
import unicodedata
from typing import Dict, Optional

# Canonical mapping for top European teams across different data feeds
CANONICAL_CLUBS: Dict[str, str] = {
    # Ligue 1
    "paris saint germain": "Paris Saint-Germain",
    "paris saint-germain": "Paris Saint-Germain",
    "psg": "Paris Saint-Germain",
    "paris sg": "Paris Saint-Germain",
    "marseille": "Olympique de Marseille",
    "olympique marseille": "Olympique de Marseille",
    "om": "Olympique de Marseille",
    "lyon": "Olympique Lyonnais",
    "olympique lyon": "Olympique Lyonnais",
    "ol": "Olympique Lyonnais",
    "monaco": "AS Monaco",
    "lille": "LOSC Lille",
    "lille osc": "LOSC Lille",
    "lens": "RC Lens",
    "racing club lens": "RC Lens",
    "nice": "OGC Nice",
    "rennes": "Stade Rennais",
    "stade rennais": "Stade Rennais",
    "brest": "Stade Brestois 29",
    "stade brestois": "Stade Brestois 29",
    "strasbourg": "RC Strasbourg",
    "toulouse": "Toulouse FC",
    "reims": "Stade de Reims",
    "montpellier": "Montpellier HSC",
    "nantes": "FC Nantes",
    "auxerre": "AJ Auxerre",
    "le havre": "Le Havre AC",
    "saint-etienne": "AS Saint-Étienne",
    "angers": "Angers SCO",

    # Premier League
    "arsenal": "Arsenal",
    "chelsea": "Chelsea",
    "liverpool": "Liverpool",
    "manchester city": "Manchester City",
    "man city": "Manchester City",
    "manchester united": "Manchester United",
    "man united": "Manchester United",
    "man utd": "Manchester United",
    "tottenham hotspur": "Tottenham Hotspur",
    "tottenham": "Tottenham Hotspur",
    "spurs": "Tottenham Hotspur",
    "aston villa": "Aston Villa",
    "newcastle united": "Newcastle United",
    "newcastle": "Newcastle United",
    "brighton": "Brighton & Hove Albion",
    "brighton and hove albion": "Brighton & Hove Albion",
    "brentford": "Brentford",
    "west ham united": "West Ham United",
    "west ham": "West Ham United",
    "fulham": "Fulham",
    "crystal palace": "Crystal Palace",
    "bournemouth": "AFC Bournemouth",
    "wolverhampton wanderers": "Wolverhampton Wanderers",
    "wolves": "Wolverhampton Wanderers",
    "everton": "Everton",
    "nottingham forest": "Nottingham Forest",
    "ipswich town": "Ipswich Town",
    "southampton": "Southampton",
    "leicester city": "Leicester City",

    # Champions League & European Contenders
    "real madrid": "Real Madrid",
    "barcelona": "FC Barcelone",
    "fc barcelona": "FC Barcelone",
    "atletico madrid": "Atlético Madrid",
    "atletico de madrid": "Atlético Madrid",
    "bayern munich": "Bayern Munich",
    "bayern munchen": "Bayern Munich",
    "fc bayern munchen": "Bayern Munich",
    "borussia dortmund": "Borussia Dortmund",
    "bvb dortmund": "Borussia Dortmund",
    "bayer leverkusen": "Bayer Leverkusen",
    "leverkusen": "Bayer Leverkusen",
    "inter milan": "Inter Milan",
    "internazionale": "Inter Milan",
    "inter": "Inter Milan",
    "juventus": "Juventus",
    "milan": "AC Milan",
    "ac milan": "AC Milan",
    "atalanta": "Atalanta",
    "napoli": "Napoli",
    "sporting cp": "Sporting CP",
    "sporting lisbon": "Sporting CP",
    "benfica": "SL Benfica",
    "porto": "FC Porto",

    # UEFA Nations League / Sélections Nationales
    "france": "France",
    "italy": "Italie",
    "italie": "Italie",
    "belgium": "Belgique",
    "belgique": "Belgique",
    "spain": "Espagne",
    "espagne": "Espagne",
    "germany": "Allemagne",
    "allemagne": "Allemagne",
    "netherlands": "Pays-Bas",
    "pays bas": "Pays-Bas",
    "pays-bas": "Pays-Bas",
    "holland": "Pays-Bas",
    "england": "Angleterre",
    "angleterre": "Angleterre",
    "portugal": "Portugal",
    "croatia": "Croatie",
    "croatie": "Croatie",
    "denmark": "Danemark",
    "danemark": "Danemark",
    "switzerland": "Suisse",
    "suisse": "Suisse",
    "poland": "Pologne",
    "pologne": "Pologne",
    "austria": "Autriche",
    "autriche": "Autriche",
    "israel": "Israël",
    "israël": "Israël",
    "sweden": "Suède",
    "suede": "Suède",
    "suède": "Suède",
    "norway": "Norvège",
    "norvege": "Norvège",
    "norvège": "Norvège",
    "serbia": "Serbie",
    "serbie": "Serbie",
    "scotland": "Écosse",
    "ecosse": "Écosse",
    "écosse": "Écosse",
    "turkey": "Turquie",
    "turquie": "Turquie",
    "türkiye": "Turquie",
    "hungary": "Hongrie",
    "hongrie": "Hongrie",
    "czechia": "République Tchèque",
    "czech republic": "République Tchèque",
    "republique tcheque": "République Tchèque",
    "greece": "Grèce",
    "grece": "Grèce",
    "grèce": "Grèce",
    "slovakia": "Slovaquie",
    "slovaquie": "Slovaquie",
    "slovenia": "Slovénie",
    "slovenie": "Slovénie",
    "ukraine": "Ukraine",
    "romania": "Roumanie",
    "roumanie": "Roumanie",
    "ireland": "Irlande",
    "irlande": "Irlande",
    "northern ireland": "Irlande du Nord",
    "wales": "Pays de Galles",
    "finland": "Finlande",
    "finlande": "Finlande",
    "iceland": "Islande",
    "islande": "Islande",
}


def clean_team_name(name: str) -> str:
    """Cleans punctuation, accents, and club prefixes for uniform matching."""
    if not name:
        return ""
    # Strip accents
    normalized = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in normalized if not unicodedata.combining(c))
    s = stripped.lower().strip()

    # Remove standard noise tokens and club suffixes/prefixes
    tokens_to_remove = [
        r"\bfc\b", r"\bafc\b", r"\bcf\b", r"\bsc\b", r"\brc\b", r"\bogc\b",
        r"\bas\b", r"\bhsc\b", r"\baj\b", r"\bac\b", r"\bsco\b",
        r"\bolympique\b", r"\bde\b", r"\bthe\b", r"\bstade\b",
    ]
    for pattern in tokens_to_remove:
        s = re.sub(pattern, " ", s)

    # Clean whitespace and non-alphanumeric chars
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canonicalize_team_name(raw_name: str) -> str:
    """Resolves any raw club name (from The Odds API, Football-Data, or Understat)

    to its single canonical name.
    """
    cleaned = clean_team_name(raw_name)

    # 1. Exact match in canonical dict
    if cleaned in CANONICAL_CLUBS:
        return CANONICAL_CLUBS[cleaned]

    # 2. Substring matching in canonical dict
    for key, canonical in CANONICAL_CLUBS.items():
        if key == cleaned or (len(key) >= 4 and (key in cleaned or cleaned in key)):
            return canonical

    # 3. Fallback to title-cased cleaned name if unknown
    return raw_name.strip()

