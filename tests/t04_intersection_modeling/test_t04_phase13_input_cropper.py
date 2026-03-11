from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from normal_topo_poc.modules.t04_intersection_modeling.input_cropper import (
    export_t04_cropped_inputs_from_geojson_files,
    run_t04_cropped_inputs_from_dataset,
)


def _node(node_id: int, x: float, y: float, *, mainid: int, kind: int = 4) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(x), float(y)]},
        "properties": {"id": int(node_id), "mainid": int(mainid), "Kind": int(kind)},
    }


def _road(
    road_id: str,
    coords: list[tuple[float, float]],
    *,
    snodeid: int,
    enodeid: int,
    direction: int = 1,
) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[float(x), float(y)] for x, y in coords]},
        "properties": {
            "road_id": road_id,
            "snodeid": int(snodeid),
            "enodeid": int(enodeid),
            "direction": int(direction),
        },
    }


def _feature_collection(features: list[dict]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": features,
    }


def _write_geojson(path: Path, features: list[dict]) -> Path:
    path.write_text(json.dumps(_feature_collection(features), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_dataset_dir(path: Path, *, node_features: list[dict], road_features: list[dict], vector_layout: bool = True) -> Path:
    root = path / "Vector" if vector_layout else path
    root.mkdir(parents=True, exist_ok=True)
    _write_geojson(root / "RCSDNode.geojson", node_features)
    _write_geojson(root / "RCSDRoad.geojson", road_features)
    return path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_dir = _repo_root() / "src"
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(src_dir) if not existing else str(src_dir) + os.pathsep + existing
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "normal_topo_poc.modules.t04_intersection_modeling.cli",
            *args,
        ],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_phase13_export_cropped_inputs_from_geojson_files_writes_visual_files(tmp_path: Path) -> None:
    node_path = _write_geojson(
        tmp_path / "RCSDNode.geojson",
        [
            _node(1, 0.0, 0.0, mainid=100),
            _node(2, 0.0, 10.0, mainid=100),
            _node(3, 100.0, 100.0, mainid=200),
        ],
    )
    road_path = _write_geojson(
        tmp_path / "RCSDRoad.geojson",
        [
            _road("south", [(0.0, 0.0), (0.0, -100.0)], snodeid=1, enodeid=101),
            _road("north", [(0.0, 10.0), (0.0, 120.0)], snodeid=2, enodeid=102),
            _road("far", [(100.0, 100.0), (120.0, 100.0)], snodeid=3, enodeid=103),
        ],
    )
    output_dir = tmp_path / "crop_single"
    result = export_t04_cropped_inputs_from_geojson_files(
        node_geojson_path=node_path,
        road_geojson_path=road_path,
        mainid=100,
        output_dir=output_dir,
        crop_buffer_m=5.0,
    )

    assert set(result.written_files) == {
        "RCSDNode.geojson",
        "RCSDRoad.geojson",
        "selected_mainid_nodes.geojson",
        "crop_bbox.geojson",
        "crop_summary.json",
        "crop_summary.txt",
    }

    summary = json.loads((output_dir / "crop_summary.json").read_text(encoding="utf-8"))
    assert summary["mainid"] == 100
    assert summary["cropped_node_count"] == 2
    assert summary["cropped_road_ids"] == ["south", "north"]

    road_payload = json.loads((output_dir / "RCSDRoad.geojson").read_text(encoding="utf-8"))
    assert len(road_payload["features"]) == 2
    for feature in road_payload["features"]:
        assert feature["geometry"]["type"] == "LineString"
        for _x, y in feature["geometry"]["coordinates"]:
            assert -5.0 <= float(y) <= 15.0


def test_phase13_crop_dataset_runner_writes_per_mainnodeid_outputs(tmp_path: Path) -> None:
    dataset_dir = _write_dataset_dir(
        tmp_path / "dataset",
        node_features=[
            _node(1, 0.0, 0.0, mainid=100),
            _node(2, 0.0, 10.0, mainid=100),
            _node(11, 50.0, 0.0, mainid=200),
            _node(12, 50.0, 10.0, mainid=200),
        ],
        road_features=[
            _road("south_a", [(0.0, 0.0), (0.0, -50.0)], snodeid=1, enodeid=101),
            _road("north_a", [(0.0, 10.0), (0.0, 60.0)], snodeid=2, enodeid=102),
            _road("south_b", [(50.0, 0.0), (50.0, -50.0)], snodeid=11, enodeid=201),
            _road("north_b", [(50.0, 10.0), (50.0, 60.0)], snodeid=12, enodeid=202),
        ],
    )
    output_root = tmp_path / "crop_dataset_out"
    result = run_t04_cropped_inputs_from_dataset(
        dataset_dir=dataset_dir,
        mainnodeids=[100, 200, 999999],
        output_root=output_root,
        crop_buffer_m=5.0,
    )

    status_map = {item.mainnodeid: item for item in result.items}
    assert status_map[100].status == "success"
    assert status_map[200].status == "success"
    assert status_map[999999].status == "error"
    assert (output_root / "mainnodeid_100" / "RCSDRoad.geojson").exists()
    assert (output_root / "mainnodeid_200" / "crop_summary.json").exists()
    assert (output_root / "mainnodeid_999999" / "error.txt").exists()
    assert Path(result.manifest_path or "").exists()
    assert Path(result.summary_path or "").exists()


def test_phase13_cli_crop_inputs_dataset_mode_smoke(tmp_path: Path) -> None:
    dataset_dir = _write_dataset_dir(
        tmp_path / "dataset_cli",
        node_features=[
            _node(1, 0.0, 0.0, mainid=100),
            _node(2, 0.0, 10.0, mainid=100),
        ],
        road_features=[
            _road("south", [(0.0, 0.0), (0.0, -50.0)], snodeid=1, enodeid=101),
            _road("north", [(0.0, 10.0), (0.0, 60.0)], snodeid=2, enodeid=102),
        ],
    )
    output_root = tmp_path / "crop_cli_out"
    proc = _run_cli(
        "--dataset-dir",
        str(dataset_dir),
        "--mainnodeid",
        "100",
        "--crop-inputs-only",
        "--crop-buffer-m",
        "5",
        "--output-dir",
        str(output_root),
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["mode"] == "cropped_inputs_dataset"
    assert payload["mainnodeids"] == [100]
    assert (output_root / "mainnodeid_100" / "RCSDNode.geojson").exists()
