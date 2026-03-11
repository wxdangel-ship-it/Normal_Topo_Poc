from __future__ import annotations

_IMPORT_ERROR: ModuleNotFoundError | None = None

try:
    from .api import (
        T04PatchBatchRunResult,
        T04PatchRunItem,
        T04RunResult,
        build_t04_patch_run_summary,
        run_t04_all_intersections_from_geojson_files,
        run_t04_all_intersections_from_patch_dir,
        run_t04_manual_mode,
        run_t04_single_intersection_from_geojson_files,
        run_t04_single_intersection_from_patch_dir,
        run_t04_single_intersection_manual_mode,
    )
    from .artifact_checker import (
        check_movement_matrix_payload,
        check_movement_results_payload,
        check_patch_manifest_payload,
        check_serialized_bundle_payload,
        check_t04_patch_output_root,
        check_t04_run_output_dir,
    )
    from .baseline_regression import (
        check_t04_baseline_manifest_payload,
        load_t04_baseline_manifest,
        run_t04_baseline_regression_smoke,
    )
    from .dataset_runner import (
        DEFAULT_COMPUTE_BUFFER_M,
        T04DatasetMainnodeidRunItem,
        T04DatasetMainnodeidRunResult,
        build_t04_dataset_mainnodeid_summary,
        run_t04_mainnodeids_from_geojson_dataset,
        write_t04_dataset_mainnodeid_result,
    )
    from .diagnostics import probe_road_geojson_file, probe_road_raw_properties
    from .geojson_io import (
        coerce_mainid_value,
        discover_geojson_dataset_inputs,
        discover_patch_dir_inputs,
        list_available_mainids,
        load_geojson_feature_collection,
        parse_mainid_values,
        select_single_intersection_node_features,
    )
    from .manual_mode_support import (
        build_approach_catalog,
        build_manual_override_template,
        build_review_bundle,
        build_review_nonstandard_targets,
        build_review_special_profile_gaps,
        build_review_unknown_movements,
        write_t04_manual_support_outputs,
    )
    from .manual_overrides import load_manual_override_source
    from .models import (
        ApproachModel,
        ArmModel,
        IntersectionBundle,
        IntersectionModel,
        MovementCandidate,
        MovementDecision,
    )
    from .multi_patch import (
        T04MultiPatchRunItem,
        T04MultiPatchRunResult,
        build_t04_multi_patch_summary,
        discover_patch_dirs,
        run_t04_multi_patch_manual_mode,
        write_t04_multi_patch_result,
    )
    from .normalize import NormalizedNode, NormalizedRoad, normalize_node_features, normalize_road_features
    from .override_roundtrip import (
        build_catalog_selector_inventory,
        roundtrip_manual_override_source,
        validate_manual_override_with_catalog,
        write_override_roundtrip_report,
    )
    from .reason_codes import *  # noqa: F403
    from .review_cycle import (
        T04PatchRootReviewCycleItem,
        T04PatchRootReviewCycleResult,
        T04ReviewCycleResult,
        build_t04_patch_root_review_cycle_summary,
        build_t04_review_cycle_summary,
        compare_t04_patch_batch_output_dirs,
        run_t04_review_cycle_from_geojson_files,
        run_t04_review_cycle_from_patch_dir,
        run_t04_review_cycle_from_patch_root,
        write_t04_patch_batch_diff_outputs,
    )
    from .run_diff import (
        compare_t04_run_dirs,
        compare_t04_run_dirs_and_write_outputs,
        write_t04_run_diff_outputs,
    )
    from .serialization import (
        build_movement_matrix,
        serialize_approach,
        serialize_arm,
        serialize_bundle,
        serialize_geometry_ref,
        serialize_intersection,
        serialize_movement_candidate,
        serialize_movement_decision,
        serialize_movement_result,
    )
    from .service_profile_resolver import (
        apply_manual_service_maps,
        apply_placeholder_paired_mainline_detection,
        detect_left_uturn_service_from_raw,
        detect_paired_mainline_from_context,
        find_raw_formway_value,
    )
    from .snapshot_compare import compare_t04_output_dir_to_snapshot
    from .t04_2_builder import (
        APPROACH_OVERRIDE_FIELDS,
        approach_key,
        build_intersection_bundles,
        build_intersection_bundles_with_manual_overrides,
    )
    from .t04_3_rules import evaluate_bundle, evaluate_movement
    from .visual_review import (
        build_t04_review_html,
        build_t04_run_diff_html,
        write_t04_review_html,
        write_t04_run_diff_html,
    )
    from .writer import (
        write_t04_patch_batch_result,
        write_t04_patch_review_bundle,
        write_t04_review_bundle,
        write_t04_run_result,
    )
