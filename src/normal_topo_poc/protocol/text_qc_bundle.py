from __future__ import annotations

import hashlib

from normal_topo_poc.protocol.text_lint import lint_text
from normal_topo_poc.utils.size_guard import apply_size_limit, within_limits


_TEMPLATE = """=== Normal_Topo_Poc TEXT_QC_BUNDLE v1 ===
Project: Normal_Topo_Poc
Run: <run_id>  Commit: <short_sha_or_tag>  ConfigDigest: <8-12chars>
Patch: <patch_uid_or_alias>  Provider: <file|sample|prod>  Seed: <int_or_na>
Module: <t01|t02|t03|t04>  ModuleVersion: <semver_or_sha>

Inputs: intersections=<ok|missing>  topo=<ok|missing>  pc=<ok|missing>  isolated=<ok|missing>  laneinfo=<ok|missing>  traj=<ok|missing>
InputMeta: <type/resolution/field_availability_summary>

Params(TopN<=12): <k1=v1; k2=v2; ...>

Metrics(TopN<=10):
- <metric_name_1>: p50=<num> p90=<num> p99=<num> threshold=<num|na> unit=<...>
- <metric_name_2>: p50=<num> p90=<num> p99=<num> threshold=<num|na> unit=<...>

Intervals(binN=<N>):
- type=<enum>  count=<int>  total_len_pct=<num%>
  top3=(<b0>-<b1>, severity=<low|med|high>, len_pct=<%>); (<b0>-<b1>, ...); (<b0>-<b1>, ...)

Breakpoints: [<enum1>, <enum2>, ...]
Errors: [<reason_enum>:<count>, <reason_enum>:<count>, ...]
Notes: <1-3 lines max>
Truncated: <true|false> (reason=<na|size_limit|...>)
=== END ===
"""


def qc_bundle_template() -> str:
    return _TEMPLATE.rstrip("\n")


def _one_line(value: object) -> str:
    text = "na" if value is None else str(value)
    return " ".join(text.replace("\t", " ").splitlines()).strip() or "na"


def _fmt_pct(value: object) -> str:
    if value is None:
        return "na%"
    text = str(value).strip()
    if text.endswith("%"):
        text = text[:-1].strip()
    try:
        number = float(text)
    except Exception:
        return "na%"
    return f"{number:.2f}%"


def _fmt_num(value: object) -> str:
    if value is None:
        return "na"
    try:
        number = float(value)
    except Exception:
        return _one_line(value)
    return f"{number:.6g}"


def _top_dict_items(data: dict[str, object], n: int) -> list[tuple[str, object]]:
    return sorted(data.items(), key=lambda item: item[0])[:n]


def _top_errors(errors: dict[str, int], n: int) -> list[tuple[str, int]]:
    return sorted(errors.items(), key=lambda item: (-int(item[1]), item[0]))[:n]


def _parse_pct(value: str) -> float:
    try:
        return float(str(value).rstrip("%").strip())
    except Exception:
        return 0.0


