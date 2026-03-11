# INTERFACE_CONTRACT - t03_segment_construction

## Inputs
### MUST
- `Intersections`
- `SegmentUnits`
- `Topology`

### SHOULD
- `PointCloud`
- `IsolatedElements`

### TBD In Subthread
- 输入关系的最小字段集合
- 拓扑先验证据的用法

## Outputs
### MUST
- `report/metrics.json`
- `report/text_bundle.txt`

### SHOULD
- `Vector/RoadSegmentTopology.*`
- `report/topology_breakpoints.json`

### TBD In Subthread
- 图结构 schema
- 异常分类
- 供 t04 消费的关系表达

## EntryPoints
> 当前线程不冻结实现入口。

建议占位：
- `python -m normal_topo_poc.modules.t03_segment_construction.run ...`

## Params
### MUST
- 当前仅冻结参数分类：
  - 连通性阈值
  - 冲突消解策略开关
  - 孤立边容忍度

### TBD In Subthread
- 具体参数名
- 默认值
- 单位

## Examples
- 待子线程补充

## Acceptance
1. 输出路段拓扑可被审计
2. 异常连接有清晰枚举
3. 文本质检包满足可粘贴约束
