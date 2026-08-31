# 0004：M5b fast-fail 后停止产品化

- 状态：Accepted
- 日期：2026-08-31

## 背景

严格 MVP 已实现，但继续投入必须先通过决策 0003 的 G1：至少 2 个独立 A 类维护者、可独立
标注的真实历史样本，以及相对 validator、generator 和 oasdiff 的 step-level 决策增量。

M5a 保留了 12 个历史对，但全部是 B/C 类 Arazzo 1.0.1 生成资产。M5b 冻结代表性 gold 后，
当前 CLI 的原始样本可运行覆盖为 0/12，complete gold 为 0，A 类维护者为 0。

## 决策

停止 Procedure CI 的产品化投入，保留功能代码 0.1.0 为研究/作品集工具。不得基于本轮语料
实现 Arazzo 1.0、OpenAPI 3.0、source-name 兼容、oasdiff adapter、GitHub Action 或新的服务层。

项目进入维护状态。只有用户或维护者主动提供符合 A 类资格且能在既定输入边界内回放的样本，
并重新满足 G1，才新建决策讨论功能投资；不能把 B/C/D 文件数量或合成版本探针当作替代证据。

## 依据

- oasdiff 能发现 PAY-05 的 operation 删除，但不提供 workflow/step 映射；
- Redocly 默认 lint 认为 head Arazzo 结构有效；
- 带 Speakeasy 自动重建标记的历史 head Arazzo 仍引用已删除 operation；本轮 Registry run
  为 `blocked_external_auth`，未验证实际重建结果；
- 该技术缝隙存在，但 Procedure CI 没有在原始样本上完成分析，无法计算 precision/recall；
- 为了开始验证而先扩兼容范围，会倒置已约定的需求门槛。

详细证据见 [M5b 对照基线](../M5-BASELINES.md) 和 [gold 冻结记录](../M5-GOLD.md)。

## 结果

正向结果：0.1.0 的清晰边界、40 项回归、语料分类、污染披露和停止决策成为完整工程作品集。

负向结果：不声称市场验证通过，不发布新的 feature 路线，不发送 M5c 外部维护者消息。

可逆条件：新的 A 类证据可以触发一次新的 G1 评审，但不会自动恢复本项目的功能路线。
