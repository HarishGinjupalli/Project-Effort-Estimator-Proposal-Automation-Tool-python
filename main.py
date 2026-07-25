"""
main.py
CLI entry point.

Usage:
    python main.py --input data/sample_client_requirements.csv --client "Contoso Retail" --output output/Contoso_Proposal.docx
"""

import argparse
import sys

from src.config_manager import load_rate_card, load_project_config, ConfigError
from src.estimator import load_requirements, build_estimate, EstimationError
from src.proposal_generator import generate_proposal
from src.utils import setup_logger, format_currency


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate a client effort/cost proposal from a requirements CSV."
    )
    parser.add_argument("--input", required=True, help="Path to requirements CSV")
    parser.add_argument("--client", required=True, help="Client name for the proposal")
    parser.add_argument("--output", required=True, help="Path to save the generated .docx proposal")
    parser.add_argument(
        "--rate-card", default="config/rate_card.yaml", help="Path to rate_card.yaml"
    )
    parser.add_argument(
        "--config", default="config/config.yaml", help="Path to config.yaml"
    )
    parser.add_argument(
        "--id-col", default=None,
        help="Override auto-detection: exact CSV column name for requirement ID",
    )
    parser.add_argument(
        "--desc-col", default=None,
        help="Override auto-detection: exact CSV column name for requirement description",
    )
    parser.add_argument(
        "--role-col", default=None,
        help="Override auto-detection: exact CSV column name for assigned role",
    )
    parser.add_argument(
        "--complexity-col", default=None,
        help="Override auto-detection: exact CSV column name for complexity",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Fail on unknown roles/complexity instead of falling back to rate_card.yaml defaults",
    )
    parser.add_argument(
        "--no-charts", action="store_true",
        help="Skip the Visual Summary chart section (cost-by-role, effort-by-complexity, top cost drivers)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logger()

    try:
        logger.info("Loading configuration...")
        rate_card = load_rate_card(args.rate_card)
        project_config = load_project_config(args.config)

        logger.info(f"Loading requirements from {args.input}...")
        df = load_requirements(
            args.input,
            id_col=args.id_col,
            desc_col=args.desc_col,
            role_col=args.role_col,
            complexity_col=args.complexity_col,
        )
        logger.info(f"Loaded {len(df)} requirement(s).")

        logger.info("Calculating effort and cost estimate...")
        summary = build_estimate(df, rate_card, strict=args.strict)

        if summary.unmapped_roles:
            logger.warning(
                f"Roles not in rate_card.yaml, priced at default_role_rate "
                f"({rate_card.default_role_rate}): {summary.unmapped_roles}"
            )
        if summary.unmapped_complexity:
            logger.warning(
                f"Complexity values not in rate_card.yaml, defaulted to "
                f"'{rate_card.default_complexity}': {summary.unmapped_complexity}"
            )

        logger.info(
            f"Estimate complete: {summary.subtotal_effort_days} person-days, "
            f"grand total {format_currency(summary.grand_total, summary.currency)}"
        )

        logger.info(f"Generating proposal document for client '{args.client}'...")
        output_path = generate_proposal(
            summary, project_config, args.client, args.output,
            include_charts=not args.no_charts,
        )

        logger.info(f"Proposal saved to: {output_path}")
        print(f"\nDone. Proposal saved to: {output_path}")

    except (ConfigError, EstimationError) as e:
        logger.error(f"Failed: {e}")
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
