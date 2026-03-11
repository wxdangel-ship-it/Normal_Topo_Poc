from __future__ import annotations

import argparse
import sys
from pathlib import Path

from normal_topo_poc.protocol.text_lint import lint_text
from normal_topo_poc.protocol.text_qc_bundle import build_demo_bundle, qc_bundle_template


REQUIRED_DOCS = [
    "SPEC.md",
    "docs/CODEX_START_HERE.md",
    "docs/PROJECT_BRIEF.md",
    "docs/AGENT_PLAYBOOK.md",
    "docs/CODEX_GUARDRAILS.md",
    "docs/ARTIFACT_PROTOCOL.md",
    "docs/WORKSPACE_SETUP.md",
]


def _find_repo_root(start: Path) -> Path | None:
    p = start.resolve()
    for candidate in [p, *p.parents]:
        if (candidate / "SPEC.md").is_file() and (candidate / "docs").is_dir():
            return candidate
    return None


def _cmd_doctor(_args: argparse.Namespace) -> int:
    root = _find_repo_root(Path.cwd())
    print("Normal_Topo_Poc doctor")

    if root is None:
        print("RepoRoot: NOT_FOUND (need SPEC.md + docs/)")
        return 1

    print("RepoRoot: OK")

    missing = [rel for rel in REQUIRED_DOCS if not (root / rel).exists()]
    if missing:
        print("Docs: MISSING")
        for rel in missing:
            print(f"- {rel}")
        return 1

    print("Docs: OK")
    print(f"Python: {sys.version.split()[0]}")

    try:
        import normal_topo_poc as pkg

        print(f"PackageImport: OK (version={pkg.__version__})")
    except Exception:
        print("PackageImport: FAIL")
        return 1

    return 0


def _cmd_qc_template(_args: argparse.Namespace) -> int:
    print(qc_bundle_template())
    return 0


def _cmd_qc_demo(_args: argparse.Namespace) -> int:
    print(build_demo_bundle())
    return 0


def _cmd_lint_text(args: argparse.Namespace) -> int:
    text = args.text if args.text is not None else sys.stdin.read()
    if not text.strip():
        print("No input text provided.", file=sys.stderr)
        return 2

    ok, violations = lint_text(text)
    if ok:
        print("OK")
        for violation in violations:
            if violation.startswith("LONG_LINE"):
                print(f"- {violation}")
        return 0

    print("NOT_PASTEABLE")
    for violation in violations:
        print(f"- {violation}")
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="normal_topo_poc")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_doctor = sub.add_parser("doctor", help="Check repo/docs/python environment.")
    p_doctor.set_defaults(func=_cmd_doctor)

    p_tpl = sub.add_parser("qc-template", help="Print TEXT_QC_BUNDLE v1 template.")
    p_tpl.set_defaults(func=_cmd_qc_template)

    p_demo = sub.add_parser("qc-demo", help="Print a demo TEXT_QC_BUNDLE (pasteable + truncated).")
    p_demo.set_defaults(func=_cmd_qc_demo)

    p_lint = sub.add_parser("lint-text", help="Check text pasteability (size/lines/long lines).")
    p_lint.add_argument("--text", help="Text to lint (if omitted, read stdin).")
    p_lint.set_defaults(func=_cmd_lint_text)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        if isinstance(exc, ValueError) and str(exc):
            print(f"ERROR: {exc}", file=sys.stderr)
        else:
            print(f"ERROR: {type(exc).__name__}", file=sys.stderr)
        return 1
