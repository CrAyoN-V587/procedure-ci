# Webhook onboarding 夹具

`base/openapi.yaml`、`head/openapi.yaml` 和 `workflow.yaml` 是严格 MVP 的最小完整输入：

- OpenAPI 3.1，四个互相依赖的 webhook 操作和一个无关的 `healthCheck` 操作；
- Arazzo 1.1，包含创建、发送测试事件、查询投递和删除四个步骤；workflow 使用官方
  `$sourceDescriptions.webhooks.<operationId>` operation expression；
- `EventType` 是通过二级 `$ref` 传递到创建步骤的嵌套 Schema。
- 后续步骤通过 `$steps.createSubscription.outputs.subscriptionId` 消费 producer 输出，夹具可
  验证 response/schema 变化沿可解释依赖路径传播。
- 夹具和回归还覆盖显式 `dependsOn` 的消费者传播、官方 `$response.header.*`/`$response.body`
  表达式，以及非标准 runtime、可复用 `$ref` 和非 JSON request body 的保守 unknown 边界。

`tests/test_procedure_ci.py` 在临时目录中从这些基线构造变体，覆盖：

| 变体 | 预期 |
| --- | --- |
| 无关 `healthCheck` 文档变化 | 无 workflow 影响 |
| `WebhookSubscription` 增加必填字段 | 创建步骤 `review`，字面量 payload `error` |
| 收窄 `EventType` 枚举 | 创建步骤 `review` |
| 改变 `sendTestEvent` 认证方案 | 发送步骤 `review` |
| 删除被引用的 `sendTestEvent` | `OAS_OPERATION_MISSING`，退出码 1 |
| 保留 `operationId` 但移动 path | 发送步骤 `review` |
| 外部 `$ref`、动态 payload | `unknown`，不抓取、不执行 |
| 缺失输出、依赖环、重复 operationId | 确定性 `error` |

变体在测试中动态生成，避免把相同的大型 OpenAPI 文档复制多份；这组输入同时是
后续历史回放和用户试点的第一份脱敏样本。

`negative/missing-operation.yaml` 是可直接从命令行运行的失败样本，用于验证退出码 1。
