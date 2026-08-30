# Procedure CI 详细设计

- 版本：0.1
- 状态：严格 MVP 已实现；等待历史回放和用户试点
- 调研基线：2026-08-29
- 整理日期：2026-08-30

## 1. 设计结论

Procedure CI 的首个可验证形态不是通用“文档转 CI”，而是 **Arazzo Impact CI**：读取 Pull Request 前后的 OpenAPI 文档和 Arazzo 工作流，计算 API 实体变化会影响哪些工作流步骤，并生成可定位、可解释、可供 CI 判定的报告。

首版坚持三条原则：

1. 使用 Arazzo 1.1.x，不定义自有 Procedure YAML 或中间规范。
2. 静态分析优先；不发送真实请求，不执行任意代码，不让 LLM 决定 CI 成败。
3. 无法确定时明确报告 `unknown`，不伪装成“未受影响”。

## 2. 目标用户与使用路径

目标用户是同时维护以下资产的 API、DevEx 或 SDK 团队：

- OpenAPI 3.1 接口定义；
- 2–3 条以上跨接口工作流；
- 在 Pull Request 中审查接口变化；
- 需要知道“哪些业务流程会被这次接口改动影响”。

预期命令（严格 MVP 的三个输入）：

```powershell
procedure-ci check `
  --base-openapi .\fixtures\base\openapi.yaml `
  --head-openapi .\fixtures\head\openapi.yaml `
  --arazzo .\fixtures\workflow.yaml `
  --format markdown
```

本地命令与 CI 使用同一分析核心。GitHub Action 只是后续薄封装，不在严格 MVP 内实现。

## 3. 严格 MVP 边界

| 维度 | MVP 支持 | 暂缓 |
| --- | --- | --- |
| API 定义 | OpenAPI 3.1 | 3.0、3.2 的兼容矩阵 |
| 工作流 | Arazzo 1.1.x 的同步 OpenAPI 子集；恰一个 `type: openapi` source description | AsyncAPI、复杂回调、跨多文档编排 |
| 输入 | 一份本地 base/head OpenAPI + 一份本地当前 Arazzo | URL、仓库自动发现、base/head Arazzo、远程引用 |
| 引用 | 文档内部 `$ref`，递归追踪并检测环 | 外部文件和网络引用 |
| 步骤定位 | 唯一 `operationId` | 模糊路径匹配和自动猜测 |
| 输出 | 版本化 JSON、Markdown | Dashboard、数据库、PR 评论机器人 |
| 执行 | 纯静态分析 | API 调用、Shell、模板、任意脚本 |
| 智能能力 | 确定性规则 | LLM 裁决、自动修复 |

## 4. 系统边界与架构

```text
base/head files
      |
      v
 loader + validator
      |
      +--> OpenAPI index ----+
      |                      |
      +--> Arazzo index -----+--> dependency graph
                                      |
base/head OpenAPI compare ------------+
                                      v
                                impact checks
                                      |
                           JSON / Markdown report
```

建议模块：

```text
src/procedure_ci/
  cli.py
  loader.py
  models.py
  oas_index.py
  arazzo_index.py
  graph.py
  compare.py
  checks.py
  report_json.py
  report_markdown.py
tests/
  fixtures/webhook_onboarding/
  test_graph.py
  test_compare.py
  test_checks.py
  test_cli.py
```

模块职责：

- `loader`：安全读取 YAML/JSON、识别版本、限制大小并保留来源位置；
- `oas_index`：建立操作、参数、请求体、响应、安全方案和 Schema 的稳定索引；
- `arazzo_index`：解析工作流、步骤、输入输出和运行时表达式；
- `graph`：建立步骤到 API 实体的依赖边；
- `compare`：产生 base/head 的实体级变化；
- `checks`：把变化传播到工作流步骤并生成诊断；
- `report_*`：只负责稳定序列化和呈现，不重新判断结果。

## 5. 核心数据模型

