# CodeX Guardrails (Global, MUST FOLLOW)

## 0. 总原则：Stop -> Ask -> Do
- 任何会冻结模块字段、输出格式、关键命名的改动，先确认再做
- 当前主线程允许创建模块文档骨架，但不允许擅自补完细节契约

## 1. 必须先问的触发条件
- 真实输入目录与文件命名需要冻结时
- 红绿灯绑定规则、LaneInfo 语义、轨迹通量定义需要冻结时
- 文本回传格式需要突破 `TEXT_QC_BUNDLE v1` 约束时

## 2. 文本回传硬约束
- 只允许可粘贴文本
- 体积建议：`<=120 行` 或 `<=8KB`
- 超限时必须截断并标记 `Truncated: true`
- 避免超长 raw dump，优先 Top-K / 摘要 / 区间表达

## 3. 代码承载硬约束
- `modules/<module_id>/` 仅承载文档
- 新增实现代码默认放 `src/normal_topo_poc/modules/<module_id>/`
- 新增测试默认放 `tests/`
- 运行产物统一写入 `outputs/_work/<module_id>/<run_id>/`

## 4. 文档结构硬约束
- `INTERFACE_CONTRACT.md` 章节顺序固定：
  `Inputs` / `Outputs` / `EntryPoints` / `Params` / `Examples` / `Acceptance`

## 5. 当前阶段的边界
- 可以搭仓库骨架
- 可以搭通用 CLI / 协议 / 测试
- 不可以跳过子线程直接把业务细节写死