def _render(payload: dict, truncated: bool, reason: str) -> str:
    project = "Normal_Topo_Poc"
    run_id = _one_line(payload.get("run_id", "na"))
    commit = _one_line(payload.get("commit", "na"))
    config_digest = _one_line(payload.get("config_digest", "na"))
    patch = _one_line(payload.get("patch", "na"))
    provider = _one_line(payload.get("provider", "na"))
    seed = _one_line(payload.get("seed", "na"))
    module = _one_line(payload.get("module", "na"))
    module_version = _one_line(payload.get("module_version", "na"))

    inputs = payload.get("inputs", {}) or {}
    intersections = _one_line(inputs.get("intersections", "missing"))
    topo = _one_line(inputs.get("topo", "missing"))
    pc = _one_line(inputs.get("pc", "missing"))
    isolated = _one_line(inputs.get("isolated", "missing"))
    laneinfo = _one_line(inputs.get("laneinfo", "missing"))
    traj = _one_line(inputs.get("traj", "missing"))
    input_meta = _one_line(payload.get("input_meta", "na"))

    params = payload.get("params", {}) or {}
    params_items = _top_dict_items({str(k): v for k, v in params.items()}, 12)
    params_text = "; ".join([f"{_one_line(k)}={_one_line(v)}" for k, v in params_items]) or "na"

    metrics = list(payload.get("metrics", []) or [])[:10]
    bin_n = int(payload.get("binN", payload.get("bin_n", 1000)) or 1000)
    intervals = payload.get("intervals", []) or []
    breakpoints = list(payload.get("breakpoints", []) or [])[:20]

    errors = payload.get("errors", {}) or {}
    if isinstance(errors, list):
        errors = {str(k): int(v) for k, v in errors}
    error_items = _top_errors({str(k): int(v) for k, v in errors.items()}, 20)
    error_text = ", ".join([f"{_one_line(k)}:{int(v)}" for k, v in error_items]) or "na"

    notes = payload.get("notes", "")
    if isinstance(notes, str):
        note_lines = [notes] if notes.strip() else []
    else:
        note_lines = [str(item) for item in notes]
    note_lines = [_one_line(line) for line in note_lines if str(line).strip()]
    note_lines = note_lines[:3] or ["na"]

    out: list[str] = []
    out.append("=== Normal_Topo_Poc TEXT_QC_BUNDLE v1 ===")
    out.append(f"Project: {project}")
    out.append(f"Run: {run_id}  Commit: {commit}  ConfigDigest: {config_digest}")
    out.append(f"Patch: {patch}  Provider: {provider}  Seed: {seed}")
    out.append(f"Module: {module}  ModuleVersion: {module_version}")
    out.append("")
    out.append(
        "Inputs: "
        f"intersections={intersections}  topo={topo}  pc={pc}  "
        f"isolated={isolated}  laneinfo={laneinfo}  traj={traj}"
    )
    out.append(f"InputMeta: {input_meta}")
    out.append("")
    out.append(f"Params(TopN<=12): {params_text}")
    out.append("")
    out.append("Metrics(TopN<=10):")
    if not metrics:
        out.append("- na: p50=na p90=na p99=na threshold=na unit=na")
    else:
        for metric in metrics:
            name = _one_line(metric.get("name", "na"))
            p50 = _fmt_num(metric.get("p50"))
            p90 = _fmt_num(metric.get("p90"))
            p99 = _fmt_num(metric.get("p99"))
            threshold = _fmt_num(metric.get("threshold"))
            unit = _one_line(metric.get("unit", "na"))
            out.append(f"- {name}: p50={p50} p90={p90} p99={p99} threshold={threshold} unit={unit}")
    out.append("")
    out.append(f"Intervals(binN={bin_n}):")
    if not intervals:
        out.append("- type=na  count=0  total_len_pct=0.00%")
        out.append(
            "  top3=(0-0, severity=low, len_pct=0.00%); "
            "(0-0, severity=low, len_pct=0.00%); "
            "(0-0, severity=low, len_pct=0.00%)"
        )
    else:
        for group in intervals:
            interval_type = _one_line(group.get("type", "na"))
            count = int(group.get("count", 0) or 0)
            total_len_pct = _fmt_pct(group.get("total_len_pct", 0.0))
            out.append(f"- type={interval_type}  count={count}  total_len_pct={total_len_pct}")
            top3 = list(group.get("top3", []) or [])[:3]
            parts = []
            for item in top3:
                b0 = int(item.get("b0", 0) or 0)
                b1 = int(item.get("b1", 0) or 0)
                severity = _one_line(item.get("severity", "low"))
                len_pct = _fmt_pct(item.get("len_pct", 0.0))
                parts.append(f"({b0}-{b1}, severity={severity}, len_pct={len_pct})")
            while len(parts) < 3:
                parts.append("(0-0, severity=low, len_pct=0.00%)")
            out.append("  top3=" + "; ".join(parts))
    out.append("")
    out.append("Breakpoints: [" + ", ".join([_one_line(item) for item in breakpoints]) + "]")
    out.append(f"Errors: [{error_text}]")
    if len(note_lines) == 1:
        out.append(f"Notes: {note_lines[0]}")
    else:
        out.append(f"Notes: {note_lines[0]}")
        for extra in note_lines[1:]:
            out.append(f"Notes: {extra}")
    out.append(f"Truncated: {'true' if truncated else 'false'} (reason={reason})")
    out.append("=== END ===")
    return "\n".join(out) + "\n"