以下模型已用 Python `dataclass` 实现；MVP 不引入额外领域抽象层：

```text
EntityRef
  source_name: str
  kind: operation | parameter | request_body | response | schema | security
  canonical_id: str
  source_pointer: str

StepRef
  document: str
  workflow_id: str
  step_id: str
  source_pointer: str

DependencyEdge
  step: StepRef
  entity: EntityRef
  reason: operation | input | output | runtime_expression | transitive_ref
  via: list[EntityRef]

EntityChange
  entity: EntityRef
  status: added | removed | modified
  changed_paths: list[str]
  change_class: behavior | example | documentation

Impact
  step: StepRef
  changes: list[EntityChange]
  dependency_paths: list[list[EntityRef]]
  severity: error | review | unknown | info
  deterministic_error: bool

Diagnostic
  schema_version: str
  code: str
  severity: error | review | unknown | info
  source_file: str
  source_pointer: str
  message: str
  affected_steps: list[StepRef]
  details: object
```

所有面向外部的标识都必须稳定；禁止用 Python 对象地址、遍历顺序或临时数组下标作为 ID。

## 6. 依赖图规则

### 6.1 OpenAPI 图

从每个 `operationId` 建立到以下实体的边：

- 路径级和操作级参数；
- 请求体及其媒体类型 Schema；
- 响应、Header 及其媒体类型 Schema；
- 操作级或全局继承的安全要求；
- 上述实体通过内部 `$ref` 递归引用的所有组件。

解析器必须记录完整引用路径并检测循环。循环引用本身不是错误；只有无法解析或超出限制时才产生诊断。

### 6.2 Arazzo 图

每个工作流步骤至少追踪：

- `operationId` 指向的 OpenAPI 操作；
- 参数、请求体字段和认证输入；
- 后续步骤引用的输出；
- 运行时表达式引用的响应状态、Header 或 Body 路径；
- `dependsOn` 和输出依赖形成的步骤关系。

显式 `dependsOn` 和 `$steps.*.outputs.*` 都进入统一 step-to-step consumer 图；若 producer 的
operation 缺失或其 API entity 变化，影响沿 consumer 方向做任意深度闭包。若表达式超出 MVP
支持范围，步骤必须标记为 `unknown`，不能静默跳过。

producer 输出边界：当前只解析 `$steps.<stepId>.outputs.<name>`（及官方 bracket 形式）。支持
`$response.header.<name>`、`$response.body` 和 `$response.body#/...`；非标准
`$response.headers.*`、selector、非字符串 output、参数/reusable `$ref` 和非
`application/json` requestBody 报告 `UNSUPPORTED_ARAZZO_FEATURE: unknown`。consumer 的
影响路径沿完整 producer step 链、producer operation 及 API entity 依赖传播。base 和 head
分别建立图后取并集，因此删除或移动的旧实体仍能出现在可解释路径中。

## 7. OpenAPI 比较语义

比较器先规范化结构，再比较会影响行为的字段：操作定位、参数、请求体、响应、Schema、安全要求以及示例有效性。

规则约束：

- 对象字段顺序无意义；
- 数组是否有序由字段语义决定，不能统一排序；
- `required`、`enum`、`type`、`allOf`/`anyOf`/`oneOf` 和 security requirement 按集合语义
  归一化；response headers 与 header parameter 名称按不区分大小写比较；path/operation
  parameter 按 `(in, name)` 合并，operation 覆盖 path；
- JSON 标量类型必须保留，不能把 `1` 与 `"1"` 视为相同；
- `description`、`summary` 等纯文档变化默认不阻断，可记录为 `info`；
- 示例变化若破坏 Schema，升级为确定性错误；
- 只详细报告被工作流依赖的实体及其传递依赖。

## 8. 诊断与严重级别

