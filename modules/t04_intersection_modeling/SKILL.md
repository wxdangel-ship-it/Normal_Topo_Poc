# SKILL.md

## What

`T04 - 复杂交叉路口建模` 负责把普通道路复杂交叉路口抽象为结构化 bundle，并产出 entry -> exit 的 movement 级默认通行结论。

本模块当前是一次保真迁移实现，默认目标是保留既有行为、测试语义和配套产物能力。

## 历史来源

本模块的 Phase-1 迁移来源是 `Highway_Topo_Poc` 的 `T10 - 复杂交叉路口建模`。除本节外，不应继续在实际模块命名、import、CLI、测试调用中使用旧命名。

## Why

使用本模块时，通常是为了完成以下任务之一：
- 对单个路口执行 movement 建模与裁决
- 通过 manual override 覆盖服务路画像或配对主路关系
- 产出 `serialized_bundle`、`movement_results`、`movement_matrix`、summary 等审查工件
- 运行 patch dir / multi-patch / baseline regression / snapshot diff
- 复用迁移来源已有的 review cycle 和 writer 协议

## Inputs

本模块支持的输入形态包括：
- `RCSDNode.geojson` / `RCSDRoad.geojson`
- 手工构造的 node / road feature 列表
- patch dir（含 `Vector/RCSDNode.geojson` 与 `Vector/RCSDRoad.geojson`）
- manual override JSON 或同结构字典
- approach override 字典
- baseline manifest 与 snapshot 目录

关键输入语义：
- `mainid` 用于收口单个信号控制区
- `manual_override_source` 用于注入 `service_profile_map` 和 `paired_mainline_map`
- `approach_overrides` 用于最小化覆写 `approach_profile`、`exit_leg_role`、`is_core_signalized_approach` 等字段

## Outputs

结构化输出包括：
- `IntersectionBundle`
- movement decision 列表
- movement matrix 视图
- patch batch / multi-patch / regression summary

默认落盘工件包括：
- `serialized_bundle.json`
- `movement_results.json`
- `movement_matrix.json`
- `summary.txt`
- batch 或 regression manifest / summary

## Workflow

1. 读取 node / road 输入，并按 `mainid` 选定单个控制区。
2. 在 `T04.2` 中构建 `IntersectionModel`、`ArmModel`、`ApproachModel`。
3. 归一化 `approach_profile`、`exit_leg_role`、`same_signalized_control_zone` 等判定字段。
4. 在 `T04.3` 中计算 `turn_sense`、`parallel_cross_count` 并输出 movement 状态。
5. 使用 writer、review、baseline、snapshot 工具链落盘或比较结果。

## Key Semantics

迁移阶段应保持以下业务内核不变：
- 场景范围是标准信号控制的平面复杂交叉路口
- 结果状态固定为 `allowed` / `allowed_with_condition` / `forbidden` / `unknown`
- `mainid` 是当前 MVP 的信号控制区收口主键
- `turn_sense` 解决“往哪转”，`parallel_cross_count` 解决“跨几层平行走廊”，二者正交
- `left_uturn_service`、`paired_mainline_no_left_uturn`、`core_standard_exit`、`service_standard_exit` 等语义优先保留
- 目标出口角色、manual override、review bundle、baseline/diff 都属于正式能力，不是历史残留

## Non-Goals

当前不把本模块扩展为：
- 非信号控制路口建模
- 环岛、立交、互通、lane-level 建模
- 实时交通或实时配时预测
- 面向全仓库的大重构入口

## Working Rule

使用本模块时遵循以下原则：
- 保真优先于优雅
- 先机械迁移，再做最小修正
- 能通过命名适配解决的问题，不提前抽象重构
- 若发现 Highway 侧依赖无法直接平移，优先做最小兼容或显式记录阻塞

补充说明见：
- `modules/t04_intersection_modeling/INTERFACE_CONTRACT.md`
- `modules/t04_intersection_modeling/PHASE2_USAGE.md`
- `modules/t04_intersection_modeling/REVIEW_USAGE.md`
- `modules/t04_intersection_modeling/PHASE7_BASELINE.md`
- `modules/t04_intersection_modeling/PHASE11_RC.md`
