# Procedure CI M5b Gold Set 冻结记录

- 冻结时间：2026-08-31T13:05:01+08:00
- 阶段：M5b fast-fail
- 读者：执行对照回放的研究者、API/DevEx 维护者、产品投资决策者
- 边界：只标注代表性历史样本；冻结后才允许查看生成器、validator、oasdiff 和 Procedure CI 输出

## 结论先行

M5a 的 12 个历史样本均不能直接进入当前 Procedure CI 0.1.0：PCH-01–06 同时使用
OpenAPI 3.0.0 和 Arazzo 1.0.1；PAY-01–06 使用 Arazzo 1.0.1，且 OpenAPI source name
是包含 `/` 的生成机器绝对路径，不符合当前输入约束。原始样本可运行覆盖率是 **0/12**。

本轮只冻结两个预先选定的代表样本。PCH-01 的 OpenAPI 和 Arazzo 历史差异在冻结前被误看，
因此标注独立性已经污染，不能用于任何指标。PAY-05 只完成 5 个直接 operation 变化的部分
gold；共享 schema 的传递闭包尚未人工穷举，不能把其余 step 当成正式负例。完整标注样本数为
**0**，低于预设的 10 个，precision、recall 和增量价值均不可计算。

## 冻结方法

标注人在冻结前只允许查看：

1. base/head OpenAPI 的原始差异；
2. head Arazzo；
3. 只列出 operationId、路径和组件名的机械提取，不得让工具判断影响闭包或严重度。

冻结后才允许查看 base/head Arazzo 差异和所有对照工具输出。每条记录使用以下字段：

`sample_id`、`base_sha`、`head_sha`、`source_class`、`openapi_version`、
`arazzo_version`、`change_id`、`oas_entity_kind`、`operation_id`、
`oas_pointer_before`、`oas_pointer_after`、`change_kind`、`workflow_id`、`step_id`、
`dependency_kind`、`dependency_path`、`gold_outcome`、`decision_required`、
`arazzo_action`、`confidence`、`evidence_pointers`、`annotation_status`、`frozen_at`。

枚举语义：

- `gold_outcome`：`none | info | review | broken | unobservable`；
- `arazzo_action`：`none | review | update | delete | unknown`；
- `annotation_status`：`complete | partial | unresolvable`；
- 动态生成噪声、私有语义、无法稳定映射的 operationId，或预计超过 90 分钟仍无法判断时，
  必须降为 `partial` 或 `unresolvable`，不得猜测补齐。

## 12 个样本的资格矩阵

| 样本 | source class | OpenAPI | Arazzo | 当前 CLI 的首个阻塞 | 解除版本标记后的下一阻塞 | 正式回放 |
| --- | --- | --- | --- | --- | --- | --- |
| PCH-01–06 | B | 3.0.0 | 1.0.1 | 不接受 Arazzo 1.0.1 | 不接受 OpenAPI 3.0.0 | 否 |
| PAY-01–06 | C | 3.1.0 | 1.0.1 | 不接受 Arazzo 1.0.1 | source name 含 `/`，不满足 `[A-Za-z0-9_-]+` | 否 |

这里只记录输入资格，不把“不支持”改写成产品缺陷。后续若只把副本中的 Arazzo 版本标记改为
1.1.0，该探针仍有第二个已知阻塞，只能验证 fast-fail 顺序；它不是有效样本，也不进入覆盖率或指标。

## 代表样本处置

| 样本 | 预选理由 | 冻结状态 | 可进入正式指标 | 说明 |
| --- | --- | --- | --- | --- |
| PCH-01 | B 类、结构化源生成、多 step | `unresolvable` | 否 | 冻结前误看 base/head Arazzo 差异，独立标注被污染；不改选其他 PCH 样本，以免产生选择偏差 |
| PAY-05 | C 类、自动重建、含 operation removal | `partial` | 否 | 只冻结直接 operation slice；共享组件的传递影响未穷举 |

PCH-01 不保留任何 gold 行，也不根据已经看到的 Arazzo 作者改动反推标签。

## PAY-05 部分 gold

共同字段：

- `sample_id`: `PAY-05`
- `base_sha`: `33df21dd2aebb948ce42517e7fbecb18d75d614b`
- `head_sha`: `df23654ee6fc915f1bc4ce1bee029ea988011078`
- `source_class`: `C`
- `openapi_version`: `3.1.0`
- `arazzo_version`: `1.0.1`
- `step_id`: `test`
- `dependency_kind`: `operation`
- `annotation_status`: `partial`
- `frozen_at`: `2026-08-31T13:05:01+08:00`

