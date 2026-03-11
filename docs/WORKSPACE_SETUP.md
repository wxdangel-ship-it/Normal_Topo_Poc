# Workspace Setup (WSL + Python)

## 1. 路径硬约束
- 本项目位于 Windows `E:` 盘
- WSL 下对应路径通常为 `/mnt/<drive>/...`
- 推荐项目根目录变量：`${REPO_ROOT}`

## 2. 路径相关注意事项
- 代码与配置尽量使用相对路径
- 文本回传优先使用逻辑名、相对路径和摘要，减少噪声

## 3. Python 环境
- 推荐使用 WSL 的 Python
- 首次进入仓库时，建议先执行：`python -m pip install -e .[dev]`
- 若未安装为 editable package，运行 CLI 时使用：`PYTHONPATH=src python -m normal_topo_poc <cmd>`
- 所有运行与测试命令默认在 repo root 执行
