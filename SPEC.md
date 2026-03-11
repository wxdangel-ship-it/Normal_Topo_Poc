# SPEC: 普通道路场景「路网拓扑自动生产」关键技术 POC 说明（Normal_Topo_Poc）

- 文档类型：需求规格说明（Specification）
- 项目名称：Normal_Topo_Poc
- 版本：v0.1
- 状态：Draft
- 交付形态：本地仓库 + 模块级子线程推进 + 质量验收文本回传
- 参考基线：完全参考 `E:\Work\Highway_Topo_Poc` 的项目级文档结构、目录约定、文本质检回传约束

---

## 目录
1. 项目概述
2. 目标与成功标准
3. 范围与非目标
4. 关键约束与假设
5. 协作闭环与工件协议
6. 交付物清单
7. 术语与统一定义
8. Patch/Provider 数据接口原则
9. 标准化报告与文本质检包规范
10. 模块目录与代码组织要求
11. 四个关键技术模块
12. 配置、运行、可复现与审计要求
13. 测试、回归与验收要求
14. 隐私与脱敏约束
15. 风险、依赖与待澄清项
16. 附录：示例配置骨架

---

## 1. 项目概述

### 1.1 项目目标
在普通道路场景下，对「路网拓扑自动生产」关键技术做 POC 论证，并对若干关键内部能力进行质量验收。目标不是一次性冻结生产方案，而是先建立：
- 可运行的仓库骨架
- 可拆分推进的模块边界
- 可回传的质量验收文本协议
- 可在后续子线程中逐模块细化的文档与实现承载方式

### 1.2 当前纳入论证的关键技术点
- t01 路口核实：
  基于已有路口、拓扑、点云、孤立要素信息，核实路口属性是否满足后续建模要求，并自动修正或触发人工介入。
- t02 路段提取：
  基于核实后的路口，提取标准化的路段单元，作为后续路段建模基础。
- t03 路段构建：
  基于路口、拓扑、点云、孤立要素等构建当前路段拓扑。
- t04 路口建模：
  基于进入路口的路段、LaneInfo、轨迹通量及其他语义孤立要素，构建路口通行关系及红绿灯绑定关系。

### 1.3 当前阶段推进策略
- 本线程仅负责：
  - 搭建仓库结构
  - 冻结项目级规则与目录约定
  - 创建模块级文档骨架
  - 提供最小 CLI / 文本协议 / 测试骨架
- 每个模块的字段级输入输出、算法细节、阈值、异常枚举、运行入口，在后续子线程分别推进。

---

## 2. 目标与成功标准

### 2.1 POC 成功标准
必须满足：
- 可拆分推进：四个模块各自有独立目录、独立文档三件套、独立源码目录与测试落点。
- 可诊断：任一模块后续都能输出可粘贴的 TEXT_QC_BUNDLE，支持外部基于文本做归因。
- 可复现：配置、版本、关键参数、输入摘要必须能记录。
- 可审计：自动修正、人工介入断点、失败原因必须以结构化摘要表达。
- 可扩展：项目级文档不提前冻结模块细节，避免阻塞子线程迭代。

### 2.2 当前最小验收范围
- 仓库目录完整，且符合参考项目的分层约定。
- 项目级文档可直接作为后续子线程公共基线。
- 模块级占位文档包含统一章节结构，可在子线程中无缝补全。
- CLI 可执行 `doctor`、`qc-template`、`qc-demo`、`lint-text`。
- 基础测试可通过。

---

## 3. 范围与非目标

### 3.1 范围
- 普通道路场景下的四个关键技术模块。
- 项目级文档、模块级文档、src-layout 包结构、基础测试、文本质检回传协议。
- 质量验收的文本输出约束与最小工具能力。

### 3.2 非目标
- 当前线程不实现具体业务算法。
- 当前线程不冻结模块字段级 `INTERFACE_CONTRACT`。
- 当前线程不引入批处理编排、真实数据 Provider 适配、图形化可视化或生产级阈值。
- 当前线程不回写任何真实业务数据目录。

---

## 4. 关键约束与假设

### 4.1 文档与代码分层约束
- 模块文档仅放在 `modules/<module_id>/`。
- 真实实现代码仅放在 `src/normal_topo_poc/modules/<module_id>/`。
- 测试统一放在 `tests/`。
- 运行产物统一落在 `outputs/_work/<module_id>/<run_id>/`。

### 4.2 文本回传约束
- 如涉及内网真实数据验收回传，默认只允许文本粘贴。
- 文本体积建议控制在 `<=120 行` 或 `<=8KB`。
- 问题定位优先使用分位数、区间摘要、Top-K、断点枚举，避免 raw dump。

### 4.3 当前全局不冻结的内容
- 各模块输入文件命名
- 字段级 schema
- 自动修正规则与阈值
- Provider 的真实适配路径
- LaneInfo / Traj / 孤立要素的精确定义

### 4.4 工作区约束
- 仓库根目录位于 Windows `E:` 盘。
- 推荐使用 WSL + Python 执行。
- 尽量使用相对路径，减少环境耦合。

---

## 5. 协作闭环与工件协议

### 5.1 协作方式
- 主线程：
  维护项目级规则、目录与通用工具。
- 子线程：
  每次聚焦一个模块，补齐该模块的接口契约、实现方案与质量验收细则。

### 5.2 内外协作闭环
- 外部侧：
  维护仓库、实现通用工具、消费文本验收结果、给出迭代建议。
- 内部侧：
  跑真实数据、生成本地产物与文本质检包、以粘贴文本回传。

### 5.3 运行时工件
- 本地文件：
  `report/metrics.json`、`report/artifact_index.json`、模块产物、辅助诊断文件。
