# Normal_Topo_Poc - Agent Playbook (Global)

## 1. 角色分工
### 1.1 主智能体（当前主线程）
负责：
- 冻结项目级目录、项目级文档、通用协议与最小公共工具
- 维持所有模块共享的约束与命名方式

不负责：
- 直接冻结任一模块的字段级接口契约
- 在没有子线程确认的情况下指定业务阈值或修正规则

### 1.2 模块子智能体（后续子线程）
负责：
- 单模块需求澄清
- 在对应模块目录内补齐 `INTERFACE_CONTRACT.md`
- 推进该模块实现、测试、验收样例

规则：
- 每个模块单独一个子线程，避免跨模块文档冲突

## 2. 文档分层
- 全局文档：根目录 `docs/`
- 模块文档：`modules/<module_id>/`
- 源码实现：`src/normal_topo_poc/modules/<module_id>/`

## 3. 模块文档最小集合
每个模块目录必须包含：
- `AGENTS.md`
- `SKILL.md`
- `INTERFACE_CONTRACT.md`

## 4. 代码承载规则
- 禁止在 `modules/<module_id>/` 放置 `.py` 实现
- 模块测试放在 `tests/`
- 运行产物统一放在 `outputs/_work/`

## 5. 协作准则
- 主线程只冻结公共规则和骨架
- 子线程只修改自己的模块目录与对应源码目录
- 涉及文本回传的变更，必须遵守 `docs/ARTIFACT_PROTOCOL.md`