| change_id | operation_id / workflow_id | OAS pointer before → after | change_kind | dependency_path | gold_outcome | decision_required | arazzo_action | confidence | evidence_pointers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `operation:getFeePrice:removed` | `getFeePrice` | `/paths/~1v0~1fees~1{id}~1price~1{subscriptionId}/get` → `-` | removed | `workflow:getFeePrice → step:test → operationId:getFeePrice` | broken | true | delete | high | base OAS operation exists；head OAS operation absent；head Arazzo `workflowId:getFeePrice/stepId:test` still references it |
| `operation:createPrice:modified` | `createPrice` | `/paths/~1v0~1prices/post` → same | modified | `workflow:createPrice → step:test → operationId:createPrice` | review | true | review | medium | base/head OAS operation differs；head Arazzo `workflowId:createPrice/stepId:test` references it |
| `operation:listPlans:modified` | `listPlans` | `/paths/~1v0~1plans/get` → same | modified | `workflow:listPlans → step:test → operationId:listPlans` | review | true | review | medium | base/head OAS operation differs；head Arazzo `workflowId:listPlans/stepId:test` references it |
| `operation:listPrices:modified` | `listPrices` | `/paths/~1v0~1prices/get` → same | modified | `workflow:listPrices → step:test → operationId:listPrices` | review | true | review | medium | base/head OAS operation differs；head Arazzo `workflowId:listPrices/stepId:test` references it |
| `operation:updatePrice:modified` | `updatePrice` | `/paths/~1v0~1prices~1{id}/patch` → same | modified | `workflow:updatePrice → step:test → operationId:updatePrice` | review | true | review | medium | base/head OAS operation differs；head Arazzo `workflowId:updatePrice/stepId:test` references it |

`getFeePrice` 的 `delete` 表示当前引用必须删除；如果维护者知道替代 operation，也可以重新绑定，
但该私有业务决定不从公开文件中猜测。其余 4 行只要求审阅，不声称一定需要修改 Arazzo。

PAY-05 head 中其余 step 只在“直接 operation 变化”这一窄切片内暂作隐式负例。由于
`FeePrice`、`Plan`、`Price`、`ReconciledFeatureAdded` 和 `schemas-Price` 等共享组件也发生变化，
完整传递闭包尚未人工判断；这些隐式负例不得进入 false-positive 或 precision 统计。

## 指标与停止边界

| 指标 | 本轮结果 | 可否作产品证据 |
| --- | ---: | --- |
| 原始样本可运行覆盖率 | 0/12 | 可以，作为覆盖边界 |
| 完整 gold 样本 | 0/12 | 可以，作为研究停止信号 |
| Procedure CI precision / recall | 不可计算 | 否 |
| 相对 generator / validator / oasdiff 的增量价值 | 0 条已证明 | 否 |
| 已验证 A 类维护者 | 0 | 否 |

Procedure CI 退出码 `2` 只表示 `not_analyzed`（输入/工具失败），不能算作命中、漏报、
`unknown` 或“发现问题”。如果后续基线确认上述阻塞与邻接工具已经覆盖主要维护动作，M5b 应按
fast-fail 收尾，保持功能冻结，并把项目定位为有验证边界的学习/研究工具。

## 角色与使用情景

| 角色 | 现在能据此做什么 | 不能据此声称什么 |
| --- | --- | --- |
| M5 研究者 | 按固定顺序运行基线，区分 `partial`、`unresolvable` 与工具输出 | 不能用污染或部分标注计算正式指标 |
| API/DevEx 维护者 | 理解 operation 删除为何要求明确决策 | 不能把生成资产当成人工维护者需求 |
| 生成器维护者 | 检查结构化源与生成出口是否同步 | 不能从 PCH-01 反推独立 gold |
| SDK contract-test 维护者 | 检查自动重建是否已经删除或修复 stale test | 不能把 C 类自动资产当作 Procedure CI 增量价值 |
| 产品投资决策者 | 用 0/12 覆盖、0 个完整 gold、0 个 A 类维护者执行停止规则 | 不能据此授权 Arazzo 1.0、OpenAPI 3.0 或 source-name 兼容开发 |

下一步只运行代表性基线并记录输出；不修改 `src/`、测试或产品输入契约。