- 外传文本：
  `TEXT_QC_BUNDLE v1`

---

## 6. 交付物清单

### 6.1 当前仓库交付
- `SPEC.md`
- `docs/`
- `modules/`
- `src/normal_topo_poc/`
- `tests/`
- `configs/`
- `scripts/`
- `data/`
- `outputs/`
- `tools/`

### 6.2 后续模块交付
- 每个模块的 `AGENTS.md` / `SKILL.md` / `INTERFACE_CONTRACT.md`
- 模块实现代码
- 模块测试
- 模块质量验收样例

---

## 7. 术语与统一定义
- Patch：
  最小处理单元，可对应一个地理区域、一批关联图层或一次拓扑生产任务。
- Provider：
  将真实输入组织成统一读取对象的适配层。
- Isolated Elements：
  带语义但不直接属于主路网主干结构的孤立要素。
- LaneInfo：
  路口建模使用的车道级属性或通行先验。
- Trajectory Flux：
  轨迹流量、通行方向或通行强度摘要。
- Breakpoint：
  自动流程无法稳定决策时输出的人工复核断点。

---

## 8. Patch/Provider 数据接口原则

### 8.1 当前仅冻结输入类别，不冻结文件名
建议后续 Provider 至少覆盖以下输入类别：
- `Intersection`
- `Topology`
- `PointCloud`
- `IsolatedElements`
- `LaneInfo`
- `Trajectory`
- `Tiles`（如需要图像先验）

### 8.2 推荐的 Patch 目录组织
以下仅作为建议骨架，字段与命名后续按模块子线程冻结：

```text
<PatchID>/
  Intersection/
  Topology/
  PointCloud/
  Vector/
  LaneInfo/
  Traj/
  Tiles/
```

### 8.3 全局原则
- 不强制内部原始目录结构直接修改。
- 允许通过 Provider 在运行时完成标准化。
- 项目主文档只维护类别级约束，模块细节以各自 `INTERFACE_CONTRACT.md` 为准。

---

## 9. 标准化报告与文本质检包规范

### 9.1 本地文件
- `report/metrics.json`：完整诊断指标
- `report/artifact_index.json`：产物索引
- 其它模块自定义工件：允许存在，但不作为外传依赖

### 9.2 外传文本
- 必须遵守 `docs/ARTIFACT_PROTOCOL.md`
- 必须支持：
  - Metrics：p50 / p90 / p99 + threshold
  - Intervals：bin 区间 + Top-K
  - Breakpoints：人工复核断点枚举
  - Errors：失败原因枚举
  - Params：关键参数摘要

---

## 10. 模块目录与代码组织要求
- 每个关键技术点一个模块目录。
- 模块目录仅承载文档，不承载 `.py` 实现。
- `INTERFACE_CONTRACT.md` 章节顺序固定：
  `Inputs` / `Outputs` / `EntryPoints` / `Params` / `Examples` / `Acceptance`
- 源码目录与模块目录命名保持一致。
- 测试命名建议：`test_<module_id>_*.py`

模块树：
```text
modules/
  t01_intersection_verification/
  t02_segment_extraction/
  t03_segment_construction/
  t04_intersection_modeling/
```

---

## 11. 四个关键技术模块

### 11.1 t01_intersection_verification
- 目标：
  核实路口属性是否满足后续建模要求。
- 关心的输出：
  pass / auto_fixed / manual_review / error 的分类结果与依据摘要。

### 11.2 t02_segment_extraction
- 目标：
  从核实后的路口出发，提取标准化路段单元。
- 关心的输出：
  路段单元集合、端点归属、标准化结果摘要与异常段落。

### 11.3 t03_segment_construction
- 目标：
  基于多源信息构建当前路段拓扑。
- 关心的输出：
  路段连通关系、缺失连接、冲突连接、孤立边等质量摘要。

### 11.4 t04_intersection_modeling
- 目标：
  构建路口通行关系及红绿灯绑定关系。
- 关心的输出：
  movement 集合、lane-to-movement 关系、signal binding 结果、人工复核断点。

---

## 12. 配置、运行、可复现与审计要求
- 记录：`run_id`、`module_version`、`config_digest`、关键参数摘要、输入摘要
- 支持：单模块独立运行
- 预留：后续 patch list 批处理能力
- 统一：所有产物只写到 `outputs/_work/`

---

## 13. 测试、回归与验收要求
- 当前阶段至少包含：
  - 文本质检协议测试
  - CLI 烟测
  - 仓库医生检查
- 后续每个模块补充：
  - schema/契约测试
  - 最小合成样例
  - 质量验收 golden 文本对比

---

## 14. 隐私与脱敏约束
- 不在文本回传中附带超长坐标、点云片段或整段原始对象。
- 优先用统计摘要、匿名 PatchID、Top-K 区间表达问题。
- 若文本超限，必须截断并标记 `Truncated: true`。

---

## 15. 风险、依赖与待澄清项
- 路口、路段、孤立要素、LaneInfo 的精确定义仍需业务确认。
- 普通道路场景是否需要和历史先验拓扑强绑定，尚未冻结。
- 红绿灯绑定的语义来源、优先级和缺失补偿策略，需在 t04 子线程明确。
- 是否增加合成数据模块，当前未纳入。

---

## 16. 附录：示例配置骨架

```yaml
run:
  run_id: "2026-03-11_01"
  output_dir: "outputs/${run.run_id}"
  seed: 42

provider:
  type: "file_patch"
  data_root: "${DATA_ROOT}"
  patch_manifest: "configs/patch_list.json"

modules:
  t01_intersection_verification:
    enabled: true

  t02_segment_extraction:
    enabled: true

  t03_segment_construction:
    enabled: true

  t04_intersection_modeling:
    enabled: true
```
