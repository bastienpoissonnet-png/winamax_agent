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
├── .github/
│   └── workflows/
│       └── daily_bet.yml           # Workflow GitHub Actions (10h00 UTC quotidien + Discord)
├── pyproject.toml                  # Configuration du package
├── requirements.txt                # Dépendances Python
├── .env.example                    # Modèle des variables d'environnement
├── Dockerfile                      # Conteneur pour exécution en production
├── winamax-agent.service           # Service systemd pour serveur Linux/VPS
├── winamax_agent/
│   ├── config.py                   # Gestionnaire de configuration (.env / CLI)
│   ├── agent.py                    # Orchestrateur central du pipeline quantitatif
│   ├── scheduler.py                # Planificateur périodique (boucle d'exécution)
│   ├── cli.py                      # Interface en ligne de commande
│   ├── ingestion/
│   │   ├── odds_client.py          # Client The Odds API (Winamax / EU)
│   │   ├── fotmob_client.py        # Client FotMob (stats sans clé API & sélections nationales)
│   │   ├── football_data_client.py # Client Football-Data.org (forme récente & résultats)
│   │   ├── understat_client.py     # Scraper/extracteur Understat (xG/xGA réels par match)
│   │   ├── name_normalizer.py      # Normalisation canonique des clubs inter-sources
│   │   ├── stats_provider.py       # Agrégateur dynamique xG/forme & justifications
│   │   └── mock_data.py            # Fixtures et cotes Winamax de simulation / hors-ligne
│   ├── models/
│   │   ├── margin.py               # Calcul d'overround et retrait de marge
│   │   ├── poisson_xg.py           # Moteur Dixon-Coles / Poisson bivarié
│   │   ├── value_bet.py            # Évaluation du Value Bet (Edge, EV)
│   │   └── parlays.py              # Générateur de combinés intelligents & de secours
│   ├── staking/
│   │   └── kelly.py                # Kelly fractionnaire, Micro-Kelly & mise de secours
│   └── reporting/
│       ├── reporter.py             # Formateur console et structure du rapport (4 blocs)
│       ├── discord_notifier.py     # Formateur d'Embed et expéditeur Webhook Discord
│       └── exporters.py            # Exporteurs Markdown et JSON
├── reports/                        # Dossier de sauvegarde des rapports quotidiens
│   └── cache/                      # Cache local Understat, FotMob & Football-Data.org
└── tests/                          # 41 tests unitaires et d'intégration validés
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
# Clé API The Odds API (Gratuit : 500 requêtes/mois sur https://the-odds-api.com)
ODDS_API_KEY=votre_cle_the_odds_api_ici

# Clé API Football-Data.org (Gratuit : https://www.football-data.org/client/register)
FOOTBALL_DATA_API_KEY=votre_cle_football_data_ici

BOOKMAKER=winamax
COMPETITIONS=soccer_uefa_nations_league,soccer_france_ligue_one,soccer_epl,soccer_spain_la_liga,soccer_italy_serie_a,soccer_germany_bundesliga,soccer_uefa_champs_league,soccer_uefa_europa_league
MARKETS=h2h,totals

TOTAL_BANKROLL=500.0
KELLY_FRACTION=0.50
MIN_STAKE=1.0
MAX_STAKE=20.0
MIN_EV_THRESHOLD=0.005
MIN_ODDS=1.50
MAX_ODDS=3.00
MIN_PROB_THRESHOLD=0.40
MIN_PROB_LOW_ODDS=0.60

PARLAY_MIN_PROB=0.60
PARLAY_MIN_ODDS=1.80
PARLAY_MAX_ODDS=4.00
PARLAY_MAX_STAKE=15.0
PARLAY_KELLY_FRACTION=0.35

