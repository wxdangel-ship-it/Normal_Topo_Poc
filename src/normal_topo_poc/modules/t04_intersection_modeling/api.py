from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .geojson_io import (
    discover_patch_dir_inputs,
    list_available_mainids,
    load_geojson_feature_collection,
    select_single_intersection_node_features,
)
from .models import IntersectionBundle, MovementDecision
from .serialization import build_movement_matrix, serialize_bundle, serialize_movement_result
from .t04_2_builder import build_intersection_bundles_with_manual_overrides
from .t04_3_rules import evaluate_bundle


@dataclass(frozen=True)
class T04RunResult:
    bundle: IntersectionBundle
    decisions: tuple[MovementDecision, ...]
    serialized_bundle: dict[str, Any]
    movement_results: tuple[dict[str, Any], ...]
    matrix_view: dict[str, Any]


@dataclass(frozen=True)
class T04PatchRunItem:
    mainid: Any
    status: str
    result: T04RunResult | None
    error: str | None = None
    output_dir: str | None = None
    written_files: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class T04PatchBatchRunResult:
    patch_dir: str
    node_geojson_path: str
    road_geojson_path: str
    mainids: tuple[Any, ...]
    items: tuple[T04PatchRunItem, ...]
    manifest_path: str | None = None
    summary_path: str | None = None


def run_t04_manual_mode(
    *,
    node_features: list[dict[str, Any]],
    road_features: list[dict[str, Any]],
    manual_override_source: str | Path | dict[str, Any] | None = None,
    source_type: str = "real",
    approach_overrides: dict[str, dict[str, Any]] | None = None,
) -> list[T04RunResult]:
    bundles = build_intersection_bundles_with_manual_overrides(
        node_features=node_features,
        road_features=road_features,
        manual_override_source=manual_override_source,
        source_type=source_type,
        approach_overrides=approach_overrides,
    )
    results: list[T04RunResult] = []
    for bundle in bundles:
        decisions = tuple(evaluate_bundle(bundle))
        movement_results = tuple(
            serialize_movement_result(candidate, decision)
            for candidate, decision in zip(bundle.movements, decisions, strict=True)
        )
        results.append(
            T04RunResult(
                bundle=bundle,
                decisions=decisions,
                serialized_bundle=serialize_bundle(bundle),
                movement_results=movement_results,
                matrix_view=build_movement_matrix(bundle, decisions),
            )
        )
    return results


def run_t04_single_intersection_manual_mode(
    *,
    node_features: list[dict[str, Any]],
    road_features: list[dict[str, Any]],
    manual_override_source: str | Path | dict[str, Any] | None = None,
    source_type: str = "real",
    approach_overrides: dict[str, dict[str, Any]] | None = None,
) -> T04RunResult:
    results = run_t04_manual_mode(
        node_features=node_features,
        road_features=road_features,
        manual_override_source=manual_override_source,
        source_type=source_type,
        approach_overrides=approach_overrides,
    )
    if len(results) != 1:
        raise ValueError(f"expected_single_intersection_result:{len(results)}")
    return results[0]


def run_t04_single_intersection_from_geojson_files(
    *,
    node_geojson_path: str | Path,
    road_geojson_path: str | Path,
    manual_override_source: str | Path | dict[str, Any] | None = None,
    source_type: str = "real",
    approach_overrides: dict[str, dict[str, Any]] | None = None,
    mainid: Any | None = None,
) -> T04RunResult:
    node_features = load_geojson_feature_collection(node_geojson_path)
    road_features = load_geojson_feature_collection(road_geojson_path)
    selected_node_features, _selected_mainid, _available_mainids = select_single_intersection_node_features(
        node_features,
        mainid=mainid,
    )
    return run_t04_single_intersection_manual_mode(
        node_features=selected_node_features,
        road_features=road_features,
        manual_override_source=manual_override_source,
        source_type=source_type,
        approach_overrides=approach_overrides,
    )


