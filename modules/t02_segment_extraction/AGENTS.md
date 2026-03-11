# t02_segment_extraction - 子 GPT Agent 约束（AGENTS）

## 1. 模块定位（当前冻结到范围，不冻结字段）
t02 是路段提取模块，负责基于已核实路口提取标准化路段单元，作为后续路段建模基础。

当前仅冻结：
- 输入类别：`VerifiedIntersections / Topology / Optional LaneBoundary Priors`
- 输出类别：`standardized segments / extraction report / anomaly intervals`
- 运行产物目录：`outputs/_work/t02_segment_extraction/<run_id>/...`

## 2. 当前明确不做
- 不冻结路段切分细则
- 不冻结路段标准化字段
- 不承担 t03 的拓扑构建职责

## 3. 输出约束
- 必含：`report/metrics.json`
- 必含：`report/text_bundle.txt`
- 可选：`Vector/RoadSegmentUnit.*`
- 可选：`report/extraction_breakpoints.json`

## 4. 质量闸门（当前）
- 每个输出路段单元必须可追溯到其起止路口或边界原因
- 路段标准化结果必须可枚举失败原因
- 无法稳定切分的区域必须生成断点摘要

## 5. 子线程目标
- 冻结路段切分逻辑
- 冻结标准化路段单元 schema
- 冻结异常类型与验收指标
