from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any

from shapely.geometry import Point

from .manual_overrides import load_manual_override_source
from .models import (
    ApproachModel,
    ArmModel,
    IntersectionBundle,
    IntersectionModel,
    MovementCandidate,
    NormalizedGeometryRef,
)
from .normalize import (
    NormalizedNode,
    NormalizedRoad,
    circular_diff_deg,
    normalize_node_features,
    normalize_road_features,
    road_away_vector,
    road_trend_vector,
    vector_angle_deg,
)
from .service_profile_resolver import (
    apply_manual_service_maps,
    apply_placeholder_paired_mainline_detection,
    detect_left_uturn_service_from_raw,
    find_raw_formway_value,
)

APPROACH_OVERRIDE_FIELDS = {
    "approach_profile",
    "exit_leg_role",
    "is_core_signalized_approach",
    "paired_mainline_approach_id",
}

_APPROACH_PROFILE_ALLOWED = {
    "default_signalized",
    "left_uturn_service",
    "paired_mainline_no_left_uturn",
    "unknown",
}

_EXIT_ROLE_ALLOWED = {
    "core_standard_exit",
    "service_standard_exit",
    "auxiliary_parallel_exit",
    "access_exit",
    "unknown",
}

_ARM_CLUSTER_DEG = 40.0
_ARM_SINGLETON_MERGE_DEG = 50.0
_ARM_SINGLETON_CLEAR_GAP_DEG = 7.0
_ARM_SPECIAL_SIDE_CLEAR_GAP_DEG = 10.0
_ARM_SPECIAL_SIDE_ATTACH_DEG = 60.0
_PROVISIONAL_ARM_SIDE_SPREAD_DEG = 60.0

_SPECIAL_COMPANION_ENTRY_PROFILES = {
    "left_uturn_service",
    "paired_mainline_no_left_uturn",
}

_SPECIAL_COMPANION_EXIT_ROLES = {
    "service_standard_exit",
    "auxiliary_parallel_exit",
    "access_exit",
}


def approach_key(road_id: str, movement_side: str) -> str:
    return f"{road_id}:{movement_side}"


def build_intersection_bundles(
    *,
    node_features: list[dict[str, Any]],
    road_features: list[dict[str, Any]],
    source_type: str = "real",
    approach_overrides: dict[str, dict[str, Any]] | None = None,
    manual_override_source: str | Path | dict[str, Any] | None = None,
    manual_service_profile_map: dict[str, str] | None = None,
    manual_paired_mainline_map: dict[str, str] | None = None,
) -> list[IntersectionBundle]:
    nodes = normalize_node_features(node_features)
    roads = normalize_road_features(road_features)
    file_service_profile_map, file_paired_mainline_map = load_manual_override_source(manual_override_source)
    return _build_bundles(
        nodes=nodes,
        roads=roads,
        source_type=source_type,
        approach_overrides=approach_overrides or {},
        manual_service_profile_map={**file_service_profile_map, **(manual_service_profile_map or {})},
        manual_paired_mainline_map={**file_paired_mainline_map, **(manual_paired_mainline_map or {})},
    )


def build_intersection_bundles_with_manual_overrides(
    *,
    node_features: list[dict[str, Any]],
    road_features: list[dict[str, Any]],
    manual_override_source: str | Path | dict[str, Any] | None = None,
    source_type: str = "real",
    approach_overrides: dict[str, dict[str, Any]] | None = None,
) -> list[IntersectionBundle]:
    return build_intersection_bundles(
        node_features=node_features,
        road_features=road_features,
        source_type=source_type,
        approach_overrides=approach_overrides,
        manual_override_source=manual_override_source,
    )


def _build_bundles(
    *,
    nodes: list[NormalizedNode],
    roads: list[NormalizedRoad],
    source_type: str,
    approach_overrides: dict[str, dict[str, Any]],
    manual_service_profile_map: dict[str, str],
    manual_paired_mainline_map: dict[str, str],
) -> list[IntersectionBundle]:
    node_by_id = {node.node_id: node for node in nodes}
    groups: dict[Any, list[NormalizedNode]] = defaultdict(list)
    for node in nodes:
        groups[node.mainid].append(node)

    bundles: list[IntersectionBundle] = []
    for mainid, group_nodes in groups.items():
        group_node_ids = {node.node_id for node in group_nodes}
        intersection = IntersectionModel(
            intersection_id=f"intersection:{mainid}",
            node_group_id=mainid,
            member_node_ids=tuple(sorted(group_node_ids, key=str)),
            control_type="signalized",
            signalized_control_zone_id=mainid,
            source_type=source_type,
            remarks=(),
        )
        incident_roads = [road for road in roads if road.snodeid in group_node_ids or road.enodeid in group_node_ids]
        approaches = _build_approaches(
            intersection=intersection,
            group_node_ids=group_node_ids,
            incident_roads=incident_roads,
            node_by_id=node_by_id,
            approach_overrides=approach_overrides,
        )
        provisional_arms, approaches = _assign_provisional_arms(
            intersection=intersection,
            approaches=approaches,
        )
        approaches = _apply_lateral_ranks(approaches)
        approaches = _apply_entry_defaults(approaches)
        approaches = apply_manual_service_maps(
            approaches=approaches,
            manual_service_profile_map=manual_service_profile_map,
            manual_paired_mainline_map=manual_paired_mainline_map,
        )
        approaches = apply_placeholder_paired_mainline_detection(approaches)
        arms, approaches = _assign_arms(
            intersection=intersection,
            approaches=approaches,
            incident_roads=incident_roads,
            group_node_ids=group_node_ids,
            provisional_arms=provisional_arms,
        )
        approaches = _apply_lateral_ranks(approaches)
        approaches = _apply_exit_defaults(approaches)
        movements = _build_movements(intersection=intersection, approaches=approaches, arms=arms)
        bundles.append(
            IntersectionBundle(
                intersection=intersection,
                arms=tuple(arms),
                approaches=tuple(approaches),
                movements=tuple(movements),
                warnings=(),
                approach_index={approach.approach_id: approach for approach in approaches},
                arm_index={arm.arm_id: arm for arm in arms},
            )
        )
    return bundles


