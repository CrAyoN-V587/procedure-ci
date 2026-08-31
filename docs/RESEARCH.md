# Procedure CI 第三次专项调研

调研快照：2026-08-31
前次基线：2026-08-29
时区：Asia/Shanghai
证据口径：官方规范、官方产品文档、公开仓库/Issue、GitHub API 只读快照；推断与事实分开记录

## 结论

Procedure CI 的技术切口仍然存在：截至本次快照，没有发现成熟工具直接把 OpenAPI 实体变化映射为
Arazzo `workflowId + stepId + dependency path`。但这还不足以支持继续扩展产品。

新的投入结论是：

> 保留已完成的严格 MVP，只投入一个有上限的 M5 证据阶段；在证明它相对 Arazzo validator、
> 生成器自动同步和 oasdiff 有增量审阅价值前，不做 GitHub Action、Arazzo 1.0 兼容、多源解析或
> 新的 diff 能力。

原因有三点：

1. Arazzo 生态确实在增长，1.1.0 已发布，解析、验证、执行和生成工具均在活跃开发；
2. 公开资产比按文件名搜索得到的结果多得多，但大量来自单一策展 corpus 或生成器，不能当作独立
   生产团队采用；
3. 已发现真实的大规模 sourceDescription 漂移事故，但现有 validator 重新运行即可发现，说明该
   事故首先是流水线编排问题，不自动证明需要一个新的分析器。

当前项目最合理的定位是 **Arazzo step-impact research tool / portfolio project**。是否升级为产品，
只由独立维护者的历史变更回放和对照实验决定。

## 2026-08-31 相比前次调研的新信息

### 1. Arazzo 1.1 已稳定发布，但语义仍在快速收敛

