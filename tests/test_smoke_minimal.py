from __future__ import annotations

from normal_topo_poc.cli import main


def test_doctor_smoke() -> None:
    assert main(["doctor"]) == 0


def test_qc_demo_smoke() -> None:
    assert main(["qc-demo"]) == 0