def _build_approaches(
    *,
    intersection: IntersectionModel,
    group_node_ids: set[Any],
    incident_roads: list[NormalizedRoad],
    node_by_id: dict[Any, NormalizedNode],
    approach_overrides: dict[str, dict[str, Any]],
) -> list[ApproachModel]:
    approaches: list[ApproachModel] = []
    for road in incident_roads:
        attached_node_id = _attached_node_id(road=road, group_node_ids=group_node_ids)
        if attached_node_id is None:
            continue
        node = node_by_id.get(attached_node_id)
        if node is None:
            continue

        away_vec = road_away_vector(road, node_id=attached_node_id)
        trend_vec = road_trend_vector(road, node_id=attached_node_id)
        side_angle = vector_angle_deg(*away_vec)
        trend_angle = vector_angle_deg(*trend_vec)
        raw_formway = find_raw_formway_value(raw_properties=road.raw_properties)
        far_node_id = _far_node_id_for_road(
            road=road,
            attached_node_id=attached_node_id,
            group_node_ids=group_node_ids,
        )

        for movement_side in _movement_sides_for_road(road=road, group_node_ids=group_node_ids):
            travel_angle = vector_angle_deg(*_travel_vector(away_vec=away_vec, movement_side=movement_side))
            key = approach_key(road.road_id, movement_side)
            override = dict(approach_overrides.get(key) or {})
            detected_profile = None
            if movement_side == "entry":
                detected_profile = detect_left_uturn_service_from_raw(raw_properties=road.raw_properties)
            approach_profile, approach_profile_source = _resolve_approach_profile(
                movement_side=movement_side,
                override=override,
                detected_profile=detected_profile,
                raw_formway=raw_formway,
            )
            if approach_profile not in _APPROACH_PROFILE_ALLOWED:
                approach_profile = "unknown"
                approach_profile_source = "unknown"
            exit_leg_role = str(override.get("exit_leg_role", "unknown"))
            if exit_leg_role not in _EXIT_ROLE_ALLOWED:
                exit_leg_role = "unknown"
            is_core = override.get("is_core_signalized_approach", "unknown")
            if is_core not in {True, False, "unknown"}:
                is_core = "unknown"
            paired_mainline_approach_id = override.get("paired_mainline_approach_id")
            paired_mainline_source = _resolve_paired_mainline_source(
                movement_side=movement_side,
                override=override,
                paired_mainline_approach_id=paired_mainline_approach_id,
            )

            remarks: list[str] = []
            if circular_diff_deg(side_angle, trend_angle) > 35.0:
                remarks.append("TODO: far-trend correction boundary for arm grouping remains candidate-only")
            if raw_formway is not None and detected_profile is None:
                remarks.append("TODO: raw formway detected but bit mapping is unconfirmed; auto service-road inference stays disabled")
            if "approach_profile" in override:
                remarks.append("manual_override:approach_profile")
            if "is_core_signalized_approach" in override:
                remarks.append("manual_override:is_core_signalized_approach")
            if "exit_leg_role" in override:
                remarks.append("manual_override:exit_leg_role")
            if "paired_mainline_approach_id" in override:
                remarks.append("manual_override:paired_mainline_approach_id")

            approaches.append(
                ApproachModel(
                    approach_id=f"{intersection.intersection_id}|{key}",
                    road_id=road.road_id,
                    intersection_id=intersection.intersection_id,
                    node_id=attached_node_id,
                    arm_id="",
                    movement_side=movement_side,
                    direction_type=_direction_type(road.direction),
                    is_core_signalized_approach=is_core,
                    approach_profile=approach_profile,
                    approach_profile_source=approach_profile_source,
                    paired_mainline_approach_id=paired_mainline_approach_id,
                    paired_mainline_source=paired_mainline_source,
                    exit_leg_role=exit_leg_role,
                    is_standard_exit_leg="unknown",
                    signalized_control_zone_id=intersection.signalized_control_zone_id,
                    side_angle_deg=side_angle,
                    travel_angle_deg=travel_angle,
                    lateral_rank=None,
                    geometry_ref=NormalizedGeometryRef(point=node.point, line=road.line),
                    evidence_refs=tuple(
                        ref
                        for ref in (
                            f"road:{road.road_id}",
                            f"node:{attached_node_id}",
                            f"far_node:{far_node_id}" if far_node_id is not None else None,
                        )
                        if ref is not None
                    ),
                    remarks=tuple(remarks),
                )
            )
    return approaches


def _resolve_approach_profile(
    *,
    movement_side: str,
    override: dict[str, Any],
    detected_profile: str | None,
    raw_formway: Any | None,
) -> tuple[str, str]:
    if "approach_profile" in override:
        return str(override.get("approach_profile")), "approach_override"
    if detected_profile is not None:
        return detected_profile, "auto_detected"
    if movement_side == "entry" and raw_formway is not None:
        return "default_signalized", "auto_detection_placeholder_no_hit"
    return "default_signalized", "default_derived"


def _resolve_paired_mainline_source(
    *,
    movement_side: str,
    override: dict[str, Any],
    paired_mainline_approach_id: str | None,
) -> str:
    if movement_side != "entry":
        return "not_applicable"
    if "paired_mainline_approach_id" in override and paired_mainline_approach_id:
        return "approach_override"
    return "not_applicable"


def _attached_node_id(*, road: NormalizedRoad, group_node_ids: set[Any]) -> Any | None:
    if road.snodeid in group_node_ids and road.enodeid not in group_node_ids:
        return road.snodeid
    if road.enodeid in group_node_ids and road.snodeid not in group_node_ids:
        return road.enodeid
    if road.snodeid in group_node_ids:
        return road.snodeid
    if road.enodeid in group_node_ids:
        return road.enodeid
    return None