| 代码 | 含义 | 默认级别 |
| --- | --- | --- |
| `OAS_OPERATION_MISSING` | Arazzo 引用的操作被删除或不存在 | `error` |
| `OAS_OPERATION_AMBIGUOUS` | `operationId` 不唯一，无法稳定绑定 | `error` |
| `OAS_REF_UNRESOLVED` | 内部 `$ref` 无法解析 | `error` |
| `ARAZZO_STEP_OUTPUT_MISSING` | 下游步骤引用了不存在的输出 | `error` |
| `ARAZZO_DEPENDENCY_CYCLE` | 步骤依赖构成无法处理的环 | `error` |
| `EXAMPLE_SCHEMA_INVALID` | Arazzo 示例不再符合 OpenAPI Schema | `error` |
| `SECURITY_SCHEME_MISSING` | 步骤所依赖的认证方案消失 | `error` |
| `ARAZZO_REF_UNRESOLVED` | Arazzo 内部 `$ref` 无法解析 | `error` |
| `UNSUPPORTED_EXTERNAL_REF` | 遇到 MVP 不支持的外部引用 | `unknown` |
| `UNSUPPORTED_ARAZZO_FEATURE` | Arazzo key 或 runtime expression 超出 MVP 子集 | `unknown` |
| `UNSUPPORTED_OAS_FEATURE` | `$dynamicRef`、`$anchor` 或可能改变基址的 `$id` 未解析 | `unknown` |
| `DEPENDENCY_CHANGED` | 依赖实体发生兼容性未定的变化 | `review` |
| `DEPENDENCY_DOC_ONLY` | 仅文档字段变化 | `info` |

级别语义：

- `error`：确定性规则证明工作流已失效；
- `review`：确定受影响，但兼容性需要人工判断；
- `unknown`：分析能力不足，不能证明安全；
- `info`：已知非阻断或仅用于定位。

首版退出码：

- `0`：分析完成且无确定性错误，可以仍包含 `review` 或 `unknown`；
- `1`：存在确定性错误；
- `2`：输入、解析或工具自身失败，未完成可信分析。

报告级别与进程退出码必须分开，避免把“需要审查”误报成工具故障。

## 9. CLI 与输出契约

```text
procedure-ci check \
  --base-openapi PATH \
  --head-openapi PATH \
  --arazzo PATH \
  [--format json|markdown] \
  [--output PATH]
```

JSON 顶层结构示例：

```json
{
  "schemaVersion": "0.1",
  "summary": {
    "workflows": 1,
    "affectedSteps": 2,
    "errors": 1,
    "reviews": 1,
    "unknowns": 0
  },
  "impacts": [],
  "diagnostics": []
}
```

Markdown 报告按以下顺序呈现：结论、受影响工作流、每个步骤的依赖路径、确定性错误、需要审查项、不支持项。相同输入必须产生稳定排序和稳定文本，便于快照测试与 PR diff。

## 10. 首个验证夹具

使用 **Webhook onboarding** 工作流：

1. `createWebhookSubscription`
2. `sendTestEvent`
3. `getWebhookDelivery`
4. 可选 `deleteWebhookSubscription`

至少构造六个 head 变体：

| 变体 | 预期结果 |
| --- | --- |
| 修改无关操作 | 工作流不受影响 |
| 请求新增必填字段 | 对应步骤 `review`；示例无效时 `error` |
| 嵌套 `$ref` 的枚举收窄 | 通过传递依赖定位对应步骤 |
| 安全要求变化 | 依赖步骤受影响 |
| 删除已引用操作 | `OAS_OPERATION_MISSING` |
| 保留 `operationId` 但改变 path/method | `review` 并显示前后定位 |

每个变体同时断言 JSON、Markdown 和退出码。

## 11. 测试策略

- 单元测试：索引、引用递归、循环、表达式抽取、结构比较、严重级别；
- 夹具测试：六个 Webhook 变体的端到端结果；
- 快照测试：JSON 字段和 Markdown 排序稳定；
- 性质测试候选：对象键顺序变化不改变结果；
- 负向测试：坏 YAML、重复 `operationId`、外部引用、不支持表达式和超限输入；
- 手工验证：在一个真实或脱敏样本上由维护者标注实际影响，再与工具结果对比。