except ModuleNotFoundError as exc:
    if exc.name != "shapely":
        raise
    _IMPORT_ERROR = exc


__all__ = [
    "APPROACH_OVERRIDE_FIELDS",
    "ApproachModel",
    "ArmModel",
    "DEFAULT_COMPUTE_BUFFER_M",
    "IntersectionBundle",
    "IntersectionModel",
    "MovementCandidate",
    "MovementDecision",
    "T04DatasetMainnodeidRunItem",
    "T04DatasetMainnodeidRunResult",
    "T04PatchRootReviewCycleItem",
    "T04PatchRootReviewCycleResult",
    "T04MultiPatchRunItem",
    "T04MultiPatchRunResult",
    "T04PatchBatchRunResult",
    "T04PatchRunItem",
    "T04ReviewCycleResult",
    "T04RunResult",
    "NormalizedNode",
    "NormalizedRoad",
    "apply_manual_service_maps",
    "apply_placeholder_paired_mainline_detection",
    "approach_key",
    "build_movement_matrix",
    "build_intersection_bundles",
    "build_intersection_bundles_with_manual_overrides",
    "build_approach_catalog",
    "build_catalog_selector_inventory",
    "build_manual_override_template",
    "build_t04_patch_root_review_cycle_summary",
    "build_review_bundle",
    "build_review_nonstandard_targets",
    "build_review_special_profile_gaps",
    "build_review_unknown_movements",
    "build_t04_multi_patch_summary",
    "build_t04_dataset_mainnodeid_summary",
    "build_t04_patch_run_summary",
    "build_t04_review_cycle_summary",
    "check_t04_baseline_manifest_payload",
    "check_movement_matrix_payload",
    "check_movement_results_payload",
    "check_patch_manifest_payload",
    "check_serialized_bundle_payload",
    "check_t04_patch_output_root",
    "check_t04_run_output_dir",
    "coerce_mainid_value",
    "compare_t04_patch_batch_output_dirs",
    "compare_t04_run_dirs",
    "compare_t04_run_dirs_and_write_outputs",
    "compare_t04_output_dir_to_snapshot",
    "detect_paired_mainline_from_context",
    "detect_left_uturn_service_from_raw",
    "discover_geojson_dataset_inputs",
    "discover_patch_dirs",
    "discover_patch_dir_inputs",
    "evaluate_bundle",
    "evaluate_movement",
    "find_raw_formway_value",
    "list_available_mainids",
    "load_t04_baseline_manifest",
    "load_geojson_feature_collection",
    "load_manual_override_source",
    "probe_road_geojson_file",
    "probe_road_raw_properties",
    "parse_mainid_values",
    "roundtrip_manual_override_source",
    "run_t04_baseline_regression_smoke",
    "run_t04_mainnodeids_from_geojson_dataset",
    "run_t04_multi_patch_manual_mode",
    "run_t04_all_intersections_from_geojson_files",
    "run_t04_all_intersections_from_patch_dir",
    "run_t04_manual_mode",
    "run_t04_review_cycle_from_geojson_files",
    "run_t04_review_cycle_from_patch_dir",
    "run_t04_review_cycle_from_patch_root",
    "run_t04_single_intersection_from_geojson_files",
    "run_t04_single_intersection_from_patch_dir",
    "run_t04_single_intersection_manual_mode",
    "select_single_intersection_node_features",
    "serialize_approach",
    "serialize_arm",
    "serialize_bundle",
    "serialize_geometry_ref",
    "serialize_intersection",
    "serialize_movement_candidate",
    "serialize_movement_decision",
    "serialize_movement_result",
    "validate_manual_override_with_catalog",
    "write_override_roundtrip_report",
    "write_t04_dataset_mainnodeid_result",
    "write_t04_multi_patch_result",
    "write_t04_patch_batch_result",
    "write_t04_patch_batch_diff_outputs",
    "write_t04_patch_review_bundle",
    "write_t04_review_bundle",
    "write_t04_run_diff_outputs",
    "write_t04_run_diff_html",
    "write_t04_run_result",
    "write_t04_review_html",
    "write_t04_manual_support_outputs",
    "build_t04_review_html",
    "build_t04_run_diff_html",
    "normalize_node_features",
    "normalize_road_features",
]


def __getattr__(name: str):
    if name in __all__ and _IMPORT_ERROR is not None:
        raise ModuleNotFoundError(
            "shapely is required to access normal_topo_poc.modules.t04_intersection_modeling exports. "
            "Install project dependencies before using T04 runtime APIs."
        ) from _IMPORT_ERROR
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
