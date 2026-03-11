# ARTIFACT_PROTOCOL（全局）- 文本粘贴回传优先

- 项目：Normal_Topo_Poc
- 版本：v1.0
- 目的：定义「内部执行后 -> 外部分析」唯一允许的回传形态（文本粘贴）
- 适用范围：t01-t04 全模块；batch 汇总同理

---

## 0. 总原则（硬约束）
1. 回传方式：仅允许文本粘贴
2. 内容要求：体积可控、结构清晰、可直接归因
3. 内容风格：优先分位数、阈值、问题类型、严重程度、Top-K 摘要
4. 体积控制：超长必须截断并给出摘要

---

## 1. 内容建议

### 1.1 允许（推荐）
- 指标分位数：`p50 / p90 / p99`
- 阈值与关键参数摘要
- 计数、比例、长度占比
- 索引化位置：`bin` 区间
- 匿名 PatchID / RunID / ConfigDigest
- 自动修正计数、人工断点计数、失败原因枚举

### 1.2 不推荐
- 大段逐要素明细
- 整段原始 GeoJSON / WKT / 顶点数组
- 冗长日志和绝对路径噪声

---

## 2. 位置表达：Index Bin 区间
- 每个 patch 运行时定义一个单调标量轴，例如：`seq / t / s`
- 将标量轴离散为 N 个 bin（推荐 `N=1000`）
- 位置仅用 `[bin_start, bin_end]` 与 `len_pct` 表达

---

## 3. 外传文本包格式：TEXT_QC_BUNDLE v1

### 3.1 体积上限
- 每个 `(patch, module)` 文本块：`<=120 行` 或 `<=8KB`
- 超出后必须只保留：
  - 关键头部
  - Metrics Top-N
  - Intervals Top-3
  - Errors Top-3
  - `Truncated: true`

### 3.2 标准模板
```text
=== Normal_Topo_Poc TEXT_QC_BUNDLE v1 ===
Project: Normal_Topo_Poc
Run: <run_id>  Commit: <short_sha_or_tag>  ConfigDigest: <8-12chars>
Patch: <patch_uid_or_alias>  Provider: <file|sample|prod>  Seed: <int_or_na>
Module: <t01|t02|t03|t04>  ModuleVersion: <semver_or_sha>

Inputs: intersections=<ok|missing>  topo=<ok|missing>  pc=<ok|missing>  isolated=<ok|missing>  laneinfo=<ok|missing>  traj=<ok|missing>
InputMeta: <type/resolution/field_availability_summary>

Params(TopN<=12): <k1=v1; k2=v2; ...>

Metrics(TopN<=10):
- <metric_name_1>: p50=<num> p90=<num> p99=<num> threshold=<num|na> unit=<...>
- <metric_name_2>: p50=<num> p90=<num> p99=<num> threshold=<num|na> unit=<...>

Intervals(binN=<N>):
- type=<enum>  count=<int>  total_len_pct=<num%>
  top3=(<b0>-<b1>, severity=<low|med|high>, len_pct=<%>); (<b0>-<b1>, ...); (<b0>-<b1>, ...)

Breakpoints: [<enum1>, <enum2>, ...]
Errors: [<reason_enum>:<count>, <reason_enum>:<count>, ...]
Notes: <1-3 lines max>
Truncated: <true|false> (reason=<na|size_limit|...>)
=== END ===
```

---

## 4. Batch 汇总文本（可选）
- 上限：`<=200 行` 或 `<=16KB`
- 内容：
  - 每模块 `ok/warn/fail` 计数
  - Top 错误原因
  - Top 断点
  - Top 区间类型

---

## 5. 与本地文件的关系
- 内部可以生成本地文件用于排查
- 外部分析只依赖 `TEXT_QC_BUNDLE`
- 模块实现不得要求外部读取内部文件