def run_t04_all_intersections_from_geojson_files(
    *,
    node_geojson_path: str | Path,
    road_geojson_path: str | Path,
    manual_override_source: str | Path | dict[str, Any] | None = None,
    source_type: str = "real",
    approach_overrides: dict[str, dict[str, Any]] | None = None,
    output_root: str | Path | None = None,
    include_catalog: bool = False,
    include_override_template: bool = False,
    include_review: bool = False,
) -> T04PatchBatchRunResult:
    node_features = load_geojson_feature_collection(node_geojson_path)
    road_features = load_geojson_feature_collection(road_geojson_path)
    mainids = tuple(list_available_mainids(node_features))

    items: list[T04PatchRunItem] = []
    for mainid in mainids:
        try:
            selected_node_features, _selected_mainid, _available_mainids = select_single_intersection_node_features(
                node_features,
                mainid=mainid,
            )
            result = run_t04_single_intersection_manual_mode(
                node_features=selected_node_features,
                road_features=road_features,
                manual_override_source=manual_override_source,
                source_type=source_type,
                approach_overrides=approach_overrides,
            )
        except Exception as exc:
            items.append(
                T04PatchRunItem(
                    mainid=mainid,
                    status="error",
                    result=None,
                    error=str(exc),
                )
            )
            continue
        items.append(
            T04PatchRunItem(
                mainid=mainid,
                status="success",
                result=result,
            )
        )

    batch_result = T04PatchBatchRunResult(
        patch_dir=str(Path(node_geojson_path).parent),
        node_geojson_path=str(Path(node_geojson_path)),
        road_geojson_path=str(Path(road_geojson_path)),
        mainids=mainids,
        items=tuple(items),
    )
    if output_root is not None:
        from .writer import write_t04_patch_batch_result

        batch_result = write_t04_patch_batch_result(
            batch_result,
            output_root,
            include_catalog=include_catalog,
            include_override_template=include_override_template,
            include_review=include_review,
        )
    return batch_result


def run_t04_single_intersection_from_patch_dir(
    *,
    patch_dir: str | Path,
    mainid: Any | None = None,
    manual_override_source: str | Path | dict[str, Any] | None = None,
    source_type: str = "real",
    approach_overrides: dict[str, dict[str, Any]] | None = None,
    output_dir: str | Path | None = None,
    include_catalog: bool = False,
    include_override_template: bool = False,
    include_review: bool = False,
) -> T04RunResult:
    node_geojson_path, road_geojson_path = discover_patch_dir_inputs(patch_dir)
    result = run_t04_single_intersection_from_geojson_files(
        node_geojson_path=node_geojson_path,
        road_geojson_path=road_geojson_path,
        manual_override_source=manual_override_source,
        source_type=source_type,
        approach_overrides=approach_overrides,
        mainid=mainid,
    )
    if output_dir is not None:
        from .writer import write_t04_run_result

        write_t04_run_result(
            result,
            output_dir,
            include_catalog=include_catalog,
            include_override_template=include_override_template,
            include_review=include_review,
        )
    return result


def run_t04_all_intersections_from_patch_dir(
    *,
    patch_dir: str | Path,
    manual_override_source: str | Path | dict[str, Any] | None = None,
    source_type: str = "real",
    approach_overrides: dict[str, dict[str, Any]] | None = None,
    output_root: str | Path | None = None,
    include_catalog: bool = False,
    include_override_template: bool = False,
    include_review: bool = False,
) -> T04PatchBatchRunResult:
    node_geojson_path, road_geojson_path = discover_patch_dir_inputs(patch_dir)
    batch_result = run_t04_all_intersections_from_geojson_files(
        node_geojson_path=node_geojson_path,
        road_geojson_path=road_geojson_path,
        manual_override_source=manual_override_source,
        source_type=source_type,
        approach_overrides=approach_overrides,
        output_root=output_root,
        include_catalog=include_catalog,
        include_override_template=include_override_template,
        include_review=include_review,
    )
    return replace(batch_result, patch_dir=str(Path(patch_dir)))


def build_t04_patch_run_summary(batch_result: T04PatchBatchRunResult) -> dict[str, Any]:
    return {
        "patch_dir": batch_result.patch_dir,
        "mainids": [item.mainid for item in batch_result.items],
        "runs": [
            {
                "mainid": item.mainid,
                "status": item.status,
                "output_dir": item.output_dir,
                "error": item.error,
                "intersection_id": item.result.bundle.intersection.intersection_id if item.result else None,
                "movement_count": len(item.result.decisions) if item.result else None,
            }
            for item in batch_result.items
        ],
        "manifest_path": batch_result.manifest_path,
        "summary_path": batch_result.summary_path,
    }


__all__ = [
    "T04PatchBatchRunResult",
    "T04PatchRunItem",
    "T04RunResult",
    "build_t04_patch_run_summary",
    "run_t04_all_intersections_from_patch_dir",
    "run_t04_manual_mode",
    "run_t04_single_intersection_from_geojson_files",
    "run_t04_single_intersection_from_patch_dir",
    "run_t04_single_intersection_manual_mode",
]
