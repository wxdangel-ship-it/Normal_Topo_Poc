# t03_segment_construction - 子 GPT Agent 约束（AGENTS）

## 1. 模块定位（当前冻结到范围，不冻结字段）
t03 是路段构建模块，负责基于路口、拓扑、点云、孤立要素等构建当前路段拓扑。

当前仅冻结：
- 输入类别：`Intersections / SegmentUnits / Topology / PointCloud / IsolatedElements`
- 输出类别：`segment topology / connectivity diagnostics / exception report`
- 运行产物目录：`outputs/_work/t03_segment_construction/<run_id>/...`

## 2. 当前明确不做
- 不冻结图结构 schema
- 不提前确定多源冲突优先级
- 不承担 t04 的路口 movement 建模职责

## 3. 输出约束
- 必含：`report/metrics.json`
- 必含：`report/text_bundle.txt`
- 可选：`Vector/RoadSegmentTopology.*`
- 可选：`report/topology_breakpoints.json`

## 4. 质量闸门（当前）
- 连通关系必须可审计
- 孤立边、冲突连接、缺失连接必须有枚举摘要
- 输出必须支持后续路口建模消费

## 5. 子线程目标
- 冻结拓扑图实体与关系 schema
- 冻结冲突消解策略
- 冻结核心质量指标
