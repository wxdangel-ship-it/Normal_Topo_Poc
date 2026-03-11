from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from shapely.geometry import GeometryCollection, LineString, MultiLineString, box, mapping

from .geojson_io import (
    discover_geojson_dataset_inputs,
    load_geojson_feature_collection,
    parse_mainid_values,
    select_single_intersection_node_features,
)
from .normalize import normalize_node_features, normalize_road_features

_NON_ALNUM = re.compile(r"[^A-Za-z0-9._-]+")
DEFAULT_CROP_BUFFER_M = 80.0


@dataclass(frozen=True)
class T04CroppedInputResult:
    mainid: Any
    available_mainids: tuple[Any, ...]
    crop_buffer_m: float
    crop_bounds: tuple[float, float, float, float]
    selected_mainid_node_features: tuple[dict[str, Any], ...]
    cropped_node_features: tuple[dict[str, Any], ...]
    cropped_road_features: tuple[dict[str, Any], ...]
    bbox_feature: dict[str, Any]
    output_dir: str | None = None
    written_files: dict[str, str] = field(default_factory=dict)
    summary_path: str | None = None
    summary_text_path: str | None = None


@dataclass(frozen=True)
class T04CroppedInputDatasetItem:
    mainnodeid: Any
    status: str
    result: T04CroppedInputResult | None
    error: str | None = None
    output_dir: str | None = None
    written_files: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class T04CroppedInputDatasetResult:
    dataset_dir: str
    node_geojson_path: str
    road_geojson_path: str
    mainnodeids: tuple[Any, ...]
    crop_buffer_m: float
    items: tuple[T04CroppedInputDatasetItem, ...]
    manifest_path: str | None = None
    summary_path: str | None = None


def build_t04_cropped_inputs(
    *,
    node_features: list[dict[str, Any]],
    road_features: list[dict[str, Any]],
    mainid: Any | None = None,
    crop_buffer_m: float = DEFAULT_CROP_BUFFER_M,
) -> T04CroppedInputResult:
    if crop_buffer_m < 0:
        raise ValueError("crop_buffer_m_must_be_non_negative")

    selected_node_features, selected_mainid, available_mainids = select_single_intersection_node_features(
        node_features,
        mainid=mainid,
    )
    selected_nodes = normalize_node_features(selected_node_features)
    if not selected_nodes:
        raise ValueError(f"selected_mainid_has_no_nodes:{selected_mainid}")

    minx = min(node.point.x for node in selected_nodes) - float(crop_buffer_m)
    miny = min(node.point.y for node in selected_nodes) - float(crop_buffer_m)
    maxx = max(node.point.x for node in selected_nodes) + float(crop_buffer_m)
    maxy = max(node.point.y for node in selected_nodes) + float(crop_buffer_m)
    crop_box = box(minx, miny, maxx, maxy)

    normalized_nodes = normalize_node_features(node_features)
    cropped_node_features = tuple(
        _copy_feature(feature)
        for feature, normalized in zip(node_features, normalized_nodes)
        if normalized.point.intersects(crop_box)
    )

    selected_node_ids = {node.node_id for node in selected_nodes}
    normalized_roads = normalize_road_features(road_features)
    cropped_roads: list[dict[str, Any]] = []
    for feature, normalized in zip(road_features, normalized_roads):
        if normalized.snodeid not in selected_node_ids and normalized.enodeid not in selected_node_ids:
            continue
        if not normalized.line.intersects(crop_box):
            continue
        clipped_geometry = _clip_line_geometry(normalized.line.intersection(crop_box))
        if clipped_geometry is None:
            continue
        feature_copy = _copy_feature(feature)
        feature_copy["geometry"] = mapping(clipped_geometry)
        cropped_roads.append(feature_copy)

    bbox_feature = {
        "type": "Feature",
        "geometry": mapping(crop_box),
        "properties": {
            "mainid": selected_mainid,
            "crop_buffer_m": float(crop_buffer_m),
        },
    }

    return T04CroppedInputResult(
        mainid=selected_mainid,
        available_mainids=tuple(available_mainids),
        crop_buffer_m=float(crop_buffer_m),
        crop_bounds=(float(minx), float(miny), float(maxx), float(maxy)),
        selected_mainid_node_features=tuple(_copy_feature(feature) for feature in selected_node_features),
        cropped_node_features=cropped_node_features,
        cropped_road_features=tuple(cropped_roads),
        bbox_feature=bbox_feature,
    )