def build_text_qc_bundle(payload: dict) -> str:
    full = _render(payload, truncated=False, reason="na")
    if within_limits(full):
        ok, violations = lint_text(full)
        if not ok:
            raise ValueError(f"lint failed: {violations}")
        return full.rstrip("\n")

    trimmed = dict(payload)
    intervals = list(payload.get("intervals", []) or [])
    trimmed["intervals"] = sorted(
        intervals,
        key=lambda item: -_parse_pct(str(item.get("total_len_pct", "0%"))),
    )[:3]

    errors = payload.get("errors", {}) or {}
    if isinstance(errors, list):
        errors = {str(k): int(v) for k, v in errors}
    trimmed["errors"] = {k: v for k, v in _top_errors({str(k): int(v) for k, v in errors.items()}, 3)}
    trimmed["notes"] = ["Truncated due to size_limit; showing Top metrics/intervals/errors only."]

    reduced = _render(trimmed, truncated=True, reason="size_limit")
    if not within_limits(reduced):
        reduced, _truncated, _reason = apply_size_limit(reduced)

    ok, violations = lint_text(reduced)
    if not ok:
        raise ValueError(f"lint failed: {violations}")
    return reduced.rstrip("\n")


def build_demo_bundle() -> str:
    digest = hashlib.sha1(b"demo_config").hexdigest()[:10]
    intervals = []
    for idx in range(80):
        intervals.append(
            {
                "type": f"demo_type_{idx:02d}",
                "count": 1 + (idx % 7),
                "total_len_pct": f"{0.10 + (idx % 10) * 0.11:.2f}%",
                "top3": [
                    {"b0": idx, "b1": idx + 1, "severity": "low", "len_pct": "0.10%"},
                    {"b0": idx + 2, "b1": idx + 3, "severity": "med", "len_pct": "0.08%"},
                    {"b0": idx + 4, "b1": idx + 5, "severity": "high", "len_pct": "0.06%"},
                ],
            }
        )

    payload = {
        "run_id": "demo_run_01",
        "commit": "demo",
        "config_digest": digest,
        "patch": "patch_demo_001",
        "provider": "sample",
        "seed": 123,
        "module": "t01",
        "module_version": "demo",
        "inputs": {
            "intersections": "ok",
            "topo": "ok",
            "pc": "ok",
            "isolated": "ok",
            "laneinfo": "missing",
            "traj": "missing",
        },
        "input_meta": "demo_input; ordinary_road; fields=ok",
        "params": {
            "binN": 1000,
            "auto_fix_enabled": True,
            "manual_breakpoint_top_n": 20,
        },
        "metrics": [
            {"name": "intersection_pass_rate", "p50": 0.96, "p90": 0.98, "p99": 0.99, "threshold": 0.95, "unit": "ratio"},
            {"name": "auto_fix_ratio", "p50": 0.04, "p90": 0.08, "p99": 0.12, "threshold": 0.10, "unit": "ratio"},
        ],
        "binN": 1000,
        "intervals": intervals,
        "breakpoints": ["manual_review", "missing_laneinfo"],
        "errors": {"E_NEED_REVIEW": 2, "E_SIGNAL_MISSING": 1},
        "notes": ["demo bundle; triggers truncation"],
    }
    return build_text_qc_bundle(payload)
