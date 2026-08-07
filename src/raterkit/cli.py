"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .probes import run_audit
from .report import inject_readme, render_report, write_demo
from .schema import Config, load_config, load_gold, load_ratings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="raterkit",
        description="Reliability, rogue-rater, drift and leakage diagnostics for labelled data.",
    )
    parser.add_argument("--version", action="version", version=f"raterkit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    rep = sub.add_parser("report", help="audit a ratings file and write a report")
    rep.add_argument("ratings", help="JSONL file, one rating per line")
    rep.add_argument("--gold", help="JSONL file of gold labels")
    rep.add_argument("--config", help="JSON audit configuration")
    rep.add_argument("--out", default="audit", help="output directory")
    rep.add_argument("--fail-on-flags", action="store_true", help="exit 2 when any probe flags")

    demo = sub.add_parser("demo", help="run the eight-project demo")
    demo.add_argument("--out", default="results", help="output directory")

    inj = sub.add_parser("inject-readme", help="refresh the demo table inside a README")
    inj.add_argument("readme")
    inj.add_argument("--results", default="results", help="results directory")

    args = parser.parse_args(argv)

    if args.command == "report":
        ratings = load_ratings(args.ratings)
        gold = load_gold(args.gold) if args.gold else None
        config = load_config(args.config) if args.config else Config()
        audit = run_audit(ratings, gold, config)
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.md").write_text(render_report(audit), encoding="utf-8")
        (out / "report.json").write_text(
            json.dumps(audit.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        flags = audit.flags
        print(f"{len(flags)} flag(s)" + (": " + ", ".join(p.name for p in flags) if flags else ""))
        print(f"wrote {out / 'report.md'} and {out / 'report.json'}")
        if args.fail_on_flags and flags:
            return 2
        return 0

    if args.command == "demo":
        results = write_demo(args.out)
        for row, seed, audit in results:
            flag_text = ", ".join(sorted(f.name for f in audit.flags)) or "none"
            print(f"{row.name:16s} seed {seed:2d}  flags: {flag_text}")
        print(f"wrote {args.out}/table.md, report.md, demo.json and figures/")
        return 0

    if args.command == "inject-readme":
        inject_readme(args.readme, args.results)
        print(f"updated demo table in {args.readme}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