def _movement_sides_for_road(*, road: NormalizedRoad, group_node_ids: set[Any]) -> list[str]:
    direction = road.direction
    if direction in (0, 1, None):
        return ["entry", "exit"]
    sides: list[str] = []
    if direction == 2:
        if road.enodeid in group_node_ids:
            sides.append("entry")
        if road.snodeid in group_node_ids:
            sides.append("exit")
    elif direction == 3:
        if road.snodeid in group_node_ids:
            sides.append("entry")
        if road.enodeid in group_node_ids:
            sides.append("exit")
    return sides or ["entry", "exit"]


def _direction_type(direction: int | None) -> str:
    if direction in (0, 1, None):
        return "bidirectional"
    if direction in (2, 3):
        return "one_way"
    return "unknown"


def _travel_vector(*, away_vec: tuple[float, float], movement_side: str) -> tuple[float, float]:
    ax, ay = away_vec
    if movement_side == "entry":
        return (-ax, -ay)
    return (ax, ay)


def _far_node_id_for_road(
    *,
    road: NormalizedRoad,
    attached_node_id: Any,
    group_node_ids: set[Any],
) -> Any | None:
    if road.snodeid == attached_node_id and road.enodeid not in group_node_ids:
        return road.enodeid
    if road.enodeid == attached_node_id and road.snodeid not in group_node_ids:
        return road.snodeid
    if road.snodeid in group_node_ids and road.enodeid not in group_node_ids:
        return road.enodeid
    if road.enodeid in group_node_ids and road.snodeid not in group_node_ids:
        return road.snodeid
    return None


def _assign_provisional_arms(
    *,
    intersection: IntersectionModel,
    approaches: list[ApproachModel],
) -> tuple[list[ArmModel], list[ApproachModel]]:
    approach_by_id = {approach.approach_id: approach for approach in approaches}
    clusters = _build_contiguous_arm_clusters(approaches, approach_by_id=approach_by_id)
    clusters = [_sorted_cluster(cluster, approach_by_id=approach_by_id) for cluster in clusters]
    return _materialize_arm_clusters(
        intersection=intersection,
        approaches=approaches,
        clusters=clusters,
    )


def _assign_arms(
    *,
    intersection: IntersectionModel,
    approaches: list[ApproachModel],
    incident_roads: list[NormalizedRoad],
    group_node_ids: set[Any],
    provisional_arms: list[ArmModel],
) -> tuple[list[ArmModel], list[ApproachModel]]:
    approach_by_id = {approach.approach_id: approach for approach in approaches}
    road_by_id = {road.road_id: road for road in incident_roads}
    far_node_by_approach = _build_far_node_by_approach(
        approaches=approaches,
        road_by_id=road_by_id,
        group_node_ids=group_node_ids,
    )
    ordered_nodes = _ordered_attached_nodes(approaches, approach_by_id=approach_by_id)
    if not ordered_nodes:
        return ([], [])

    provisional_arm_by_id = {arm.arm_id: arm for arm in provisional_arms}
    seed_entries = _select_final_arm_seed_entries(
        approaches=approaches,
        provisional_arm_by_id=provisional_arm_by_id,
    )
    clusters = _build_seed_partition_clusters(
        ordered_nodes=ordered_nodes,
        approach_by_id=approach_by_id,
        far_node_by_approach=far_node_by_approach,
        seed_entries=seed_entries,
    )
    clusters = [_sorted_cluster(cluster, approach_by_id=approach_by_id) for cluster in clusters]
    return _materialize_arm_clusters(
        intersection=intersection,
        approaches=approaches,
        clusters=clusters,
    )


def _build_contiguous_arm_clusters(
    approaches: list[ApproachModel],
    *,
    approach_by_id: dict[str, ApproachModel],
) -> list[dict[str, Any]]:
    ordered_nodes = _ordered_attached_nodes(approaches, approach_by_id=approach_by_id)
    if not ordered_nodes:
        return []

    clusters: list[dict[str, Any]] = [
        {
            "angles": list(ordered_nodes[0]["angles"]),
            "members": list(ordered_nodes[0]["members"]),
        }
    ]
    for current in ordered_nodes[1:]:
        diff = circular_diff_deg(current["representative_angle_deg"], _mean_angle_deg(clusters[-1]["angles"]))
        if diff <= _ARM_CLUSTER_DEG:
            clusters[-1]["angles"].extend(current["angles"])
            clusters[-1]["members"].extend(current["members"])
            continue
        clusters.append({"angles": list(current["angles"]), "members": list(current["members"])})

    if len(clusters) >= 2:
        wrap_diff = circular_diff_deg(_mean_angle_deg(clusters[0]["angles"]), _mean_angle_deg(clusters[-1]["angles"]))
        if wrap_diff <= _ARM_CLUSTER_DEG:
            first = clusters.pop(0)
            clusters[-1]["angles"].extend(first["angles"])
            clusters[-1]["members"].extend(first["members"])

    return clusters


def _ordered_attached_nodes(
    approaches: list[ApproachModel],
    *,
    approach_by_id: dict[str, ApproachModel],
) -> list[dict[str, Any]]:
    node_members: dict[Any, list[str]] = defaultdict(list)
    node_points: dict[Any, Point] = {}
    for approach in approaches:
        node_members[approach.node_id].append(approach.approach_id)
        if approach.geometry_ref.point is not None and approach.node_id not in node_points:
            node_points[approach.node_id] = approach.geometry_ref.point

    if not node_members:
        return []

    centroid_x, centroid_y = _attached_node_centroid(node_points)
    ordered_nodes: list[dict[str, Any]] = []
    for node_id, member_ids in node_members.items():
        point = node_points.get(node_id)
        if point is None:
            node_angle_deg = _mean_angle_deg([approach_by_id[member_id].side_angle_deg for member_id in member_ids])
        else:
            node_angle_deg = vector_angle_deg(float(point.x - centroid_x), float(point.y - centroid_y))
        ordered_member_ids = sorted(
            member_ids,
            key=lambda approach_id: (
                approach_by_id[approach_id].side_angle_deg,
                approach_by_id[approach_id].approach_id,
            ),
        )
        ordered_nodes.append(
            {
                "node_id": node_id,
                "node_angle_deg": node_angle_deg,
                "representative_angle_deg": _mean_angle_deg(
                    [approach_by_id[approach_id].side_angle_deg for approach_id in ordered_member_ids]
                ),
                "members": ordered_member_ids,
                "angles": [approach_by_id[approach_id].side_angle_deg for approach_id in ordered_member_ids],
            }
        )

    ordered_nodes.sort(key=lambda item: (item["node_angle_deg"], str(item["node_id"])))
    return ordered_nodes