def write_t04_cropped_inputs(
    result: T04CroppedInputResult,
    output_dir: str | Path,
) -> T04CroppedInputResult:
    resolved = Path(output_dir)
    resolved.mkdir(parents=True, exist_ok=True)

    node_path = resolved / "RCSDNode.geojson"
    road_path = resolved / "RCSDRoad.geojson"
    selected_node_path = resolved / "selected_mainid_nodes.geojson"
    bbox_path = resolved / "crop_bbox.geojson"
    summary_path = resolved / "crop_summary.json"
    summary_text_path = resolved / "crop_summary.txt"

    node_path.write_text(_feature_collection_text(result.cropped_node_features), encoding="utf-8")
    road_path.write_text(_feature_collection_text(result.cropped_road_features), encoding="utf-8")
    selected_node_path.write_text(_feature_collection_text(result.selected_mainid_node_features), encoding="utf-8")
    bbox_path.write_text(_feature_collection_text((result.bbox_feature,)), encoding="utf-8")

    summary_payload = build_t04_cropped_input_summary(result)
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_text_path.write_text(_build_t04_cropped_input_summary_text(result), encoding="utf-8")

    return replace(
        result,
        output_dir=str(resolved),
        written_files={
            "RCSDNode.geojson": str(node_path),
            "RCSDRoad.geojson": str(road_path),
            "selected_mainid_nodes.geojson": str(selected_node_path),
            "crop_bbox.geojson": str(bbox_path),
            "crop_summary.json": str(summary_path),
            "crop_summary.txt": str(summary_text_path),
        },
        summary_path=str(summary_path),
        summary_text_path=str(summary_text_path),
    )


def export_t04_cropped_inputs_from_geojson_files(
    *,
    node_geojson_path: str | Path,
    road_geojson_path: str | Path,
    mainid: Any | None = None,
    output_dir: str | Path | None = None,
    crop_buffer_m: float = DEFAULT_CROP_BUFFER_M,
) -> T04CroppedInputResult:
    result = build_t04_cropped_inputs(
        node_features=load_geojson_feature_collection(node_geojson_path),
        road_features=load_geojson_feature_collection(road_geojson_path),
        mainid=mainid,
        crop_buffer_m=crop_buffer_m,
    )
    if output_dir is not None:
        return write_t04_cropped_inputs(result, output_dir)
    return result


def run_t04_cropped_inputs_from_dataset(
    *,
    dataset_dir: str | Path,
    mainnodeids: list[Any] | tuple[Any, ...] | None,
    output_root: str | Path,
    crop_buffer_m: float = DEFAULT_CROP_BUFFER_M,
) -> T04CroppedInputDatasetResult:
    parsed_mainnodeids = parse_mainid_values(mainnodeids)
    if not parsed_mainnodeids:
        raise ValueError("crop_dataset_mode_requires_mainnodeids")

    node_geojson_path, road_geojson_path = discover_geojson_dataset_inputs(dataset_dir)
    resolved_output_root = Path(output_root)
    resolved_output_root.mkdir(parents=True, exist_ok=True)

    items: list[T04CroppedInputDatasetItem] = []
    for mainnodeid in parsed_mainnodeids:
        item_output_dir = resolved_output_root / _mainnodeid_dir_name(mainnodeid)
        try:
            result = export_t04_cropped_inputs_from_geojson_files(
                node_geojson_path=node_geojson_path,
                road_geojson_path=road_geojson_path,
                mainid=mainnodeid,
                output_dir=item_output_dir,
                crop_buffer_m=crop_buffer_m,
            )
        except Exception as exc:
            item_output_dir.mkdir(parents=True, exist_ok=True)
            error_path = item_output_dir / "error.txt"
            error_path.write_text(str(exc) + "\n", encoding="utf-8")
            items.append(
                T04CroppedInputDatasetItem(
                    mainnodeid=mainnodeid,
                    status="error",
                    result=None,
                    error=str(exc),
                    output_dir=str(item_output_dir),
                    written_files={"error.txt": str(error_path)},
                )
            )
            continue
        items.append(
            T04CroppedInputDatasetItem(
                mainnodeid=mainnodeid,
                status="success",
                result=result,
                output_dir=str(item_output_dir),
                written_files=result.written_files,
            )
        )

    dataset_result = T04CroppedInputDatasetResult(
        dataset_dir=str(Path(dataset_dir)),
        node_geojson_path=str(node_geojson_path),
        road_geojson_path=str(road_geojson_path),
        mainnodeids=parsed_mainnodeids,
        crop_buffer_m=float(crop_buffer_m),
        items=tuple(items),
    )
    return write_t04_cropped_input_dataset_result(dataset_result, resolved_output_root)


