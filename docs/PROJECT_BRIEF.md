# Normal_Topo_Poc - Project Brief (Global)

## 1. 项目目标
在普通道路场景下，对「路网拓扑自动生产」四个关键技术模块做 POC 论证，并建立可拆分推进、可诊断、可回传质量验收文本的仓库基线。

## 2. POC 范围（t01-t04）
- t01：路口核实
- t02：路段提取
- t03：路段构建
- t04：路口建模

## 3. 当前线程职责
- 搭建项目级目录与文档
- 固化与 `Highway_Topo_Poc` 一致的文档分层、代码归属和文本回传约定
- 为四个模块建立独立文档三件套与源码目录占位
- 提供最小 CLI、文本质检协议和基础测试

## 4. 关键约束
- 模块文档放 `modules/<module_id>/`
- 模块代码放 `src/normal_topo_poc/modules/<module_id>/`
- 运行产物放 `outputs/_work/<module_id>/<run_id>/`
- 真实字段、阈值、算法细节、Provider 适配路径在子线程冻结

## 5. 成功标准（MVP）
- 仓库骨架完整
- 公共协议可直接复用
- 后续每个模块都能独立推进，不需要重做项目级结构

## 6. 模块目录（概览）
```text
modules/
  t01_intersection_verification/
  t02_segment_extraction/
  t03_segment_construction/
  t04_intersection_modeling/
```