SCHEDULE_INTERVAL_HOURS=6
SIMULATION_MODE=false
```

> **Note :** Si aucune clé API n'est renseignée, l'agent bascule automatiquement en mode **Simulation/Démonstration** avec des fixtures et cotes Winamax réalistes (Ligue des Nations, L1, PL, UCL) pour tester immédiatement le pipeline.

---

## 💻 4. Utilisation

### Exécution unique (Génération des rapports Section A et Section B)
```bash
python3 -m winamax_agent.cli --run-once
```

### Mode Démonstration / Hors-ligne (sans consommer de quota d'API)
```bash
python3 -m winamax_agent.cli --demo
```

### Paramétrer la Bankroll et le seuil d'EV en ligne de commande
```bash
python3 -m winamax_agent.cli --bankroll 1000 --min-ev 0.005 --kelly-fraction 0.50
```

### Mode Planifié (Worker autonome toutes les 6 heures)
```bash
python3 -m winamax_agent.cli --schedule --interval-hours 6
```

---

## 📊 5. Format de Sortie Généré (`latest_report.md`)

L'agent produit automatiquement deux fichiers dans `reports/` :
1. `reports/latest_report.md` (Markdown structuré avec Section A et Section B).
2. `reports/latest_report.json` (JSON structuré pour intégration bot Discord/Telegram/Webhook).

### Structure du Rapport Quotidien :
- **Section A : Meilleur Pari Simple (Sweet Spot [1.50, 3.00])**
  * Événement, marché et cote Winamax.
  * Probabilité sans marge, probabilité réelle estimée (Modèle Dixon-Coles xG + ancrage marché), Edge et EV.
  * Mise Kelly 50% avec paliers de risque (10 € à 20 € max pour cotes 1.50-1.85, 10 € max pour 1.86-2.30, 5 € max pour 2.31-3.00).
  * Justification analytique en 3 points : xG réels Understat, confrontations/tactique, forme récente Football-Data.org.
- **Section B : Meilleur Combiné du Jour (2 à 3 matchs, Cote totale [1.80, 4.00])**
  * Sélections sur matchs strictement distincts (indépendance statistique).
  * Sélections sécurisées à haute probabilité individuelle ($P_{\text{modèle}} \ge 60\%$, ex: 1X, X2, Over 1.5).
  * Cote combinée totale, probabilité combinée cumulée et EV combinée positive.
  * Staking Kelly combiné fractionnaire plafonné strictement à 15.00 € max.
  * Justification croisée de corrélation et indépendance statistique.
- **Opportunités secondaires :** Paris simples et combinés alternatifs à espérance positive (EV > 0.5%).

---

## 📲 6. Automatisation Cloud & Notifications Discord (Sans PC allumé)

Pour exécuter l'agent chaque jour **gratuitement dans le cloud** et recevoir les recommandations directement sur votre smartphone via Discord (sans laisser de machine allumée), le projet intègre un workflow **GitHub Actions** (`.github/workflows/daily_bet.yml`).

### 📌 Les 3 étapes de configuration :

#### Étape 1 : Pousser le projet sur votre dépôt GitHub
Si votre dépôt local n'est pas encore lié à votre compte GitHub (idéalement un dépôt privé pour sécuriser vos stratégies) :
```bash
git add .
git commit -m "feat: agent decisionnel, notifications discord et github actions"
git remote add origin https://github.com/<votre-utilisateur>/<votre-depot>.git
git branch -M main
git push -u origin main
```

#### Étape 2 : Configurer les Secrets GitHub du dépôt
Rendez-vous sur l'interface GitHub de votre projet :
1. Allez dans l'onglet **Settings** > **Secrets and variables** > **Actions**.
2. Cliquez sur **New repository secret** et enregistrez les 3 variables suivantes :
   * `ODDS_API_KEY` : Votre clé The Odds API (ex: `b9c8...`).
   * `FOOTBALL_DATA_API_KEY` : Votre clé Football-Data.org.
   * `DISCORD_WEBHOOK_URL` : L'URL du webhook de votre salon Discord privé *(dans Discord : Paramètres du salon > Intégrations > Webhooks > Nouveau webhook > Copier l'URL)*.

> [!NOTE]
> En cas d'absence de webhook, le moteur s'exécute normalement sans planter et génère les fichiers `reports/latest_report.md` et `reports/latest_report.json` téléchargeables dans les artefacts GitHub Actions.

#### Étape 3 : Activer et Tester l'Exécution
1. Rendez-vous dans l'onglet **Actions** de votre dépôt GitHub.
2. Sélectionnez le workflow **Daily Winamax Value Betting Analysis**.
3. Cliquez sur **Run workflow** pour lancer une première exécution manuelle immédiate.
4. Le workflow s'exécutera désormais **automatiquement tous les jours à 10h00 UTC (12h00 heure de Paris)** et publiera l'Embed complet sur votre téléphone :
   * 🟢 **Opportunités validées** ($EV > 0$) avec mise Kelly calculée.
   * 🟡 **Choix de secours** avec alerte explicite et mise symbolique bridée à 1,00 €.

---

## ⚙️ 7. Déploiements Alternatifs (VPS, Systemd, Docker, Cron Local)

### Option A : Service Linux Systemd (Sur VPS personnel)
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

### Option B : Tâche Cron Locale (ex: scan tous les jours à 12h00)
```bash
crontab -e
```
Ajouter la ligne suivante :
```cron
0 12 * * * /usr/bin/python3 -m winamax_agent.cli --run-once >> /home/bastien/winamax_agent/reports/cron.log 2>&1
```

### Option C : Conteneur Docker
```bash
docker build -t winamax-agent .
docker run -d --name winamax-worker --env-file .env -v $(pwd)/reports:/app/reports winamax-agent
```

---

## 🧪 8. Tests Unitaires & Intégration

L'ensemble de la suite de **41 tests unitaires et d'intégration** valide l'intégralité du pipeline mathématique, des intégrations d'API, de la génération d'Embed Discord et des modes de secours :
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
Résultat : **41 tests validés avec succès (OK)**.


