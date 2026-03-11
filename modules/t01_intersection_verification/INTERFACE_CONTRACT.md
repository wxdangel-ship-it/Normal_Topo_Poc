# INTERFACE_CONTRACT - t01_intersection_verification

## Inputs
### MUST
- `Intersection`
- `Topology`
- `PointCloud`
- `IsolatedElements`

### TBD In Subthread
- 文件命名
- 字段级 schema
- 证据聚合方式

## Outputs
### MUST
- `report/metrics.json`
- `report/text_bundle.txt`

### SHOULD
- `Vector/IntersectionVerified.*`
- `report/manual_breakpoints.json`

### TBD In Subthread
- 状态枚举
- 自动修正记录格式
- 证据对象格式

## EntryPoints
> 当前线程不冻结实现入口。

建议占位：
- `python -m normal_topo_poc.modules.t01_intersection_verification.run ...`

## Params
### MUST
- 当前不冻结字段，仅保留参数分类：
  - 自动修正开关
  - 人工断点上限
  - 核实阈值组

### TBD In Subthread
- 具体参数名
- 默认值
- 单位

## Examples
- 待子线程补充最小 patch 示例

## Acceptance
1. 每个输入路口都有明确结果状态
2. 自动修正可追溯
3. 人工介入原因可枚举
4. 文本质检包满足可粘贴约束