所有确定性错误代码至少有一个正例和一个不触发反例。

## 12. M0 的技术取舍

实际栈：Python 3.12、`argparse`、`dataclasses`、`jsonschema` 4.26.0、pytest 8.4.2、Ruff 0.16.5，以及满足 YAML 1.2、安全加载要求的 `ruamel.yaml` 0.18.17。

M0 已完成：

1. 验证 Arazzo 1.1.x 样例能被安全读取并保留来源指针；
2. 验证 OpenAPI 3.1 内部引用和循环 Schema；
3. 验证 JSON Schema 2020-12 的字面量示例检查；
4. 检查依赖的 Python 3.12 兼容性并写入 `pyproject.toml`；
5. 采用 `ruamel.yaml` YAML 1.2 安全加载，避免 YAML 1.1 隐式布尔值导致类型漂移。

M0 已在 Python 3.12 隔离环境完成；依赖和开发命令以 `pyproject.toml` 为准，当前不等待主机未具备的 Python 3.14。

## 13. 安全与可复现边界

- 默认只读用户显式传入的本地文件，不扫描整个仓库；
- 禁止自定义 YAML tag、模板求值、Shell 和网络访问；
- 对文件大小、引用深度、节点数和诊断数量设置上限；
- 不读取环境变量作为工作流输入，不输出 Token 或真实密钥；
- 报告保存相对来源位置和 JSON Pointer，不复制大段业务数据；
- 同一输入、同一版本必须产生确定性结果。

## 14. 阶段与耗时

| 阶段 | 交付物 | 估时 |
| --- | --- | ---: |
| M0：可行性验证 | 库评估、解析 spike、首个夹具；用户访谈转入 M5 | 3–5 天 |
| M1：索引与依赖图 | OpenAPI/Arazzo 索引、内部 `$ref`、图查询 | 15–22 小时 |
| M2：差异与诊断 | base/head 比较、诊断代码、退出码 | 18–26 小时 |
| M3：CLI 与报告 | 稳定 JSON/Markdown、端到端夹具 | 12–18 小时 |
| M4：试用修正 | 真实样本、误报分析、文档 | 15–24 小时 |

严格 MVP 合计约 60–90 小时，即每周 15 小时约 4–6 周。若加入 GitHub Action、PR 定位、Skill 渲染和正式 pilot，约 90–135 小时，6–9 周。

## 15. 验证指标与停止条件

M5 记录目标团队的工作流数量、当前审查方法与耗时，并衡量工具的 precision、recall、`unknown` 比例和是否改变审查决定。

任一条件满足时停止产品化：

- 5 支目标团队中少于 2 支维护可分析的工作流；
- 真实样本的关键误报率持续高于 20%；
- 第 3 周仍无法稳定处理内部引用和循环 Schema；
- 上游成熟工具已提供等价的步骤级影响分析；
- 用户只需要通用 OpenAPI breaking-change 检查，而不关心工作流步骤。

若技术成立但需求不足，将成果收缩为 `arazzo-impact-lab`：保留研究报告、夹具和可复用解析实验，控制总投入在 30–50 小时。

## 16. 后续而非 MVP

- 复用 oasdiff 等成熟引擎提供更丰富的 API 变化分类；
- 输出 GitHub Action 注释和 SARIF；
- 从 Arazzo 生成 Agent Skill 的只读说明页；
- 支持 OpenAPI 3.2、外部引用、AsyncAPI 和多文档工作流；
- 与 Arazzo runner 的 dry-run/trace/replay 结果组合。

## 17. MVP 后的唯一入口

先进行历史变更回放和目标用户访谈，记录误报、漏报和审阅时间；不因单个样本直接扩展到
Action、服务端、真实 API 执行或完整 Arazzo validator。
