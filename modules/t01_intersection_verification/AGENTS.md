# t01_intersection_verification - 子 GPT Agent 约束（AGENTS）

## 1. 模块定位（当前冻结到范围，不冻结字段）
t01 是路口核实模块，负责基于已有路口、拓扑、点云、孤立要素信息，核实路口属性是否满足后续建模要求，并输出自动修正结果或人工介入断点。

当前仅冻结：
- 输入类别：`Intersection / Topology / PointCloud / IsolatedElements`
- 输出类别：`verified intersections / anomaly report / manual breakpoints`
- 运行产物目录：`outputs/_work/t01_intersection_verification/<run_id>/...`

## 2. 当前明确不做
- 不在本阶段冻结字段级 schema、文件命名和阈值
- 不替代 t02 / t03 / t04 的职责
- 不回写原始 patch 数据

## 3. 输出约束
- 必含：`report/metrics.json`
- 必含：`report/text_bundle.txt`
- 可选：`Vector/IntersectionVerified.*`
- 可选：`report/manual_breakpoints.json`

## 4. 质量闸门（当前）
- 每个输入路口必须落入 `pass / auto_fixed / manual_review / error` 之一
- 自动修正必须带规则名与证据摘要
- 人工介入原因必须枚举化

## 5. 子线程目标
- 冻结输入输出字段
- 冻结自动修正规则与人工介入断点枚举
- 冻结运行入口与最小验收样例