def write_t04_cropped_input_dataset_result(
    result: T04CroppedInputDatasetResult,
    output_root: str | Path,
) -> T04CroppedInputDatasetResult:
    resolved = Path(output_root)
    resolved.mkdir(parents=True, exist_ok=True)
    manifest_path = resolved / "manifest.json"
    summary_path = resolved / "summary.txt"
    manifest_path.write_text(
        json.dumps(build_t04_cropped_input_dataset_summary(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary_path.write_text(_build_t04_cropped_input_dataset_summary_text(result), encoding="utf-8")
    return replace(result, manifest_path=str(manifest_path), summary_path=str(summary_path))


def build_t04_cropped_input_summary(result: T04CroppedInputResult) -> dict[str, Any]:
    selected_nodes = normalize_node_features(result.selected_mainid_node_features)
    cropped_nodes = normalize_node_features(result.cropped_node_features)
    cropped_roads = normalize_road_features(result.cropped_road_features)
    return {
        "mainid": result.mainid,
        "available_mainids": list(result.available_mainids),
        "crop_buffer_m": result.crop_buffer_m,
        "crop_bounds": list(result.crop_bounds),
        "selected_mainid_node_count": len(result.selected_mainid_node_features),
        "cropped_node_count": len(result.cropped_node_features),
        "cropped_road_count": len(result.cropped_road_features),
        "selected_mainid_node_ids": [node.node_id for node in selected_nodes],
        "cropped_node_ids": [node.node_id for node in cropped_nodes],
        "cropped_road_ids": [road.road_id for road in cropped_roads],
        "output_dir": result.output_dir,
        "written_files": dict(result.written_files),
    }


def build_t04_cropped_input_dataset_summary(result: T04CroppedInputDatasetResult) -> dict[str, Any]:
    return {
        "dataset_dir": result.dataset_dir,
        "node_geojson_path": result.node_geojson_path,
        "road_geojson_path": result.road_geojson_path,
        "mainnodeids": list(result.mainnodeids),
        "crop_buffer_m": result.crop_buffer_m,
        "items": [
            {
                "mainnodeid": item.mainnodeid,
                "status": item.status,
                "error": item.error,
                "output_dir": item.output_dir,
                "crop_summary": build_t04_cropped_input_summary(item.result) if item.result is not None else None,
            }
            for item in result.items
        ],
        "manifest_path": result.manifest_path,
        "summary_path": result.summary_path,
    }


def _clip_line_geometry(geometry: Any) -> LineString | MultiLineString | None:
    if geometry.is_empty:
        return None
    if isinstance(geometry, LineString):
        return geometry
    if isinstance(geometry, MultiLineString):
        lines = [line for line in geometry.geoms if not line.is_empty and len(line.coords) >= 2]
        if not lines:
            return None
        if len(lines) == 1:
            return lines[0]
        return MultiLineString(lines)
    if isinstance(geometry, GeometryCollection):
        lines: list[LineString] = []
        for item in geometry.geoms:
            clipped = _clip_line_geometry(item)
            if clipped is None:
                continue
            if isinstance(clipped, LineString):
                lines.append(clipped)
            else:
                lines.extend(list(clipped.geoms))
        if not lines:
            return None
        if len(lines) == 1:
            return lines[0]
        return MultiLineString(lines)
    return None


def _feature_collection_text(features: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> str:
    payload = {
        "type": "FeatureCollection",
        "features": list(features),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _copy_feature(feature: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(feature)


def _build_t04_cropped_input_summary_text(result: T04CroppedInputResult) -> str:
    payload = build_t04_cropped_input_summary(result)
    lines = [
        f"mainid: {payload['mainid']}",
        f"available_mainids: {','.join(str(item) for item in payload['available_mainids'])}",
        f"crop_buffer_m: {payload['crop_buffer_m']}",
        f"crop_bounds: {payload['crop_bounds']}",
        f"selected_mainid_node_count: {payload['selected_mainid_node_count']}",
        f"cropped_node_count: {payload['cropped_node_count']}",
        f"cropped_road_count: {payload['cropped_road_count']}",
        f"selected_mainid_node_ids: {payload['selected_mainid_node_ids']}",
        f"cropped_node_ids: {payload['cropped_node_ids']}",
        f"cropped_road_ids: {payload['cropped_road_ids']}",
    ]
    if result.output_dir:
        lines.append(f"output_dir: {result.output_dir}")
    return "\n".join(lines) + "\n"


def _build_t04_cropped_input_dataset_summary_text(result: T04CroppedInputDatasetResult) -> str:
    success_count = sum(1 for item in result.items if item.status == "success")
    error_count = sum(1 for item in result.items if item.status == "error")
    lines = [
        f"dataset_dir: {result.dataset_dir}",
        f"node_geojson_path: {result.node_geojson_path}",
        f"road_geojson_path: {result.road_geojson_path}",
        f"mainnodeid_count: {len(result.mainnodeids)}",
        f"crop_buffer_m: {result.crop_buffer_m}",
        f"success_count: {success_count}",
        f"error_count: {error_count}",
        "items:",
    ]
    for item in result.items:
        line = f"  - mainnodeid={item.mainnodeid} status={item.status}"
        if item.output_dir:
            line += f" output_dir={item.output_dir}"
        if item.error:
            line += f" error={item.error}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def _mainnodeid_dir_name(mainnodeid: Any) -> str:
    raw = _NON_ALNUM.sub("_", str(mainnodeid)).strip("_")
    if not raw:
        raw = "unknown"
    return f"mainnodeid_{raw}"


__all__ = [
    "DEFAULT_CROP_BUFFER_M",
    "T04CroppedInputDatasetItem",
    "T04CroppedInputDatasetResult",
    "T04CroppedInputResult",
    "build_t04_cropped_input_dataset_summary",
    "build_t04_cropped_input_summary",
    "build_t04_cropped_inputs",
    "export_t04_cropped_inputs_from_geojson_files",
    "run_t04_cropped_inputs_from_dataset",
    "write_t04_cropped_input_dataset_result",
    "write_t04_cropped_inputs",
]
