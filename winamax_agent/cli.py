"""Command-line interface (CLI) for the Winamax Betting Agent."""

from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path
from winamax_agent.agent import WinamaxBettingAgent
from winamax_agent.config import AgentConfig
from winamax_agent.reporting.discord_notifier import send_discord_report
from winamax_agent.reporting.exporters import export_to_json, export_to_markdown
from winamax_agent.scheduler import AgentScheduler


def parse_args() -> argparse.Namespace:
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(
        description="Winamax Sports Betting Value Agent (Ligue 1, Premier League, Champions League)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        default=True,
        help="Exécute une analyse unique et affiche le rapport sans boucle",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Lance l'agent en mode planifié (worker récurrent toutes les X heures)",
    )
    parser.add_argument(
        "--interval-hours",
        type=int,
        default=None,
        help="Intervalle entre chaque scan en mode planifié (en heures)",
    )
    parser.add_argument(
        "--demo",
        "--simulation",
        action="store_true",
        help="Force le mode démonstration / simulation (utilise les cotes Winamax de test)",
    )
    parser.add_argument(
        "--bankroll",
        type=float,
        default=None,
        help="Capital total alloué aux paris (€) pour le calcul de mise",
    )
    parser.add_argument(
        "--kelly-fraction",
        type=float,
        default=None,
        help="Fraction de Kelly à appliquer (ex: 0.50 pour Demi-Kelly)",
    )
    parser.add_argument(
        "--min-ev",
        type=float,
        default=None,
        help="Seuil minimal d'espérance de gain (ex: 0.0 pour strict EV > 0)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Dossier d'exportation des rapports (Markdown et JSON)",
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=".env",
        help="Chemin vers le fichier de variables d'environnement",
    )
    parser.add_argument(
        "--discord-webhook",
        type=str,
        default=None,
        help="URL du webhook Discord pour notification immédiate (écrase la valeur .env)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Active les logs détaillés en mode DEBUG",
    )
    # Bankroll tracking arguments
    parser.add_argument(
        "--record-bet",
        type=str,
        default=None,
        help="Enregistre un pari dans le suivi de bankroll (ex: 'Atlético Madrid')",
    )
    parser.add_argument(
        "--stake",
        type=float,
        default=None,
        help="Montant de la mise du pari en euros (€)",
    )
    parser.add_argument(
        "--odds",
        type=float,
        default=None,
        help="Cote Winamax du pari",
    )
    parser.add_argument(
        "--status",
        type=str,
        choices=["pending", "win", "loss"],
        default="pending",
        help="Résultat du pari : 'pending', 'win', ou 'loss'",
    )
    parser.add_argument(
        "--bankroll-file",
        type=str,
        default="reports/bankroll.json",
        help="Chemin vers le fichier de suivi bankroll.json",
    )

    return parser.parse_args()


def main() -> None:
    """CLI entrypoint."""
    args = parse_args()

    # Logging setup
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Interception de la commande d'enregistrement de pari
    if args.record_bet:
        if args.stake is None:
            print("❌ Erreur : L'argument --stake est obligatoire pour enregistrer un pari.")
            sys.exit(1)
        if args.odds is None:
            print("❌ Erreur : L'argument --odds est obligatoire pour enregistrer un pari.")
            sys.exit(1)

        from winamax_agent.bankroll import record_bet
        try:
            b_data = record_bet(
                selection=args.record_bet,
                stake=args.stake,
                odds=args.odds,
                status=args.status,
                filepath=args.bankroll_file,
            )
            status_emojis = {"win": "🟢 [GAGNÉ]", "loss": "🔴 [PERDU]", "pending": "⏳ [EN COURS]"}
            badge = status_emojis.get(args.status.lower(), f"[{args.status.upper()}]")
            net_prof = b_data["history"][-1]["net_profit"] if b_data.get("history") else 0.0
            print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(" 💼 SUIVI DE LA CAGNOTTE (BANKROLL TRACKER) — PARI ENREGISTRÉ")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f" • Sélection      : {args.record_bet}")
            print(f" • Mise & Cote    : {args.stake:.2f} € @ {args.odds:.2f}")
            print(f" • Statut         : {badge}")
            print(f" • Résultat net   : {net_prof:+.2f} €")
            print(f" • Solde actuel   : {b_data['current_bankroll']:.2f} € (Profit global: {b_data['total_profit']:+.2f} €)")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
            return
        except Exception as e:
            print(f"❌ Erreur lors de l'enregistrement du pari : {e}")
            sys.exit(1)

    # Load base configuration
    config = AgentConfig.from_env(env_path=args.env_file)

    # CLI Overrides
    if args.demo:
        config.simulation_mode = True
    if args.bankroll is not None:
        config.total_bankroll = args.bankroll
    if args.kelly_fraction is not None:
        config.kelly_fraction = args.kelly_fraction
    if args.min_ev is not None:
        config.min_ev_threshold = args.min_ev
    if args.output_dir:
        config.output_dir = Path(args.output_dir)
    if args.interval_hours is not None:
        config.schedule_interval_hours = args.interval_hours
    if args.discord_webhook:
        config.discord_webhook_url = args.discord_webhook.strip()

    # Initialize agent
    agent = WinamaxBettingAgent(config=config)

    if args.schedule:
        # Scheduled periodic worker
        scheduler = AgentScheduler(
            agent=agent,
            interval_hours=config.schedule_interval_hours,
        )
        scheduler.start_loop()
    else:
        # Run once
        report = agent.run_daily_analysis()
        print(report.render_console())

        # Automatically export reports
        out_dir = config.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        latest_md = out_dir / "latest_report.md"
        latest_json = out_dir / "latest_report.json"
        export_to_markdown(report, latest_md)
        export_to_json(report, latest_json)
        print(f"📁 Rapports sauvegardés : {latest_md} et {latest_json}\n")

        # Discord notification
        if config.discord_webhook_url:
            discord_success = send_discord_report(report, webhook_url=config.discord_webhook_url)
            if discord_success:
                print("📲 Notification Discord transmise avec succès sur votre salon !\n")
            else:
                print("⚠️ Impossible de transmettre la notification Discord (vérifiez le webhook).\n")


if __name__ == "__main__":
    main()

