# CodeX Start Here (Normal_Topo_Poc)

## 0. 先读文档（按顺序）
1. `SPEC.md`
2. `docs/PROJECT_BRIEF.md`
3. `docs/AGENT_PLAYBOOK.md`
4. `docs/CODEX_GUARDRAILS.md`
5. `docs/ARTIFACT_PROTOCOL.md`
6. `docs/WORKSPACE_SETUP.md`

## 1. 规则优先级（冲突时按此执行）
`SPEC.md` > `docs/ARTIFACT_PROTOCOL.md` > `docs/CODEX_GUARDRAILS.md` > 其他文档

## 2. 启动握手（必须执行）
在写任何模块代码、创建任何新接口或冻结任何字段之前：
- 输出你的「理解摘要」
- 输出「待确认问题」
- 输出「最小落地计划」
- 等用户确认后再开始模块级细化

## 3. 本阶段禁止事项
- 禁止在主线程自作主张冻结模块字段级 `INTERFACE_CONTRACT`
- 禁止把可执行 Python 实现放进 `modules/<module_id>/`
- 禁止让外传文本依赖图片、文件附件或超长 raw dump

## 4. 目录与代码归属
- 模块文档在 `modules/<module_id>/`
- 实现代码在 `src/normal_topo_poc/modules/<module_id>/`
- 运行产物统一在 `outputs/_work/<module_id>/<run_id>/`
- 所有测试在 `tests/`

## 5. 建议进场检查
- `git rev-parse --show-toplevel`
- `git status -sb`
- `PYTHONPATH=src python -m normal_topo_poc doctor`
