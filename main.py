from __future__ import annotations

import argparse

from app.data_sources import has_live_credentials, load_profile
from app.ics import write_ics
from app.live_binance import LiveDataUnavailable
from app.runtime import generate_plan


def render_plan(plan) -> str:
    lines: list[str] = []
    profile = plan.profile
    lines.append("# BNB Yield Cruiser MVP")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- balances: {profile.balances}")
    lines.append(f"- liquidity window: {profile.liquidity_window_days} days")
    lines.append(f"- risk tolerance: {profile.risk_tolerance}")
    lines.append(f"- advanced products: {'enabled' if profile.allow_advanced_products else 'disabled'}")
    lines.append(f"- data mode: {plan.data_mode}")
    if getattr(plan, "warnings", None):
        lines.append(f"- warnings: {len(plan.warnings)}")
    lines.append("")
    lines.append("## Allocation Plan")

    for item in plan.allocations:
        lines.append(
            f"- {item.bucket}: {item.amount:.4f} {item.asset} -> {item.scored.opportunity.product_name}"
        )
        lines.append(f"  fit: {item.scored.include_reason}")
        if item.scored.opportunity.notes:
            lines.append(f"  note: {item.scored.opportunity.notes}")

    lines.append("")
    lines.append("## Excluded Or Lower-Priority Options")
    for item in plan.excluded:
        lines.append(
            f"- {item.opportunity.product_name} ({item.opportunity.asset}, score {item.score:.2f}): {item.exclude_reason}"
        )

    if plan.reminders:
        lines.append("")
        lines.append("## Reminders")
        for reminder in plan.reminders:
            lines.append(f"- {reminder.title}: {reminder.when.isoformat()} -> {reminder.description}")

    lines.append("")
    lines.append("## Risk Notice")
    lines.append("- This MVP ranks fit, not guaranteed returns.")
    lines.append("- Advanced products are opt-in only and require user confirmation before execution.")
    if getattr(plan, "warnings", None):
        lines.append("")
        lines.append("## Data Warnings")
        for warning in plan.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BNB Yield Cruiser MVP planner.")
    parser.add_argument("--profile", default="data/profile.sample.json", help="Path to user profile JSON")
    parser.add_argument(
        "--opportunities",
        default="data/opportunities.sample.json",
        help="Path to normalized opportunity JSON",
    )
    parser.add_argument(
        "--ics",
        default="build/bnb-yield-cruiser-reminders.ics",
        help="Where to write the reminder ICS file",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "sample", "live"),
        default="auto",
        help="Data mode. `auto` prefers live Simple Earn data when SDK and credentials are available.",
    )
    parser.add_argument(
        "--use-wallet-balances",
        action="store_true",
        help="In live mode, try to replace profile balances with wallet balances for the same assets.",
    )
    parser.add_argument(
        "--skip-public-events",
        action="store_true",
        help="Do not try to refresh Launchpool or HODLer opportunities from official Binance announcement pages.",
    )
    args = parser.parse_args()

    profile = load_profile(args.profile)
    try:
        plan = generate_plan(
            profile=profile,
            opportunities_path=args.opportunities,
            mode=args.mode,
            use_wallet_balances=args.use_wallet_balances,
            skip_public_events=args.skip_public_events,
            has_live_credentials=has_live_credentials(),
        )
    except LiveDataUnavailable as exc:
        raise SystemExit(str(exc)) from exc

    print(render_plan(plan))
    if profile.wants_reminders and plan.reminders:
        output = write_ics(plan.reminders, args.ics)
        print("")
        print(f"ICS written to: {output}")


if __name__ == "__main__":
    main()
