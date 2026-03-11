# INTERFACE_CONTRACT.md

Module: `T04 - 复杂交叉路口建模`

Scope:
- 标准信号控制
- 平面复杂交叉路口
- movement 级默认通行建模
- manual override / review / baseline / diff / patch runner

Out of Scope:
- 环岛、立交、互通
- 非信号控制场景
- lane-level 精细建模
- 实时交通与实时信号
- `T04.4` 的完整显式规则体系

## Inputs

支持以下输入形态：
- 单路口手工输入：`node_features`、`road_features`
- 文件输入：`RCSDNode.geojson`、`RCSDRoad.geojson`
- patch dir 输入：包含 `Vector/RCSDNode.geojson` 与 `Vector/RCSDRoad.geojson`
- batch 输入：patch root 下多个 patch 子目录
- 覆写输入：manual override JSON / dict、`approach_overrides`
- 基线输入：`T04_BASELINE_MANIFEST.json`、snapshot 目录

最小输入语义要求：
- node 要能提供 `id` 与 `mainid`
- road 要能提供几何、`snodeid`、`enodeid`、方向信息
- `mainid` 用于收口单个信号控制区
- manual override 至少支持 `service_profile_map` 与 `paired_mainline_map`

业务输入边界：
- 以普通道路复杂交叉路口为对象
- 默认判定只处理单个 movement 的理论成立性
- 字段名允许与底层真值字段不同，但必须能映射到既有数据语义

## Outputs

核心结构化输出：
- `IntersectionBundle`
- movement decision 列表
- movement matrix
- patch batch / multi-patch / regression summary

单路口默认落盘输出：
- `serialized_bundle.json`
- `movement_results.json`
- `movement_matrix.json`
- `summary.txt`

批处理或基线附加输出：
- `manifest.json`
- `summary.txt`
- `regression_manifest.json`
- `regression_summary.txt`
- review bundle 与 diff 相关产物

默认输出目录：
- `outputs/_work/t04_intersection_modeling/<run_id>/...`

判定结果状态固定为：
- `allowed`
- `allowed_with_condition`
- `forbidden`
- `unknown`

## EntryPoints

CLI：
- `python -m normal_topo_poc.modules.t04_intersection_modeling.cli`

常用 API：
- `run_t04_single_intersection_manual_mode`
- `run_t04_single_intersection_from_geojson_files`
- `run_t04_single_intersection_from_patch_dir`
- `run_t04_all_intersections_from_patch_dir`
- `run_t04_multi_patch_manual_mode`
- `run_t04_baseline_regression_smoke`
- `compare_t04_output_dir_to_snapshot`
- `write_t04_run_result`
- `write_t04_patch_batch_result`

模块职责分层：
- `T04.1`：虚拟样例与手工输入组织
- `T04.2`：bundle / arm / approach 建模
- `T04.3`：默认规则裁决
- `T04.4`：显式规则扩展预留，不在本阶段实现范围内

配套说明文档：
- `modules/t04_intersection_modeling/PHASE2_USAGE.md`
- `modules/t04_intersection_modeling/REVIEW_USAGE.md`
- `modules/t04_intersection_modeling/PHASE7_BASELINE.md`
- `modules/t04_intersection_modeling/PHASE11_RC.md`
- `modules/t04_intersection_modeling/INTERNAL_WSL_USAGE.md`

## Params

核心参数：
- `mainid`: 指定单个信号控制区；未指定且存在多个 `mainid` 时应报错
- `node_features` / `road_features`: 手工或内存输入
- `node_geojson_path` / `road_geojson_path`: 单文件输入
- `patch_dir` / `patch_root`: patch 目录或 patch 根目录
- `output_dir` / `output_root`: 产物写出位置
- `manual_override_source`: JSON 文件路径或同结构字典
- `approach_overrides`: approach 级字段覆写

关键业务参数语义：
- `approach_profile` 支持 `default_signalized`、`left_uturn_service`、`paired_mainline_no_left_uturn`、`unknown`
- `exit_leg_role` 支持 `core_standard_exit`、`service_standard_exit`、`auxiliary_parallel_exit`、`access_exit`、`unknown`
- `turn_sense` 与 `parallel_cross_count` 为派生字段，不要求外部直接提供
- `same_signalized_control_zone` 当前 MVP 口径由 `mainid` 归一化得出

错误处理约定：
- 输入缺关键文件、指定 `mainid` 不存在、manual override 引用了不存在的 road / approach、或工件结构不合法时，应抛出显式错误
- 对业务上无法稳定识别的情况，优先输出 `unknown` 或 `breakpoint`，不做 silent guess

## Examples

单路口文件模式：

```bash
PYTHONPATH=src python -m normal_topo_poc.modules.t04_intersection_modeling.cli \
  --node-file data/RCSDNode.geojson \
  --road-file data/RCSDRoad.geojson \
  --mainid 100 \
  --output-dir outputs/_work/t04_intersection_modeling/example_single
```

patch dir 全量模式：

```bash
PYTHONPATH=src python -m normal_topo_poc.modules.t04_intersection_modeling.cli \
  --patch-dir data/patch_001 \
  --all-mainids \
  --output-dir outputs/_work/t04_intersection_modeling/example_patch
```

multi-patch + manual override：

```bash
PYTHONPATH=src python -m normal_topo_poc.modules.t04_intersection_modeling.cli \
  --patch-root data/patch_root \
  --override-root data/override_root \
  --output-dir outputs/_work/t04_intersection_modeling/example_multi_patch
```

基线回归：

```python
from normal_topo_poc.modules.t04_intersection_modeling import run_t04_baseline_regression_smoke

summary = run_t04_baseline_regression_smoke()
```

## Acceptance

本阶段至少满足：
- 模块文档已切换为 `T04 / Normal_Topo_Poc` 正式模块语境
- `src/normal_topo_poc/modules/t04_intersection_modeling/` 可成功导入
- CLI 入口 `python -m normal_topo_poc.modules.t04_intersection_modeling.cli --help` 可用
- `python -m compileall src tests` 通过
- 若环境具备 `pytest`，`tests/t04_intersection_modeling/` 可执行并给出真实通过/失败结果
- 除明确的历史来源说明外，模块内不残留旧项目命名
- manual override、review、baseline、diff、patch runner 等既有能力未被静默删除