[Arazzo 1.1.0](https://spec.openapis.org/arazzo/v1.1.0.html) 于 2026-05-17 发布；新增或强化了
`$self`/基址解析、AsyncAPI、step `dependsOn`、JSONPath/XPath selector 等能力。官方同时明确：
同步 workflow 的顺序通常由 steps 数组表达，而 `dependsOn` 主要用于异步协调。

规范仍有会导致不同实现分歧的公开问题：

- [#518](https://github.com/OAI/Arazzo-Specification/issues/518)：simple condition 缺少规范化语法与
  runtime-expression 边界规则；
- [#501](https://github.com/OAI/Arazzo-Specification/issues/501)：共享 ABNF 对 HTTP/message source
  组合约束不足；
- [#557](https://github.com/OAI/Arazzo-Specification/issues/557)：跨 workflow 的 step `dependsOn`
  写法与 runtime-expression ABNF 不一致。

因此，严格 MVP 把超出已验证子集的语义报告为 `unknown` 仍是正确选择。此时扩展条件求值、
selector 或 AsyncAPI，会把规范歧义转化为本项目维护成本，不应优先。

### 2. 相邻工具覆盖面继续扩大

| 工具 | 2026-08-31 可确认能力 | 对 Procedure CI 的约束 |
| --- | --- | --- |
| [OAI Arazzo tooling](https://github.com/OAI/Arazzo-Specification#tooling) | 官方清单已覆盖编辑、生成、验证、解析/解析引用、执行、转换和 mock | 不做通用 Arazzo 工具箱 |
| [Redocly CLI](https://redocly.com/docs/cli/changelog) | 2.35.0 已支持 Arazzo 1.1 syntax；lint 可输出 GitHub Actions 注释；Respect 可执行 workflow | 不做 validator、runner 或仅为注释包装一层 Action |
| [libopenapi Arazzo](https://pb33f.io/libopenapi/arazzo/) | 解析、源码位置、21 条结构/语义验证规则，并可把 OpenAPI source 附着后验证 operation 引用 | 不把完整规范验证作为差异点 |
| [Jentic Arazzo Tools](https://github.com/jentic/jentic-arazzo-tools) / [Arazzo Toolkit](https://github.com/usearazzo/arazzo-toolkit) | parser、resolver、validator、runner、UI；当前公开 README 仍以 1.0.x 为主 | 生态版本支持并不整齐；不能假设 1.1 已普及 |
| [Speakeasy SDK tests](https://www.speakeasy.com/docs/customize-testing/customizing-sdk-tests) | Arazzo 驱动 SDK contract tests；`x-speakeasy-test-rebuild: true` 会随 OpenAPI 自动重建参数、body、response 和 examples | 自动同步资产不是首批用户，只能作为负向对照 |
| [oasdiff](https://github.com/oasdiff/oasdiff) | 最新 v1.30.0（2026-08-30）新增 58 条检查、可审计覆盖模型、boolean schema/prefixItems 和 OpenAPI 3.2 method 支持；此前已具备精确 source location、稳定 fingerprint、机器输出 Schema 和 Action | 不再扩展通用 OpenAPI diff；先比较复用其输出是否更可靠 |
| [PactFlow Drift](https://github.com/pactflow/roadmap/issues/138) | 路线图有 Q4 `Drift - Arazzo`；现有 Drift 明确聚焦运行中实现是否符合 OpenAPI，而非业务 E2E | 属于相邻竞争信号，但目前不等价于静态 step impact |

2026-08-31 GitHub API 快照：OAI/Arazzo-Specification 465 Star、oasdiff 1,336、
pb33f/libopenapi 868、speakeasy-api/openapi 277、jentic/arazzo-engine 64、
strefethen/arazzo-cli 7。Star 只表示公开可见性，不能证明独立用户数量或付费需求。

### 3. 公开 Arazzo 资产存在，但来源结构不均匀

GitHub code search 的查询口径会造成数量级差异：

- `arazzo extension:yaml`：38 个结果，其中不少只是依赖配置或测试 fixture；
- `sourceDescriptions workflowId extension:yaml`：8 个结果；
- `sourceDescriptions workflowId language:YAML`：4,216 个结果，主要由 `api-evangelist/*`
  仓库中的 `.yml` workflow 构成。

这不是采用率统计。GitHub code search 只覆盖可索引的公开默认分支，会漏掉私有仓库、JSON、非典型
写法和未索引内容；同时，一个组织可贡献数千个文件。它只能用于寻找语料，不能当市场规模。

## 四类公开样本及其含义

### A. API Evangelist：大规模策展 corpus，有真实漂移事故

[roadmap #205](https://github.com/api-evangelist/roadmap/issues/205) 记录了一次明确事故：4,956 个
workflow 文件含 5,574 个本地 sourceDescriptions，其中 5,153 个（92%）在 OpenAPI refine/split
后指向不存在文件，影响 545 个 provider。原验证门禁在 authoring 时曾通过，但 transform 后没有
重新验证；修复通过 operationId 索引把步骤重新映射到 split 后的 OpenAPI。

这是目前最强的公开漂移证据，也暴露两个边界：

- 需求真实：OpenAPI 文件拆分/移动会破坏 Arazzo source topology 和 operation binding；
- 独特性未证：重新运行现有 resolver/validator 已能发现悬空引用，缺失的是 pipeline wiring；
  Procedure CI 只有在进一步解释“哪些 step 因哪些实体变化需要审阅”时才有增量价值。

该 corpus 是 API Evangelist 的独立第三方 profile，多个仓库由同一策展流程维护，并有 AI 辅助生成
记录。因此它适合作为高覆盖压力语料，不代表 545 个独立生产用户。

### B. Pachca：持续维护的多表面 recipe，但 Arazzo 是生成出口

[Pachca workflows](https://github.com/pachca/openapi/blob/main/apps/docs/public/workflows.arazzo.yaml)
使用 Arazzo 1.0.1。GitHub API 显示 2026-05-17 至 2026-08-28 有 10 个提交触及该文件；代表性
API audit 提交同时修改 OpenAPI、workflows、CLI、SDK、Agent Skills 和文档。

但其源资产是 `packages/spec/workflows.ts`，发布的 Arazzo 只是多个生成出口之一。它证明同一 API
变化需要传播到多个消费表面，却不证明团队需要单独维护 Arazzo 或会购买 step-impact 工具。
适合作为“混合/生成资产”对照，不应直接计为手写 workflow 用户。

### C. Paygentic/Speakeasy：高频 Arazzo 变化，但已有自动同步

[Paygentic Python SDK tests](https://github.com/paygentic/sdk-python/blob/main/.speakeasy/tests.arazzo.yaml)
使用 Arazzo 1.0.1。2026-03-06 至 2026-08-27 有 29 个提交触及该文件，代表性 SDK regenerate
提交也修改 `.speakeasy/out.openapi.yaml`。

这些 workflow 带 `x-speakeasy-test-rebuild: true`；Speakeasy 官方说明该标志会在 OpenAPI 变化后
自动重建测试。它是很好的变化语料和负向对照，但不是 Procedure CI 的目标：如果上游生成器已能
可靠同步，额外 impact report 的收益可能接近零。

### D. Bank API：接近手写的 1.1 多步样本，但没有历史序列

[Bank API Arazzo](https://github.com/erwinkramer/bank-api/blob/main/.arazzo/v1.arazzo.yaml) 使用
1.1.0，含三个步骤、跨步骤输出和 optimistic concurrency；截至快照只有一次文件提交。文件注释
还说明 Spectral 当时不能正确验证 1.1，且样本使用非标准 `$response.headers.etag`。

它适合验证语法覆盖和 `unknown` 行为，但没有足够历史变化，不能单独证明 step-impact 的审阅价值。

## 用户分层与目标选择

| 群体 | 资产来源 | Procedure CI 可能价值 | 本轮判断 |
| --- | --- | --- | --- |
| A：人工或混合维护的多步 workflow | 人负责依赖、参数和跨步骤数据流 | 变化定位到 step，减少人工追踪 | 唯一候选首批用户；必须找到至少 2 个独立维护者 |
| B：由同仓库结构化源生成的 Arazzo | TypeScript/数据库/模板生成多个出口 | 作为 generator QA，发现传播遗漏 | 次要用户；先与生成器自带校验对照 |
| C：随 OpenAPI 自动重建的 contract tests | Speakeasy 等生成器 | 生成器已拥有同步上下文 | 不作为产品需求证据，只做负向对照 |
| D：策展/研究 corpus | 批量生成或修复公开 API workflow | 压力测试和规则发现 | 只作为语料，不按文件数计算用户 |

首批目标从“任何维护 Arazzo 的团队”收紧为：

- 至少两条跨 operation 的 workflow；
- Arazzo 不是每次都由同一生成器完全重建；
- OpenAPI 与 workflow 在 PR 中共同演进；
- 团队当前需要人工判断 schema/auth/response 变化是否影响具体步骤。

## 产品边界复核

### 仍然成立

- 核心问题只做 `OpenAPI change → Arazzo step impact`；
- 输出必须包含 workflow、step、实体和依赖路径；
- `error / review / unknown / info` 分离；
- 离线、只读、确定性；LLM 不进入 CI 判定；
- 不自造 workflow DSL，不执行生产 API。

### 明确不做

- 不复制 Redocly/libopenapi/Jentic 的完整 Arazzo validation；
- 不复制 Speakeasy 的 workflow 生成和自动重建；
- 不复制 oasdiff 的 breaking-change 分类；
- 不因为 API Evangelist 的大量文件就立即实现多仓库、网络 resolver 或自动修复；
- 不为跑通生成式 1.0.1 corpus 而直接扩版本范围。

### 需要通过证据门槛才能进入设计的候选

- Arazzo 1.0.x 的共享同步 operationId 子集；
- 多个本地 OpenAPI sourceDescriptions；
- OpenAPI split/move 后的 operation relocation；
- oasdiff JSON change provider；
- GitHub Action/SARIF。

每一项都必须由至少一个 A 类样本触发；C/D 类语料只能帮助测试，不能单独触发产品扩展。

## M5 验证设计

### M5a：语料筛选（5–7 小时）

1. 从 API Evangelist、Pachca、Paygentic 和其他独立仓库列出 12–20 个候选历史变更；
2. 标记资产属于 A/B/C/D 哪一类，并记录 Arazzo 版本、source 数、step 数、生成/维护方式；
3. 只保留至少 10 个可还原的 base/head OpenAPI 对；
4. 先用现有 validator/generator/oasdiff 建立基线，不把它们能完整回答的问题算作本项目价值。

### M5b：人工标注与回放（10–14 小时）

对每个样本先人工写 gold set：

- 哪些 workflow/step 真正受影响；
- 影响路径是 operation、parameter、request、response、security 还是 source relocation；
- 维护者是否需要修改 Arazzo；
- 现有工具已经给出什么信号。

然后才运行 Procedure CI，记录 precision、recall、`unknown` 比例、重复/新增诊断，以及报告是否改变
审阅决定。不得先看工具输出再反向构造标签。

### M5c：维护者验证

联系至少 3 个仓库维护者，目标是获得 2 个互相独立的 A 类样本。只询问实际工作流维护和变更审阅
过程，不用“是否喜欢这个 idea”代替行为证据。实际工作量上限 3–5 小时，回复等待不计入工时。

## 继续与停止条件

只有以下条件同时满足，才继续工程投入：

1. 至少 2 个独立维护者拥有 A 类 workflow；
2. 至少 10 个历史变更可人工标注，且来自至少 2 个独立维护源；
3. Procedure CI 在至少 3 个样本中提供 validator/generator/oasdiff 没有的 step-level 决策信息；
4. 关键影响 recall 不低于 90%，关键误报率不高于 20%，`unknown` 不吞没主要工作流；
5. 报告至少两次改变或显著缩短真实审阅决定。

任一情况成立时停止产品化：

- 找不到 2 个独立 A 类维护者；
- 有规模的公开资产主要由生成器完整同步；
- 现有 validator + generator + oasdiff 已覆盖维护者需要的决策；
- 为支持真实样本必须先实现完整 resolver/runner/condition evaluator；
- 只能在同一策展 corpus 内证明效果。

下一阶段最大投入上限为 20–30 小时研究与回放，不含新功能开发。门槛失败时保留现有 CLI，项目以
`arazzo-impact-lab`/作品集形态收尾；门槛通过后再单独估算 1.0 兼容、多源或 oasdiff adapter。

## 主要来源

- [Arazzo 1.1.0 Specification](https://spec.openapis.org/arazzo/v1.1.0.html)
- [Arazzo 1.0.1 Specification](https://spec.openapis.org/arazzo/v1.0.1.html)
- [OAI Arazzo tooling](https://github.com/OAI/Arazzo-Specification#tooling)
- [Arazzo 1.1.0 release](https://github.com/OAI/Arazzo-Specification/releases/tag/1.1.0)
- [oasdiff](https://github.com/oasdiff/oasdiff) 与 [v1.30.0 release](https://github.com/oasdiff/oasdiff/releases/tag/v1.30.0)
- [libopenapi Arazzo](https://pb33f.io/libopenapi/arazzo/)
- [Redocly Arazzo lint](https://redocly.com/docs/cli/v1/guides/lint-arazzo)
- [Redocly Respect](https://redocly.com/docs/respect/v1/commands/respect)
- [Jentic Arazzo Tools](https://github.com/jentic/jentic-arazzo-tools)
- [Arazzo Toolkit](https://github.com/usearazzo/arazzo-toolkit)
- [Speakeasy custom SDK tests](https://www.speakeasy.com/docs/customize-testing/customizing-sdk-tests)
- [PactFlow roadmap: Drift - Arazzo](https://github.com/pactflow/roadmap/issues/138)
- [PactFlow: Where Drift Fits](https://pactflow.github.io/drift-docs/docs/concepts/where-drift-fits/)
- [API Evangelist roadmap #205](https://github.com/api-evangelist/roadmap/issues/205)
- [API Evangelist OpenAI Arazzo sample](https://github.com/api-evangelist/openai/blob/main/arazzo/openai-thread-and-run-workflow.yml)
- [Pachca workflows](https://github.com/pachca/openapi/blob/main/apps/docs/public/workflows.arazzo.yaml)
- [Paygentic Speakeasy tests](https://github.com/paygentic/sdk-python/blob/main/.speakeasy/tests.arazzo.yaml)
- [Bank API Arazzo](https://github.com/erwinkramer/bank-api/blob/main/.arazzo/v1.arazzo.yaml)
