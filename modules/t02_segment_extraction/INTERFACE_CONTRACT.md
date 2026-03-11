# INTERFACE_CONTRACT - t02_segment_extraction

## Inputs
### MUST
- `VerifiedIntersections`
- `Topology`

### SHOULD
- `LaneBoundary` 或其它几何先验

### TBD In Subthread
- 上游输入文件名
- 路段切分的必要字段

## Outputs
### MUST
- `report/metrics.json`
- `report/text_bundle.txt`

### SHOULD
- `Vector/RoadSegmentUnit.*`
- `report/extraction_breakpoints.json`

### TBD In Subthread
- 路段单元主键
- 起止点表达方式
- 路段异常类型

## EntryPoints
> 当前线程不冻结实现入口。

建议占位：
- `python -m normal_topo_poc.modules.t02_segment_extraction.run ...`

## Params
### MUST
- 当前仅冻结参数分类：
  - 最小路段长度
  - 切分容差
  - 标准化开关

### TBD In Subthread
- 具体参数名
- 默认值
- 单位

## Examples
- 待子线程补充

## Acceptance
1. 输出路段单元可追溯到起止约束
2. 路段切分失败有明确原因
3. 文本质检包满足可粘贴约束
