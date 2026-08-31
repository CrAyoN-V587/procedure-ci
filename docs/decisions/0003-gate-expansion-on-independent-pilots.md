# 0003：用独立维护者和对照回放约束功能扩展

- 状态：Accepted
- 日期：2026-08-31

## 背景

严格 MVP 已证明单 OpenAPI、Arazzo 1.1 operationId 子集的 step-impact 可以确定性实现。第三次调研
同时发现：

- API Evangelist 的 4,956 个 workflow corpus 曾因 OpenAPI refine/split 出现 5,153 个悬空
  sourceDescriptions，但原有 validator 在 transform 后重新运行即可发现；
- Pachca 的 Arazzo 1.0.1 是结构化 workflow 源的生成出口；
- Paygentic/Speakeasy 的 Arazzo 1.0.1 contract tests 可用 `x-speakeasy-test-rebuild` 自动同步；
- Redocly、libopenapi、Jentic、Speakeasy、oasdiff 已覆盖验证、执行、生成、自动同步和通用 API diff；
- 尚未找到两个互相独立、人工或混合维护多步 Arazzo 且明确需要 step-impact 的团队。

因此，大量文件不能直接当作大量独立用户；真实漂移也不自动证明需要新的 validator 或 Action。

## 决策

1. 保留 0.1.0 实现，不在当前证据下增加 Arazzo 1.0、多 source、oasdiff adapter、GitHub Action
   或自动修复。
2. 将候选资产分为 A（人工/混合维护）、B（结构化源生成）、C（自动重建 contract tests）和
   D（策展/研究 corpus）。只有 A 类样本可以触发产品能力扩展。
3. 下一阶段只做 M5：至少 10 个历史变化的独立 gold set，以及 validator/generator/oasdiff 对照。
4. 只有至少 2 个独立 A 类维护者、至少 3 个增量 step-level 发现、recall ≥ 90%、关键误报率
   ≤ 20%，并有两次真实审阅收益时，才进入下一功能设计。
5. M5 工作量上限为 20–30 小时；失败时以研究工具/作品集形态收尾。

## 影响

- 当前代码和三输入 CLI 不变；设计文档必须明确区分已实现能力与候选能力。
- 1.0.1 和 API Evangelist 多源 corpus 可用于了解覆盖缺口，但不能为了跑通语料先扩实现。
- sourceDescription link health 先与现有 resolver/validator 对照；Procedure CI 只计算新增的 step-level
  决策价值。
- 通用 OpenAPI 变化分类不继续自行扩张；是否接入 oasdiff 由真实回放结果决定。
- GitHub Action 不再是自然的下一里程碑，必须先证明现有 JSON/Markdown 报告会被用于 PR 决策。
