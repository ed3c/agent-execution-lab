from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from agent_execution_lab.lab06 import render_summary, run_suite


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    report = run_suite(args.seed)
    evidence_dir = ROOT / "evidence" / "experiments"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    json_path = evidence_dir / f"lab06-seed-{args.seed}.json"
    md_path = evidence_dir / f"lab06-seed-{args.seed}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = render_summary(report)
    md_path.write_text(summary, encoding="utf-8")
    print(summary)
    print(f"JSON: {json_path}")
    return 0 if report["suite_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
