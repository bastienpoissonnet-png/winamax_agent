# 🎯 Winamax Betting Agent : Outil d'Aide à la Décision Quantitative

Agent autonome conçu pour l'analyse quantitative et l'identification quotidienne des meilleures opportunités de **Value Betting** sur **Winamax** (Ligue 1, Premier League, Ligue des Champions), avec dimensionnement mathématique du capital via le critère de **Kelly fractionnaire**.

---

## 📐 1. Architecture Quantitative & Mathématique

### A. Suppression de la Marge Bookmaker (Vig / Overround)
Winamax prélève une commission sur chaque marché. Pour un marché 1X2 avec des cotes $O_1, O_2, O_3$ :
$$\text{Overround} = \sum_{i=1}^{3} \frac{1}{O_i} - 1$$

Pour retrouver la probabilité implicite non biaisée du marché (*Fair Implied Probability*), l'agent applique la normalisation multiplicative :
$$P_{i}^{\text{fair}} = \frac{1 / O_i}{\sum_{k} 1 / O_k}$$
*(L'agent inclut également la méthode exponentielle Power/Shin pour corriger le biais favori-outsider).*

### B. Modèle Prédictif Bivarié Poisson & Dixon-Coles (xG)
Les probabilités réelles ($P_{\text{true}}$) sont calculées via les métriques avancées d'**Expected Goals (xG)** :
- Force offensive ($\alpha_i$) et faiblesse défensive ($\beta_j$) normalisées par rapport aux moyennes de ligue.
- Avantage du terrain ($\gamma \approx 1.18$) et ajustements contextuels (fatigue, absences majeures).
- Modélisation de la matrice de scores avec correction de Dixon-Coles ($\rho$) pour les faibles scores (0-0, 1-0, 0-1, 1-1) :
$$P(X=x, Y=y) = \frac{\lambda^x e^{-\lambda}}{x!} \times \frac{\mu^y e^{-\mu}}{y!} \times \tau(x, y)$$

Les probabilités de marché (1X2, Plus/Moins de 2.5 buts, BTTS) sont obtenues par agrégation de la grille de scores.

### C. Espérance de Gain (Expected Value - EV)
Une opportunité n'est sélectionnée que si son espérance mathématique est **strictement positive** :
$$\text{EV} = (P_{\text{true}} \times \text{Cote}_{\text{Winamax}}) - 1.0 > 0$$
$$\text{Edge} = P_{\text{true}} - P^{\text{fair}}$$

### D. Dimensionnement de Mise : Critère de Kelly Fractionnaire (50%)
Pour maximiser le taux de croissance du capital à long terme tout en divisant les *drawdowns* par deux :
$$f^* = \frac{\text{EV}}{\text{Cote} - 1}$$
$$f_{\text{Demi-Kelly}} = 0.50 \times f^*$$
$$\text{Mise brute} = f_{\text{Demi-Kelly}} \times \text{Bankroll}$$

**Règles strictes de gestion :**
- Si $\text{EV} \le 0 \implies \text{Mise} = 0.00\text{ €}$ (Refus catégorique de parier).
- Plancher de mise : **1.00 €** (si $\text{EV} > 0$).
- Plafond absolu strict : **20.00 €**.

---

## 📁 2. Structure du Projet

```text
winamax_agent/
├── pyproject.toml              # Configuration du package
├── requirements.txt            # Dépendances Python
├── .env.example                # Modèle des variables d'environnement
├── Dockerfile                  # Conteneur pour exécution en production
├── winamax-agent.service       # Service systemd pour serveur Linux/VPS
├── winamax_agent/
│   ├── config.py               # Gestionnaire de configuration (.env / CLI)
│   ├── agent.py                # Orchestrateur central du pipeline quantitatif
│   ├── scheduler.py            # Planificateur périodique (boucle d'exécution)
│   ├── cli.py                  # Interface en ligne de commande
│   ├── ingestion/
│   │   ├── odds_client.py      # Client The Odds API (Winamax / EU)
│   │   ├── stats_provider.py   # Métriques xG, forme et justifications analytiques
│   │   └── mock_data.py        # Fixtures et cotes Winamax de simulation / hors-ligne
│   ├── models/
│   │   ├── margin.py           # Calcul d'overround et retrait de marge
│   │   ├── poisson_xg.py       # Moteur Dixon-Coles / Poisson bivarié
│   │   └── value_bet.py        # Évaluation du Value Bet (Edge, EV)
│   ├── staking/
│   │   └── kelly.py            # Kelly fractionnaire 50%, plancher 1€ et plafond 20€
│   └── reporting/
│       ├── reporter.py         # Formateur console et structure du rapport
│       └── exporters.py        # Exporteurs Markdown et JSON
├── reports/                    # Dossier de sauvegarde des rapports quotidiens
└── tests/                      # Suite de tests unitaires et d'intégration
```

---

## 🚀 3. Installation et Configuration

### Prérequis
- Python 3.10+ (standard library autonome sans compilation requise).

### Étape 1 : Cloner le dépôt et créer l'environnement virtuel
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Étape 2 : Configurer les clés d'API (`.env`)
Copiez le modèle `.env.example` en `.env` :
```bash
cp .env.example .env
```
Éditez le fichier `.env` :
```ini
# Clé API gratuite sur https://the-odds-api.com (500 requêtes/mois)
ODDS_API_KEY=votre_cle_api_ici

BOOKMAKER=winamax
COMPETITIONS=soccer_france_ligue_one,soccer_epl,soccer_uefa_champs_league
MARKETS=h2h,totals

TOTAL_BANKROLL=500.0
KELLY_FRACTION=0.50
MIN_STAKE=1.0
MAX_STAKE=20.0
MIN_EV_THRESHOLD=0.0

SCHEDULE_INTERVAL_HOURS=6
SIMULATION_MODE=false
```

> **Note :** Si aucune clé API n'est renseignée, l'agent bascule automatiquement en mode **Simulation/Démonstration** avec des cotes Winamax réalistes pour tester immédiatement le pipeline.

---

## 💻 4. Utilisation

### Exécution unique (Analyse immédiate)
```bash
python3 -m winamax_agent.cli --run-once
```

### Mode Démonstration / Hors-ligne (sans consommer de quota d'API)
```bash
python3 -m winamax_agent.cli --demo
```

### Paramétrer la Bankroll et le seuil d'EV en ligne de commande
```bash
python3 -m winamax_agent.cli --bankroll 1000 --min-ev 0.05 --kelly-fraction 0.50
```

### Mode Planifié (Worker autonome toutes les 6 heures)
```bash
python3 -m winamax_agent.cli --schedule --interval-hours 6
```

---

## 📊 5. Format de Sortie Généré

L'agent affiche un rapport console et produit automatiquement deux fichiers dans `reports/` :
1. `reports/latest_report.md` (Markdown lisible avec tableaux et alertes).
2. `reports/latest_report.json` (JSON structuré pour intégration bot Discord/Telegram/Webhook).

### Exemple d'affichage console :
```text
================================================================================
 🎯 WINAMAX VALUE BETTING AGENT - RAPPORT QUOTIDIEN D'AIDE À LA DÉCISION
 Date d'analyse : 2026-10-06 10:19:41
 Marchés analysés : 25 sur 5 rencontres | Opportunités EV > 0 : 11
================================================================================

🏆 RECOMMANDATION PRINCIPALE DU JOUR (MEILLEUR VALUE BET) :
  • Match        : Arsenal vs Chelsea (Premier League)
  • Coup d'envoi : 2026-10-07T17:30:00Z
  • Marché       : 1X2 (Résultat)
  • Pari retenu  : Victoire Arsenal (1)
  • Cote Winamax : 1.88

📊 ANALYSE QUANTITATIVE & PROBABILITÉS :
  • Probabilité brute Winamax (avec marge) : 53.2%
  • Probabilité fair Winamax (sans marge)  : 51.2%
  • Probabilité réelle estimée (Modèle xG) : 64.2%
  • Avantage estimé (Edge)                 : +13.01%
  • Espérance de gain (Expected Value - EV): +20.71% (STRICTEMENT POSITIVE)

💰 GESTION DE MISE & BANKROLL (STAKING) :
  • MISE EXACTE CONSEILLÉE : 20.00 €
  • Justification sizing   : Pari à valeur (EV: 20.71%). Demi-Kelly appliqué (50%). Plafond strict de 20.00 € atteint.

🔍 JUSTIFICATION ANALYTIQUE EN 3 POINTS CLÉS :
  1. [xG & Métriques avancées] :
     Métrique xG : Arsenal génère en moyenne 2.05 xG/m pour 0.75 xGA concédés (différentiel net +1.30). En face, Chelsea affiche 1.90 xG et 1.28 xGA (différentiel +0.62). L'écart de création brute valide un net ascendant statistique.
  2. [Confrontation directe & dynamique tactique] :
     Dynamique tactique & confrontations : Le schéma tactique confronte le volume offensif à domicile face à un bloc adverse concédant régulièrement des situations franches à l'extérieur. Les métriques d'efficacité dans les 30 derniers mètres confirment un avantage structurel sur ce profil de match.
  3. [Contexte d'équipe, absences & dynamique] :
     Contexte d'équipe & forme récente : Arsenal totalise 13/15 pts récents (effectif quasi au complet, indice fatigue 30%), contre 10/15 pts pour Chelsea (absences pesant sur le rendement). Le différentiel de fraîcheur physique et de dynamique valide l'espérance de gain.
```

---

## ⚙️ 6. Déploiement en Production

### Option A : Service Linux Systemd (Recommandé sur VPS)
1. Copier le fichier de service :
```bash
sudo cp winamax-agent.service /etc/systemd/system/
```
2. Activer et démarrer le démon :
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now winamax-agent.service
```
3. Suivre les logs en temps réel :
```bash
journalctl -u winamax-agent.service -f
```

### Option B : Tâche Cron (ex: scan tous les jours à 09h00 et 14h00)
```bash
crontab -e
```
Ajouter la ligne suivante :
```cron
0 9,14 * * * /home/bastien/winamax_agent/.venv/bin/python3 -m winamax_agent.cli --run-once >> /home/bastien/winamax_agent/reports/cron.log 2>&1
```

### Option C : Docker
```bash
docker build -t winamax-agent .
docker run -d --name winamax-worker --env-file .env -v $(pwd)/reports:/app/reports winamax-agent
```

---

## 🧪 7. Tests Unitaires & Intégration

L'ensemble de la suite de tests valide la cohérence des calculs de marge, la formule de Kelly (plancher/plafond/EV<=0) et la simulation Dixon-Coles :
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
Résultat : **15 tests validés à 100%**.
