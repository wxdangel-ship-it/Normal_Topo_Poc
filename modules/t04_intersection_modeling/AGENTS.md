# AGENTS.md

## 模块定位

你正在 `Normal_Topo_Poc` 的正式模块 `T04 - 复杂交叉路口建模` 中工作。

本阶段目标不是重做设计，而是把既有能力平移到当前仓库、统一命名，并在当前工程骨架下跑通。

## 历史来源

本模块的 Phase-1 实现来源于 `Highway_Topo_Poc` 的 `T10 - 复杂交叉路口建模`。除本节外，不应在实际模块命名、import、CLI、测试调用中继续保留旧命名。

当前默认关注点：
- 普通道路复杂交叉路口
- movement 级理论通行建模
- manual override
- review cycle / review bundle
- baseline / diff / snapshot regression
- patch dir / dataset runner / multi-patch runner

当前默认不做：
- 借迁移之机重构业务规则
- 扩大模块业务范围
- 改写其它模块
- lane-level、实时交通、实时信号等扩展设计

## 工程边界

遵守当前仓库的目录约定：
- 文档与契约放 `modules/t04_intersection_modeling/`
- 实现代码放 `src/normal_topo_poc/modules/t04_intersection_modeling/`
- 测试放 `tests/t04_intersection_modeling/`
- fixtures 放 `tests/fixtures/t04_intersection_modeling/`
- 运行输出放 `outputs/_work/t04_intersection_modeling/<run_id>/`

除非确有接线需要，不修改其它模块目录。

## 当前线程工作原则

1. 先以迁移来源模块为行为真值，优先做机械迁移和命名适配。
2. 迁移后只做最小修正，目标是导入、CLI、测试、产物落盘可运行。
3. 若发现迁移来源模块依赖原仓库主线上下文，优先做最小隔离或显式记录阻塞，不静默删除能力。
4. 只有在当前仓库约定与原实现明显冲突时，才做必要改写。

## 业务冻结口径

当前应保持与迁移来源一致的核心语义：
- 场景范围：标准信号控制、平面复杂交叉路口
- 结果状态：`allowed` / `allowed_with_condition` / `forbidden` / `unknown`
- 模块分层：`T04.1` / `T04.2` / `T04.3` / `T04.4`
- 建模核心：`IntersectionModel` / `ArmModel` / `ApproachModel`
- 关键能力：`approach_profile`、`exit_leg_role`、`turn_sense`、`parallel_cross_count`
- 配套能力：manual override、review bundle、baseline regression、snapshot diff、patch runner

## 真值与映射原则

- 高层文档中的字段名是业务语义字段，不等于底层原始字段名。
- 对底层数据的读取、归一化和派生，应优先对齐既有实现与仓库文档。
- 遇到无法稳定识别的字段或关系，输出 `unknown`、`breakpoint` 或显式错误，不做 silent guess。

## 文档与实现协同

本模块的最小参考顺序：
1. `modules/t04_intersection_modeling/INTERFACE_CONTRACT.md`
2. `modules/t04_intersection_modeling/PHASE2_USAGE.md`
3. `modules/t04_intersection_modeling/REVIEW_USAGE.md`
4. `modules/t04_intersection_modeling/PHASE7_BASELINE.md`
5. `modules/t04_intersection_modeling/PHASE11_RC.md`
6. `modules/t04_intersection_modeling/INTERNAL_WSL_USAGE.md`

当文档与代码出现冲突时：
- 迁移阶段优先保留原始实现既有行为；
- 但新命名、目录、CLI 路径、输出路径必须服从当前仓库约定。

## 禁止事项

- 不要把实现代码写进 `modules/t04_intersection_modeling/`
- 不要顺手改动 `t00` 到 `t03` 或其它模块
- 不要未经说明地删除迁移来源已有测试、fixtures 或产物协议
- 不要把旧项目命名残留在实际模块命名、import、CLI、测试调用中

## 交付关注点

本模块交付时至少应满足：
- 文档已切换为 `T04 / Normal_Topo_Poc` 语境
- `src/normal_topo_poc/modules/t04_intersection_modeling/` 可导入
- `python -m normal_topo_poc.modules.t04_intersection_modeling.cli --help` 可用
- `python -m compileall src tests` 通过
- 若环境具备 `pytest`，`tests/t04_intersection_modeling/` 可执行并给出真实结果