def _attached_node_centroid(node_points: dict[Any, Point]) -> tuple[float, float]:
    if not node_points:
        return (0.0, 0.0)
    points = list(node_points.values())
    return (
        float(sum(point.x for point in points) / len(points)),
        float(sum(point.y for point in points) / len(points)),
    )


def _materialize_arm_clusters(
    *,
    intersection: IntersectionModel,
    approaches: list[ApproachModel],
    clusters: list[dict[str, Any]],
) -> tuple[list[ArmModel], list[ApproachModel]]:
    arms: list[ArmModel] = []
    arm_id_by_approach: dict[str, str] = {}
    for idx, cluster in enumerate(clusters):
        arm_id = f"{intersection.intersection_id}|arm:{idx}"
        for approach_id in cluster["members"]:
            arm_id_by_approach[approach_id] = arm_id
        arms.append(
            ArmModel(
                arm_id=arm_id,
                intersection_id=intersection.intersection_id,
                member_approach_ids=tuple(cluster["members"]),
                arm_heading_group=f"group_{idx}",
                representative_angle_deg=_mean_angle_deg(cluster["angles"]),
                remarks=("TODO: arm_heading_group remains abstract; no absolute NSEW binding in MVP",),
            )
        )
    updated = [replace(approach, arm_id=arm_id_by_approach[approach.approach_id]) for approach in approaches]
    return (arms, updated)


def _select_final_arm_seed_entries(
    *,
    approaches: list[ApproachModel],
    provisional_arm_by_id: dict[str, ArmModel],
) -> list[ApproachModel]:
    provisional_side_counts = _count_approaches_by_arm_side(approaches)
    seed_entries = [
        approach
        for approach in approaches
        if _is_final_arm_seed_entry(
            approach,
            provisional_arm_by_id=provisional_arm_by_id,
            provisional_side_counts=provisional_side_counts,
        )
    ]
    if seed_entries:
        return seed_entries
    fallback_entries = [
        approach
        for approach in approaches
        if approach.movement_side == "entry"
        and approach.approach_profile not in _SPECIAL_COMPANION_ENTRY_PROFILES
    ]
    if fallback_entries:
        return fallback_entries
    return [approach for approach in approaches if approach.movement_side == "entry"]


def _is_final_arm_seed_entry(
    approach: ApproachModel,
    *,
    provisional_arm_by_id: dict[str, ArmModel],
    provisional_side_counts: dict[tuple[str, str], int],
) -> bool:
    if approach.movement_side != "entry":
        return False
    if approach.approach_profile in _SPECIAL_COMPANION_ENTRY_PROFILES:
        return False
    if approach.approach_profile not in {"default_signalized", "unknown"}:
        return False
    if approach.is_core_signalized_approach is not True:
        return False
    provisional_arm = provisional_arm_by_id.get(approach.arm_id)
    if provisional_arm is None:
        return True
    if provisional_side_counts.get((approach.arm_id, "exit"), 0) > 0:
        return True
    return len(provisional_arm.member_approach_ids) > 1


def _build_seed_partition_clusters(
    *,
    ordered_nodes: list[dict[str, Any]],
    approach_by_id: dict[str, ApproachModel],
    far_node_by_approach: dict[str, Any | None],
    seed_entries: list[ApproachModel],
) -> list[dict[str, Any]]:
    if not ordered_nodes:
        return []

    node_index_by_id = {
        item["node_id"]: index
        for index, item in enumerate(ordered_nodes)
    }
    parent = _build_node_component_parent(
        ordered_nodes=ordered_nodes,
        approach_by_id=approach_by_id,
        far_node_by_approach=far_node_by_approach,
    )
    component_nodes: dict[Any, list[Any]] = defaultdict(list)
    for node_id in node_index_by_id:
        component_nodes[_uf_find(parent, node_id)].append(node_id)

    seed_node_ids = [approach.node_id for approach in seed_entries if approach.node_id in node_index_by_id]
    seed_roots = _stable_node_ids(
        [_uf_find(parent, node_id) for node_id in seed_node_ids]
    )
    if not seed_roots:
        seed_roots = _stable_node_ids(list(component_nodes.keys()))

    seed_index_lists = {
        root: sorted(node_index_by_id[node_id] for node_id in component_nodes[root])
        for root in seed_roots
    }
    seed_rank_by_root = {root: rank for rank, root in enumerate(seed_roots)}
    provisional_members_by_arm: dict[str, list[ApproachModel]] = defaultdict(list)
    for approach in approach_by_id.values():
        provisional_members_by_arm[approach.arm_id].append(approach)
    component_angles = {
        root: [
            angle
            for node_id in component_nodes[root]
            for angle in next(item["angles"] for item in ordered_nodes if item["node_id"] == node_id)
        ]
        for root in component_nodes
    }
    seed_root_by_provisional_arm: dict[str, Any] = {}
    for seed_entry in seed_entries:
        seed_root_by_provisional_arm.setdefault(seed_entry.arm_id, _uf_find(parent, seed_entry.node_id))
    component_assignment: dict[Any, Any] = {}
    total_nodes = len(ordered_nodes)
    for root, component_node_ids in component_nodes.items():
        if root in seed_index_lists:
            component_assignment[root] = root
            continue
        provisional_arm_ids = _stable_node_ids(
            [
                approach_by_id[approach_id].arm_id
                for node_id in component_node_ids
                for approach_id in next(item["members"] for item in ordered_nodes if item["node_id"] == node_id)
            ]
        )
        if (
            len(provisional_arm_ids) == 1
            and provisional_arm_ids[0] in seed_root_by_provisional_arm
            and _provisional_arm_is_locally_coherent(provisional_members_by_arm[provisional_arm_ids[0]])
        ):
            component_assignment[root] = seed_root_by_provisional_arm[provisional_arm_ids[0]]
            continue
        required_root = _select_required_seed_root(
            component_node_ids=component_node_ids,
            ordered_nodes=ordered_nodes,
            approach_by_id=approach_by_id,
            seed_angles_by_root={seed_root: component_angles[seed_root] for seed_root in seed_roots},
        )
        if required_root is not None:
            component_assignment[root] = required_root
            continue
        attach_root = _select_clear_singleton_seed_root(
            component_angles=component_angles[root],
            seed_angles_by_root={seed_root: component_angles[seed_root] for seed_root in seed_roots},
        )
        component_assignment[root] = attach_root if attach_root is not None else root

    node_assignment: dict[Any, Any] = {}
    for root, component_node_ids in component_nodes.items():
        for node_id in component_node_ids:
            node_assignment[node_id] = component_assignment[root]

    clusters_by_root: dict[Any, dict[str, Any]] = {}
    for node_item in ordered_nodes:
        node_id = node_item["node_id"]
        arm_root = node_assignment[node_id]
        cluster = clusters_by_root.setdefault(arm_root, {"members": [], "angles": []})
        cluster["members"].extend(node_item["members"])
        cluster["angles"].extend(node_item["angles"])

    return list(clusters_by_root.values())


