# Procedure CI 二次调研

调研日期：2026-08-29
整理日期：2026-08-30
时区：Asia/Shanghai
结论口径：一手仓库、官方规范、公开 Issue 和当前主机只读验证

## 结论

最初的“把任意文档转换成有来源、可测试的 Procedure，并在 CI 中防止过期”不适合直接投入。它同时撞上了文档执行、文档测试、代码—文档漂移、OpenAPI diff、Skill 生成和 Skill 同步等多个已有赛道。

二次调研后，项目应收窄为：

> 对 base/head OpenAPI 和 Arazzo 建立语义依赖图，将 API entity 变化映射为受影响的 workflow/step，并输出 PR 可审阅报告。

采用 Arazzo 而不是自定义 YAML IR 是硬边界。OpenAPI Initiative 对 Arazzo 的定义本身就是“表达多次 API 调用及其依赖，以完成特定结果”；官方列出的用例已经包括 Agent 安全执行、MCP/SDK/代码生成、文档和测试。[Arazzo 官方定位](https://www.openapis.org/arazzo-specification) · [Arazzo 1.1.0 规范](https://spec.openapis.org/arazzo/latest.html)

投入判断：**值得做 M0 和严格 MVP；不值得在没有试点前建设完整产品。**

## 为什么通用 Procedure CI 不成立

| 项目/标准 | 已覆盖能力 | 对本项目的约束 |
| --- | --- | --- |
| [book-to-skill](https://github.com/virgiliojr94/book-to-skill) | 把多种书籍/文档转换为 Agent Skill，并支持把新材料折叠进现有 Skill | “文档转 Skill”不是差异点；一次性生成不能作为主产品 |
| [Runme](https://github.com/runmedev/runme) | 直接执行 Markdown 中的 shell/代码单元，把 runbook 变成可运行 notebook | 不再建设 Markdown 执行器或通用 runbook runner |
| [Doc Detective](https://github.com/doc-detective/doc-detective) | 从文档/测试规格执行浏览器、HTTP、shell 等步骤；Agent 工具还能从文档生成测试 | 不再把“文档步骤转测试”作为核心；其公开 [CI 退出码问题 #674](https://github.com/doc-detective/doc-detective/issues/674) 只是实现缺口，不足以支持另起通用项目 |
| [Fiberplane Drift](https://github.com/fiberplane/drift) | 把 Markdown 绑定到文件/AST symbol，变动时在 CI 标记 stale | 文件和 symbol 级文档漂移已有产品；其 [structured-data node #36](https://github.com/fiberplane/drift/issues/36) 尚未覆盖 OpenAPI key/value 级绑定，说明细粒度结构化依赖仍有切口，但可能被快速补齐 |
| [oasdiff](https://github.com/oasdiff/oasdiff) | OpenAPI diff、breaking checks、源码定位、JSON/Markdown/JUnit/GitHub Actions 输出 | 不重写通用 OpenAPI diff；本项目只补“哪个 Arazzo step 依赖该变化” |
| [agent-runbook](https://github.com/KnoxOps/agent-runbook) | 把有契约的 YAML runbook 编译为 Agent Skill，支持 loop/checkpoint | 不定义新的 runbook DSL，不把 Skill 编译作为核心 |
| [GitHub `gh skill`](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills) | 安装、更新、发布和验证 Skill，并记录 repo/ref/tree SHA provenance | Skill 来源和版本跟踪已有官方路径；本项目不做 Skill 包管理 |
| [Arazzo 官方工具清单](https://github.com/OAI/Arazzo-Specification#tooling) | 编辑器、生成器、validator、parser/resolver、runner、mock、Markdown 转换 | 不做完整 Arazzo 工具箱，只做影响分析 |
| [arazzo-cli](https://github.com/strefethen/arazzo-cli) | Arazzo 执行、DAG、dry-run、trace/replay、CI contract test、MCP | 录制回放能发现实际 request drift，但不是 PR 中的静态 step impact 清单；本项目不执行 API |

2026-08-29 的只读 GitHub API 快照也说明两类市场成熟度不同：`book-to-skill` 约 26.9k Star，而 Arazzo 官方规范仓库约 465 Star，文档/工作流工具多在百至两千量级。Star 只能说明可见性，但足以提醒：Skill 热度不能直接外推为 Arazzo 产品采用。

## 真正的缺口

现有工具通常回答以下问题之一：

- API 发生了哪些 breaking/non-breaking changes？
- 文档绑定的文件或 symbol 是否变化？
- Arazzo 文档是否合法、能否执行？
- 录制的工作流在新版本下是否构造相同 request？
- Skill 是否来自新的上游版本？

Procedure CI 只尝试回答一个更窄的问题：

```text
OpenAPI entity changed
        ↓
哪些 Arazzo step 直接或传递依赖它？
        ↓
依赖为何受影响，当前引用是否已经确定性失效？
```

这里的“传递”很重要。例如一个 step 调用 `createWebhookSubscription`，request body 引用 `CreateWebhookRequest`，后者再引用 `WebhookFilter`。即使 operationId 没变，二级 schema 的 required/enum 改变也可能需要重新审阅该 step。

## 目标用户和触发场景

### 目标用户

- 将 OpenAPI 保存在 Git 中的 API 平台或 Developer Experience 团队；
- 已维护至少 2–3 个多步 API 集成流程；
- 正在向 Agent、MCP、SDK 或开发者门户暴露这些流程；
- PR 审阅时需要知道 API 改动对业务流程的影响。

普通 API 消费者、没有多步 workflow 的小型 API、只关心 breaking change 的团队不是首批用户。

### 首个场景：Webhook 接入流程

首个 fixture 固定为四步：

1. `createWebhookSubscription`；
2. `sendTestEvent`；
3. `getWebhookDelivery`；
4. 可选 `deleteWebhookSubscription`。

这个场景能同时覆盖：跨步骤 ID 传递、认证、request schema、轮询 response、成功条件和清理步骤。拟定的 6 个 mutation：

| 变化 | 预期 |
| --- | --- |
| 修改无关 `listUsers` operation | workflow 不受影响 |
| `CreateWebhookRequest` 新增 required 字段 | create step 为 `review`，若已有 example 不合法则为 `error` |
| 二级 `$ref` `WebhookFilter` enum 收窄 | create step 通过传递依赖受影响 |
| security scheme 或 requirement 改变 | 使用该 operation 的 step 受影响 |
| 删除 `sendTestEvent` operation | 对应 step 为确定性 `error` |
| operationId 保持不变但 path/method 改变 | 对应 step 为 `review`；不误报其他 step |

## 真实场景证据

[World Monitor](https://github.com/koala73/worldmonitor) 同时发布 REST API、OpenAPI 和 25 个 Agent Skills。其 [Agent Skills index](https://worldmonitor.app/.well-known/agent-skills/index.json) 明确说明 Skill 用于给 Agent 提供比“遍历完整 OpenAPI”更聚焦的 recipe。

抽查 [check-country-risk Skill](https://worldmonitor.app/.well-known/agent-skills/check-country-risk/SKILL.md) 与 [OpenAPI 3.1.0](https://worldmonitor.app/openapi.yaml) 可见，同一能力在 Skill 中重复记录：

- operation `GetCountryRisk` 和 endpoint；
- `X-WorldMonitor-Key` 认证；
- query parameter；
- response 字段和错误码。

这证明“API source 与 Agent-facing procedure 之间存在多个可能漂移的重复表面”。但 World Monitor 当前公开入口不能证明其用 Arazzo，也不能证明团队愿意采用 Procedure CI。因此它是问题场景证据，不是产品采用证据。

Arazzo 官方规范于 2026-05-17 发布 1.1.0，明确增加 AsyncAPI、step `dependsOn`、selector、workflow chaining 和 Agent 场景；工具列表已经包含编辑、生成、验证、解析、执行和转换。[1.1.0 变化](https://www.openapis.org/arazzo-specification) 这说明标准在发展，也说明采用处于早期且竞争面会快速变化。

## 产品假设和证据级别

| 假设 | 当前证据 | 级别 |
| --- | --- | --- |
| Agent 需要比完整 OpenAPI 更聚焦的多步 recipe | Arazzo 官方定位、World Monitor Skills | 标准/项目证据 |
| OpenAPI 和 Agent procedure 会漂移 | 同一 operation/auth/schema 在两个表面重复 | 合理推断，未量化 |
| step-level impact 比 oasdiff 更省审阅时间 | 暂无用户或历史 PR 对照 | 未验证 |
| 用户愿意维护 Arazzo | Arazzo 工具和公开样例存在，普及率未知 | 弱证据 |
| 可以在 4–6 周做出可靠子集 | 标准对象边界清楚，仍有 resolver 风险 | 待 M0 验证 |

## 竞争优势必须满足的条件

独立价值只在以下条件同时成立时存在：

1. 输出到 `workflowId + stepId`，而不是仅报告 spec 文件变化；
2. 能追踪 operation 到 parameter/request/response/security 和二级 `$ref` schema；
3. 区分“确定性失效”“需要审阅”“不支持/未知”，不把所有依赖变化都阻断；
4. 报告能解释依赖路径，而不是只给黑盒相似度或 LLM 判断；
5. 不要求执行生产 API；
6. 对无关 operation 变化保持低误报。

如果最终只是 `oasdiff + grep operationId`，项目不应独立立项。

## 市场验证计划

在实现完整 CLI 前，找 5 个具备 OpenAPI 的 API 团队或公开仓库，询问：

1. 是否维护多步 API workflow、Postman collection、教程或 Agent Skill？
2. API 改动后怎样判断这些流程是否需要更新？
3. 是否有因 schema/auth/response 变化导致教程、SDK 示例或 Agent recipe 过期的案例？
4. 是否愿意把关键 workflow 写成 Arazzo，还是更愿意继续维护测试脚本？
5. PR 中哪种报告会改变审阅决定？

继续条件：至少 2 个团队拥有可维护的多步 workflow，并愿意提供 10 个左右历史变更用于回放。

停止/降级条件：

- 5 个团队中不足 2 个有此流程；
- 用户只需要 breaking-change 检测，直接推荐 oasdiff；
- 现有 Arazzo 工具增加等价 step impact；
- 10–20 个真实变更中误报超过 20%；
- 用户不愿显式维护 workflow dependency。

## 投入建议

- M0：值得，3–5 天；
- 严格 MVP：在 M0 通过后投入 60–90 小时；
- GitHub Action、源码定位、Skill renderer、外部试点：总计 90–135 小时；
- 没有外部试点：以 `arazzo-impact-lab` 学习项目收尾，不宣称需求已验证；
- 不建议现在安装大量依赖、搭建服务端或设计商业化功能。

## 主要来源

- [Arazzo 1.1.0 Specification](https://spec.openapis.org/arazzo/latest.html)
- [OpenAPI Initiative: Arazzo Specification](https://www.openapis.org/arazzo-specification)
- [OAI/Arazzo-Specification tooling](https://github.com/OAI/Arazzo-Specification#tooling)
- [oasdiff](https://github.com/oasdiff/oasdiff)
- [Fiberplane Drift](https://github.com/fiberplane/drift)
- [Runme](https://github.com/runmedev/runme)
- [Doc Detective](https://github.com/doc-detective/doc-detective)
- [book-to-skill](https://github.com/virgiliojr94/book-to-skill)
- [arazzo-cli](https://github.com/strefethen/arazzo-cli)
- [World Monitor programmatic access](https://github.com/koala73/worldmonitor#programmatic-access)
- [World Monitor Agent Skills index](https://worldmonitor.app/.well-known/agent-skills/index.json)