def _build_node_component_parent(
    *,
    ordered_nodes: list[dict[str, Any]],
    approach_by_id: dict[str, ApproachModel],
    far_node_by_approach: dict[str, Any | None],
) -> dict[Any, Any]:
    parent = {item["node_id"]: item["node_id"] for item in ordered_nodes}
    node_ids_by_far_node: dict[Any, list[Any]] = defaultdict(list)
    for approach_id, far_node_id in far_node_by_approach.items():
        if far_node_id is None:
            continue
        approach = approach_by_id[approach_id]
        node_ids_by_far_node[far_node_id].append(approach.node_id)
    for node_ids in node_ids_by_far_node.values():
        unique_ids = _stable_node_ids(node_ids)
        if len(unique_ids) < 2:
            continue
        anchor = unique_ids[0]
        for node_id in unique_ids[1:]:
            _uf_union(parent, anchor, node_id)
    return parent


def _nearest_seed_distance(node_index: int, seed_indexes: list[int], total_nodes: int) -> tuple[int, int]:
    best: tuple[int, int] | None = None
    for seed_index in seed_indexes:
        clockwise = (seed_index - node_index) % total_nodes
        counter_clockwise = (node_index - seed_index) % total_nodes
        dist = min(clockwise, counter_clockwise)
        candidate = (dist, clockwise)
        if best is None or candidate < best:
            best = candidate
    if best is None:
        return (total_nodes, total_nodes)
    return best


def _select_required_seed_root(
    *,
    component_node_ids: list[Any],
    ordered_nodes: list[dict[str, Any]],
    approach_by_id: dict[str, ApproachModel],
    seed_angles_by_root: dict[Any, list[float]],
) -> Any | None:
    node_item_by_id = {item["node_id"]: item for item in ordered_nodes}
    component_members = [
        approach_by_id[approach_id]
        for node_id in component_node_ids
        for approach_id in node_item_by_id[node_id]["members"]
    ]
    entry_items = [item for item in component_members if item.movement_side == "entry"]
    exit_items = [item for item in component_members if item.movement_side == "exit"]
    if any(_requires_entry_companion(item) for item in entry_items) and len(entry_items) < 2:
        return _select_clear_required_seed_root(
            anchor_angles=[item.side_angle_deg for item in entry_items if _requires_entry_companion(item)],
            seed_angles_by_root=seed_angles_by_root,
        )
    if any(_requires_exit_companion(item) for item in exit_items) and len(exit_items) < 2:
        return _select_clear_required_seed_root(
            anchor_angles=[item.side_angle_deg for item in exit_items if _requires_exit_companion(item)],
            seed_angles_by_root=seed_angles_by_root,
        )
    return None


def _select_clear_singleton_seed_root(
    *,
    component_angles: list[float],
    seed_angles_by_root: dict[Any, list[float]],
) -> Any | None:
    if len(component_angles) != 1 or len(seed_angles_by_root) < 2:
        return None
    source_angle = component_angles[0]
    candidates = sorted(
        (
            circular_diff_deg(source_angle, _mean_angle_deg(seed_angles)),
            seed_root,
        )
        for seed_root, seed_angles in seed_angles_by_root.items()
        if seed_angles
    )
    if not candidates:
        return None
    if len(candidates) >= 2 and candidates[1][0] - candidates[0][0] < _ARM_SINGLETON_CLEAR_GAP_DEG:
        return None
    return candidates[0][1]


def _select_clear_required_seed_root(
    *,
    anchor_angles: list[float],
    seed_angles_by_root: dict[Any, list[float]],
) -> Any | None:
    if not anchor_angles or not seed_angles_by_root:
        return None
    candidates = sorted(
        (
            _min_circular_diff(anchor_angles, seed_angles),
            seed_root,
        )
        for seed_root, seed_angles in seed_angles_by_root.items()
        if seed_angles
    )
    if not candidates:
        return None
    if candidates[0][0] > _ARM_SPECIAL_SIDE_ATTACH_DEG:
        return None
    if len(candidates) >= 2 and candidates[1][0] - candidates[0][0] < _ARM_SPECIAL_SIDE_CLEAR_GAP_DEG:
        return None
    return candidates[0][1]


def _provisional_arm_is_locally_coherent(approaches: list[ApproachModel]) -> bool:
    entry_angles = [approach.side_angle_deg for approach in approaches if approach.movement_side == "entry"]
    exit_angles = [approach.side_angle_deg for approach in approaches if approach.movement_side == "exit"]
    return _angles_are_locally_coherent(entry_angles) and _angles_are_locally_coherent(exit_angles)


def _angles_are_locally_coherent(angles: list[float]) -> bool:
    if len(angles) <= 1:
        return True
    ordered = sorted(float(angle) % 360.0 for angle in angles)
    max_gap = 0.0
    for idx, angle in enumerate(ordered):
        next_angle = ordered[(idx + 1) % len(ordered)]
        gap = (next_angle - angle) % 360.0
        if gap > max_gap:
            max_gap = gap
    covered_arc = 360.0 - max_gap
    return covered_arc <= _PROVISIONAL_ARM_SIDE_SPREAD_DEG


def _stable_node_ids(node_ids: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    out: list[Any] = []
    for node_id in node_ids:
        if node_id in seen:
            continue
        seen.add(node_id)
        out.append(node_id)
    return out


def _uf_find(parent: dict[Any, Any], item: Any) -> Any:
    root = item
    while parent[root] != root:
        root = parent[root]
    while parent[item] != item:
        next_item = parent[item]
        parent[item] = root
        item = next_item
    return root


def _uf_union(parent: dict[Any, Any], left: Any, right: Any) -> None:
    left_root = _uf_find(parent, left)
    right_root = _uf_find(parent, right)
    if left_root == right_root:
        return
    parent[right_root] = left_root


def _build_far_node_by_approach(
    *,
    approaches: list[ApproachModel],
    road_by_id: dict[str, NormalizedRoad],
    group_node_ids: set[Any],
) -> dict[str, Any | None]:
    far_node_by_approach: dict[str, Any | None] = {}
    for approach in approaches:
        road = road_by_id.get(approach.road_id)
        if road is None:
            far_node_by_approach[approach.approach_id] = None
            continue
        far_node_by_approach[approach.approach_id] = _far_node_id_for_road(
            road=road,
            attached_node_id=approach.node_id,
            group_node_ids=group_node_ids,
        )
    return far_node_by_approach


def _merge_far_node_linked_clusters(
    clusters: list[dict[str, Any]],
    *,
    far_node_by_approach: dict[str, Any | None],
) -> list[dict[str, Any]]:
    merged = [{"angles": list(cluster["angles"]), "members": list(cluster["members"])} for cluster in clusters]
    while True:
        cluster_count = len(merged)
        if cluster_count <= 1:
            return merged
        merged_pair: tuple[int, int] | None = None
        for idx in range(cluster_count):
            next_idx = (idx + 1) % cluster_count
            if idx == next_idx:
                continue
            if _clusters_share_far_node(
                merged[idx],
                merged[next_idx],
                far_node_by_approach=far_node_by_approach,
            ):
                merged_pair = (next_idx, idx)
                break
        if merged_pair is None:
            return merged
        source_idx, target_idx = merged_pair
        _merge_adjacent_clusters(merged, source_idx=source_idx, target_idx=target_idx)


def _clusters_share_far_node(
    left_cluster: dict[str, Any],
    right_cluster: dict[str, Any],
    *,
    far_node_by_approach: dict[str, Any | None],
) -> bool:
    left_far_nodes = {
        far_node_by_approach.get(approach_id)
        for approach_id in left_cluster["members"]
        if far_node_by_approach.get(approach_id) is not None
    }
    right_far_nodes = {
        far_node_by_approach.get(approach_id)
        for approach_id in right_cluster["members"]
        if far_node_by_approach.get(approach_id) is not None
    }
    return bool(left_far_nodes and right_far_nodes and left_far_nodes.intersection(right_far_nodes))


def _merge_special_side_required_clusters(
    clusters: list[dict[str, Any]],
    *,
    approach_by_id: dict[str, ApproachModel],
) -> list[dict[str, Any]]:
    merged = [{"angles": list(cluster["angles"]), "members": list(cluster["members"])} for cluster in clusters]
    while True:
        best_pair: tuple[float, int, int] | None = None
        cluster_count = len(merged)
        if cluster_count <= 1:
            return merged
        for idx, cluster in enumerate(merged):
            requirements = _cluster_side_requirements(cluster, approach_by_id=approach_by_id)
            if not requirements:
                continue
            for side, anchor_angles in requirements.items():
                candidate_targets: list[tuple[float, int]] = []
                for target_idx in _neighbor_cluster_indices(idx, cluster_count):
                    target_angles = _cluster_side_travel_angles(
                        merged[target_idx],
                        movement_side=side,
                        approach_by_id=approach_by_id,
                    )
                    if not target_angles:
                        continue
                    candidate_targets.append((_min_circular_diff(anchor_angles, target_angles), target_idx))
                if not candidate_targets:
                    continue
                candidate_targets.sort()
                best_diff, best_target_idx = candidate_targets[0]
                if len(candidate_targets) >= 2:
                    second_diff = candidate_targets[1][0]
                    if second_diff - best_diff < _ARM_SPECIAL_SIDE_CLEAR_GAP_DEG:
                        continue
                pair = (best_diff, idx, best_target_idx)
                if best_pair is None or pair < best_pair:
                    best_pair = pair
        if best_pair is None:
            return merged
        _diff, source_idx, target_idx = best_pair
        _merge_adjacent_clusters(merged, source_idx=source_idx, target_idx=target_idx)


def _cluster_side_requirements(
    cluster: dict[str, Any],
    *,
    approach_by_id: dict[str, ApproachModel],
) -> dict[str, list[float]]:
    requirements: dict[str, list[float]] = {}
    entry_items = [
        approach_by_id[approach_id]
        for approach_id in cluster["members"]
        if approach_by_id[approach_id].movement_side == "entry"
    ]
    exit_items = [
        approach_by_id[approach_id]
        for approach_id in cluster["members"]
        if approach_by_id[approach_id].movement_side == "exit"
    ]

    entry_anchors = [item.travel_angle_deg for item in entry_items if _requires_entry_companion(item)]
    if entry_anchors and len(entry_items) < 2:
        requirements["entry"] = entry_anchors

    exit_anchors = [item.travel_angle_deg for item in exit_items if _requires_exit_companion(item)]
    if exit_anchors and len(exit_items) < 2:
        requirements["exit"] = exit_anchors
    return requirements


def _requires_entry_companion(approach: ApproachModel) -> bool:
    if approach.approach_profile in _SPECIAL_COMPANION_ENTRY_PROFILES:
        return True
    if approach.approach_profile not in {"default_signalized", "unknown"}:
        return True
    return approach.is_core_signalized_approach is False


def _requires_exit_companion(approach: ApproachModel) -> bool:
    if approach.exit_leg_role in _SPECIAL_COMPANION_EXIT_ROLES:
        return True
    return approach.is_standard_exit_leg is False


def _cluster_side_travel_angles(
    cluster: dict[str, Any],
    *,
    movement_side: str,
    approach_by_id: dict[str, ApproachModel],
) -> list[float]:
    return [
        approach_by_id[approach_id].travel_angle_deg
        for approach_id in cluster["members"]
        if approach_by_id[approach_id].movement_side == movement_side
    ]


def _min_circular_diff(left_angles: list[float], right_angles: list[float]) -> float:
    if not left_angles or not right_angles:
        return 360.0
    return min(
        circular_diff_deg(left_angle, right_angle)
        for left_angle in left_angles
        for right_angle in right_angles
    )


def _merge_singleton_one_side_clusters(
    clusters: list[dict[str, Any]],
    *,
    approach_by_id: dict[str, ApproachModel],
) -> list[dict[str, Any]]:
    merged = [{"angles": list(cluster["angles"]), "members": list(cluster["members"])} for cluster in clusters]
    while True:
        best_pair: tuple[float, int, int] | None = None
        cluster_count = len(merged)
        if cluster_count <= 1:
            return merged
        for idx, cluster in enumerate(merged):
            if len(cluster["members"]) != 1:
                continue
            movement_sides = _cluster_movement_sides(cluster, approach_by_id=approach_by_id)
            if len(movement_sides) != 1:
                continue
            cluster_angle = _mean_angle_deg(cluster["angles"])
            candidate_targets: list[tuple[float, int]] = []
            for target_idx in _neighbor_cluster_indices(idx, cluster_count):
                target = merged[target_idx]
                if len(target["members"]) < 2:
                    continue
                diff = circular_diff_deg(cluster_angle, _mean_angle_deg(target["angles"]))
                if diff > _ARM_SINGLETON_MERGE_DEG:
                    continue
                candidate_targets.append((diff, target_idx))
            if not candidate_targets:
                continue
            candidate_targets.sort()
            best_diff, best_target_idx = candidate_targets[0]
            if len(candidate_targets) >= 2:
                second_diff = candidate_targets[1][0]
                if second_diff - best_diff < _ARM_SINGLETON_CLEAR_GAP_DEG:
                    continue
            pair = (best_diff, idx, best_target_idx)
            if best_pair is None or pair < best_pair:
                best_pair = pair
        if best_pair is None:
            return merged

        _diff, source_idx, target_idx = best_pair
        _merge_adjacent_clusters(merged, source_idx=source_idx, target_idx=target_idx)


def _neighbor_cluster_indices(cluster_idx: int, cluster_count: int) -> tuple[int, ...]:
    if cluster_count <= 1:
        return ()
    prev_idx = (cluster_idx - 1) % cluster_count
    next_idx = (cluster_idx + 1) % cluster_count
    if prev_idx == next_idx:
        return (prev_idx,)
    return (prev_idx, next_idx)


def _merge_adjacent_clusters(
    clusters: list[dict[str, Any]],
    *,
    source_idx: int,
    target_idx: int,
) -> None:
    if source_idx == target_idx:
        return
    cluster_count = len(clusters)
    prev_idx = (source_idx - 1) % cluster_count
    next_idx = (source_idx + 1) % cluster_count
    if target_idx not in {prev_idx, next_idx}:
        raise ValueError("arm_merge_target_must_be_adjacent")

    source_cluster = clusters[source_idx]
    if target_idx == prev_idx:
        target_cluster = clusters[target_idx]
        target_cluster["angles"].extend(source_cluster["angles"])
        target_cluster["members"].extend(source_cluster["members"])
        del clusters[source_idx]
        return

    target_cluster = clusters[target_idx]
    target_cluster["angles"] = [*source_cluster["angles"], *target_cluster["angles"]]
    target_cluster["members"] = [*source_cluster["members"], *target_cluster["members"]]
    del clusters[source_idx]


def _sorted_cluster(
    cluster: dict[str, Any],
    *,
    approach_by_id: dict[str, ApproachModel],
) -> dict[str, Any]:
    ordered_members = sorted(
        cluster["members"],
        key=lambda approach_id: (
            approach_by_id[approach_id].side_angle_deg,
            approach_by_id[approach_id].approach_id,
        ),
    )
    return {
        "angles": [approach_by_id[approach_id].side_angle_deg for approach_id in ordered_members],
        "members": ordered_members,
    }


def _cluster_movement_sides(
    cluster: dict[str, Any],
    *,
    approach_by_id: dict[str, ApproachModel],
) -> set[str]:
    return {approach_by_id[approach_id].movement_side for approach_id in cluster["members"]}


def _mean_angle_deg(angles: list[float]) -> float:
    sx = 0.0
    sy = 0.0
    for angle in angles:
        rad = math.radians(angle)
        sx += math.cos(rad)
        sy += math.sin(rad)
    if abs(sx) <= 1e-9 and abs(sy) <= 1e-9:
        return float(angles[0])
    result = math.degrees(math.atan2(sy, sx))
    if result < 0:
        result += 360.0
    return float(result)


def _apply_lateral_ranks(approaches: list[ApproachModel]) -> list[ApproachModel]:
    by_arm_side: dict[tuple[str, str], list[ApproachModel]] = defaultdict(list)
    for approach in approaches:
        by_arm_side[(approach.arm_id, approach.movement_side)].append(approach)

    updated: dict[str, ApproachModel] = {approach.approach_id: approach for approach in approaches}
    for (_arm_id, movement_side), items in by_arm_side.items():
        scored = sorted(items, key=lambda item: _left_rank_key(item, movement_side), reverse=True)
        for rank, approach in enumerate(scored):
            updated[approach.approach_id] = replace(approach, lateral_rank=rank)
    return list(updated.values())


def _left_rank_key(approach: ApproachModel, movement_side: str) -> float:
    point = approach.geometry_ref.point or Point(0.0, 0.0)
    travel_rad = math.radians(approach.travel_angle_deg)
    left_axis = (-math.sin(travel_rad), math.cos(travel_rad))
    return float(point.x * left_axis[0] + point.y * left_axis[1])


def _apply_entry_defaults(approaches: list[ApproachModel]) -> list[ApproachModel]:
    by_arm: dict[str, list[ApproachModel]] = defaultdict(list)
    for approach in approaches:
        if approach.movement_side == "entry":
            by_arm[approach.arm_id].append(approach)

    updated: dict[str, ApproachModel] = {approach.approach_id: approach for approach in approaches}
    for items in by_arm.values():
        unresolved = [
            item
            for item in items
            if item.is_core_signalized_approach == "unknown" and "manual_override:is_core_signalized_approach" not in item.remarks
        ]
        if not unresolved:
            continue
        if len(items) == 1:
            item = unresolved[0]
            updated[item.approach_id] = replace(item, is_core_signalized_approach=True)
            continue
        ordered = sorted(items, key=lambda item: (item.lateral_rank is None, item.lateral_rank if item.lateral_rank is not None else 999))
        if ordered and ordered[0].lateral_rank is not None:
            leftmost_id = ordered[0].approach_id
            for item in unresolved:
                updated[item.approach_id] = replace(item, is_core_signalized_approach=item.approach_id == leftmost_id)
        else:
            for item in unresolved:
                updated[item.approach_id] = replace(item, remarks=item.remarks + ("TODO: core approach inference ambiguous",))
    return list(updated.values())


def _apply_exit_defaults(approaches: list[ApproachModel]) -> list[ApproachModel]:
    by_arm: dict[str, list[ApproachModel]] = defaultdict(list)
    for approach in approaches:
        if approach.movement_side == "exit":
            by_arm[approach.arm_id].append(approach)

    updated: dict[str, ApproachModel] = {approach.approach_id: approach for approach in approaches}
    for items in by_arm.values():
        unresolved = [
            item
            for item in items
            if item.exit_leg_role == "unknown" and "manual_override:exit_leg_role" not in item.remarks
        ]
        if len(items) == 1 and unresolved:
            item = unresolved[0]
            updated[item.approach_id] = replace(item, exit_leg_role="core_standard_exit", is_standard_exit_leg=True)
        for item in items:
            role = updated[item.approach_id].exit_leg_role
            if role in {"core_standard_exit", "service_standard_exit"}:
                standard: bool | str = True
            elif role in {"auxiliary_parallel_exit", "access_exit"}:
                standard = False
            else:
                standard = "unknown"
            updated[item.approach_id] = replace(updated[item.approach_id], is_standard_exit_leg=standard)
    return list(updated.values())


def _build_movements(
    *,
    intersection: IntersectionModel,
    approaches: list[ApproachModel],
    arms: list[ArmModel],
) -> list[MovementCandidate]:
    arm_by_id = {arm.arm_id: arm for arm in arms}
    arm_side_counts = _count_approaches_by_arm_side(approaches)
    entries = [approach for approach in approaches if approach.movement_side == "entry"]
    exits = [approach for approach in approaches if approach.movement_side == "exit"]
    movements: list[MovementCandidate] = []
    for source in entries:
        for target in exits:
            relation = _arm_relation(arm_by_id[source.arm_id], arm_by_id[target.arm_id])
            turn_sense = _derive_turn_sense(source=source, target=target, arm_relation=relation)
            cross_count = _derive_parallel_cross_count(
                source=source,
                target=target,
                arm_side_counts=arm_side_counts,
            )
            remarks: list[str] = []
            if relation == "same":
                remarks.append("same-arm target kept in uturn family; lateral shift remains in parallel_cross_count")
            if cross_count == "unknown":
                remarks.append("TODO: corridor-layer relation could not be stably determined")
            movements.append(
                MovementCandidate(
                    movement_id=f"{intersection.intersection_id}|{approach_key(source.road_id, source.movement_side)}->{approach_key(target.road_id, target.movement_side)}",
                    source=source,
                    target=target,
                    source_arm_id=source.arm_id,
                    target_arm_id=target.arm_id,
                    arm_relation=relation,
                    turn_sense=turn_sense,
                    parallel_cross_count=cross_count,
                    same_signalized_control_zone=source.signalized_control_zone_id == target.signalized_control_zone_id,
                    evidence_refs=source.evidence_refs + target.evidence_refs,
                    remarks=tuple(remarks),
                )
            )
    return movements


def _arm_relation(source_arm: ArmModel, target_arm: ArmModel) -> str:
    if source_arm.arm_id == target_arm.arm_id:
        return "same"
    diff = circular_diff_deg(source_arm.representative_angle_deg, target_arm.representative_angle_deg)
    if diff >= 150.0:
        return "opposite"
    return "adjacent"


def _derive_turn_sense(*, source: ApproachModel, target: ApproachModel, arm_relation: str) -> str:
    if arm_relation == "same":
        return "uturn"
    if arm_relation == "opposite":
        return "through"
    delta = _signed_angle_delta(source.travel_angle_deg, target.travel_angle_deg)
    if abs(delta) < 15.0:
        return "through"
    return "left" if delta > 0 else "right"


def _signed_angle_delta(source_deg: float, target_deg: float) -> float:
    return float((target_deg - source_deg + 180.0) % 360.0 - 180.0)


def _derive_parallel_cross_count(
    *,
    source: ApproachModel,
    target: ApproachModel,
    arm_side_counts: dict[tuple[str, str], int],
) -> int | str:
    source_width = arm_side_counts.get((source.arm_id, source.movement_side), 0)
    target_width = arm_side_counts.get((target.arm_id, target.movement_side), 0)
    if source_width <= 1 or target_width <= 1:
        return 0
    if source.lateral_rank is None or target.lateral_rank is None:
        return "unknown"
    delta = abs(int(source.lateral_rank) - int(target.lateral_rank))
    if delta == 0:
        return 0
    if delta == 1:
        return 1
    return "2+"


def _count_approaches_by_arm_side(approaches: list[ApproachModel]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for approach in approaches:
        counts[(approach.arm_id, approach.movement_side)] += 1
    return counts
