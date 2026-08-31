# Procedure CI M5a 语料筛选清单

- 快照日期：2026-08-31
- 阶段：M5a 已完成
- 读者：准备人工标注和对照回放的研究者
- 边界：只保存公开仓库、路径、完整 commit SHA 和分类结论；不复制第三方原始文件，
  不记录受影响 step 或工具输出

## 结论

M5a 筛选了 15 个候选，其中 12 个具有精确、可公开读取的 parent/head
OpenAPI 边界和 head Arazzo，覆盖 2 个独立维护源。数量门槛通过，但这 12 个样本均为
Arazzo 1.0.1：6 个是结构化源的生成出口（B），6 个是会随 OpenAPI 自动重建的
contract tests（C）。它们可用于 M5b 的生成器/负向对照，但不证明 A 类用户需求。

当前 0.1.0 只接受 Arazzo 1.1.x，因此 12 个保留样本中可直接由现有 CLI 回放的数量是
0。这是覆盖结果，不是先扩展 1.0.1 支持的授权。M5b 必须先独立建立 gold set 和基线，
再决定是否有值得解除的产品阻塞。

| 指标 | 结果 |
| --- | ---: |
| 候选数 | 15 |
| 分类 | A：1（弱证据，不计入已验证维护者）；B：6；C：6；D：2 |
| 可还原的 OpenAPI parent/head + head Arazzo | 12 |
| 可还原样本的独立维护源 | 2（`pachca/openapi`、`paygentic`） |
| 当前 MVP 可直接回放 | 0 |
| 已验证 A 类维护者 | 0 |

## 纳入口径

候选记录字段包括 `sample_id`、仓库/资产路径、`independent_source_id`、A/B/C/D 类型与
依据、Arazzo 版本、source/workflow/step 数、维护方式、base/head 完整 SHA、OpenAPI 和
Arazzo 路径、候选变化类型、可还原性、MVP 可回放性、可用基线及保留/排除理由。

“可还原”必须同时满足：

1. base 和 head 是公开可读的精确 commit，优先使用单提交的 parent/head；
2. base/head OpenAPI 路径可定位，head 的 Arazzo 路径可定位；
3. 不需要猜测缺失的私有生成源或历史文件；
4. 可还原不等于现有 MVP 可回放，版本、source 数和输入语义单独判定。

A 类的最低资格统一为：一个独立维护源至少有一条人工或混合维护、至少 2 step、
跨至少 2 operation、且不会每次由同一生成器完整重建的 Arazzo。拥有 2–3 条 workflow
是更强的用户信号，不是入类硬门槛。

## 保留样本：Pachca（B）

共同字段：

- 仓库/独立源：[`pachca/openapi`](https://github.com/pachca/openapi)；
- base/head OpenAPI：`packages/spec/openapi.yaml`；head Arazzo：
  `apps/docs/public/workflows.arazzo.yaml`；
- 版本和规模：Arazzo 1.0.1，1 source；workflow/step 数见表；
- 分类依据：Arazzo 是 `packages/spec/workflows.ts` 结构化源的多个发布出口之一；
- 基线候选：结构化源/生成一致性、Arazzo validator、oasdiff；M5a 只登记，不执行；
- 决定：全部保留到 M5b；可还原，但因 Arazzo 1.0.1 不可由当前 MVP 直接回放。

| sample_id | 日期 | base parent | head | workflow/step | 候选变化面 |
| --- | --- | --- | --- | ---: | --- |
| PCH-01 | 2026-08-28 | [`1e756a37b535349939821bde7789a92a2c6591a9`](https://github.com/pachca/openapi/commit/1e756a37b535349939821bde7789a92a2c6591a9) | [`b0e7d1a6e42c87328c1d1ca208f5f60ce581205e`](https://github.com/pachca/openapi/commit/b0e7d1a6e42c87328c1d1ca208f5f60ce581205e) | 73/121 | operation、request/response schema |
| PCH-02 | 2026-08-12 | [`ec42fa414045dc7673d793fa2af73ce8fe327c4b`](https://github.com/pachca/openapi/commit/ec42fa414045dc7673d793fa2af73ce8fe327c4b) | [`61ae3588926c8b90a843b924bf9cb3d78e6cecf9`](https://github.com/pachca/openapi/commit/61ae3588926c8b90a843b924bf9cb3d78e6cecf9) | 73/120 | operation、parameter、schema |
| PCH-03 | 2026-08-07 | [`8960c69777c22a3936d3de482a01d3b72496c9a4`](https://github.com/pachca/openapi/commit/8960c69777c22a3936d3de482a01d3b72496c9a4) | [`d1156c738c244165252b20b90dd305af219c58de`](https://github.com/pachca/openapi/commit/d1156c738c244165252b20b90dd305af219c58de) | 70/115 | operation、authentication |
| PCH-04 | 2026-08-01 | [`ca1801c1e109103502e951cecb8fb65dbf17c9df`](https://github.com/pachca/openapi/commit/ca1801c1e109103502e951cecb8fb65dbf17c9df) | [`0f3abd9d5cca038bc74df0fa4326268efd73fc3b`](https://github.com/pachca/openapi/commit/0f3abd9d5cca038bc74df0fa4326268efd73fc3b) | 70/115 | request/response schema |
| PCH-05 | 2026-07-07 | [`8404f37764dd38c49892f6f465a0b23ec8265da2`](https://github.com/pachca/openapi/commit/8404f37764dd38c49892f6f465a0b23ec8265da2) | [`561bf57668ccfaa65a8581086385eb151ca2c33e`](https://github.com/pachca/openapi/commit/561bf57668ccfaa65a8581086385eb151ca2c33e) | 70/115 | operation、security、response |
| PCH-06 | 2026-06-24 | [`1dcb9feccc07a51c0166f8037167a416a834ade6`](https://github.com/pachca/openapi/commit/1dcb9feccc07a51c0166f8037167a416a834ade6) | [`dc5bd88bb2a778cc4fc2261ee8c9dee6aba31321`](https://github.com/pachca/openapi/commit/dc5bd88bb2a778cc4fc2261ee8c9dee6aba31321) | 69/113 | security、request/response schema |

候选变化面只根据提交说明和变更文件类型登记，不是受影响 step 的 gold 标签。

## 保留样本：Paygentic/Speakeasy（C）

共同字段：

- 仓库：[`paygentic/sdk-python`](https://github.com/paygentic/sdk-python)；独立源 ID：`paygentic`，
  其他语言 SDK 不重复计数；
- base/head OpenAPI：`.speakeasy/out.openapi.yaml`；head Arazzo：
  `.speakeasy/tests.arazzo.yaml`；
- 版本和规模：Arazzo 1.0.1，1 source；workflow/step 数见表；
- 分类依据：文件含 `x-speakeasy-test-rebuild: true`，OpenAPI 变化后由 Speakeasy 自动重建测试；
- 基线候选：Speakeasy rebuild、Arazzo validator、oasdiff；M5a 只登记，不执行；
- 决定：全部保留为 M5b 负向对照；可还原，但因 1.0.1 和自动重建语义不计为当前 MVP
  可直接回放或 A 类需求。

| sample_id | 日期 | base parent | head | workflow/step | 候选变化面 |
| --- | --- | --- | --- | ---: | --- |
| PAY-01 | 2026-08-27 | [`025130816db5edec6daf51d6a35aa6c0d88c21ed`](https://github.com/paygentic/sdk-python/commit/025130816db5edec6daf51d6a35aa6c0d88c21ed) | [`a5152040e655bfe83306cbc90bb5bf030b579d3c`](https://github.com/paygentic/sdk-python/commit/a5152040e655bfe83306cbc90bb5bf030b579d3c) | 157/157 | operation、request/response schema |
| PAY-02 | 2026-08-18 | [`8b2bd738f1549a69941b9dbe54438c4539c2d4bd`](https://github.com/paygentic/sdk-python/commit/8b2bd738f1549a69941b9dbe54438c4539c2d4bd) | [`cc557daaf25d887cc221fa5bec9af5b85fc3db70`](https://github.com/paygentic/sdk-python/commit/cc557daaf25d887cc221fa5bec9af5b85fc3db70) | 155/155 | operation、request/response/error schema |
| PAY-03 | 2026-08-06 | [`2d2a9b608d3e8a89b775513d27acad7145b460e6`](https://github.com/paygentic/sdk-python/commit/2d2a9b608d3e8a89b775513d27acad7145b460e6) | [`8b2bd738f1549a69941b9dbe54438c4539c2d4bd`](https://github.com/paygentic/sdk-python/commit/8b2bd738f1549a69941b9dbe54438c4539c2d4bd) | 154/154 | request/response schema |
| PAY-04 | 2026-07-30 | [`695c75ad9fb8642def00dc6f083e8902a7124bc6`](https://github.com/paygentic/sdk-python/commit/695c75ad9fb8642def00dc6f083e8902a7124bc6) | [`2d2a9b608d3e8a89b775513d27acad7145b460e6`](https://github.com/paygentic/sdk-python/commit/2d2a9b608d3e8a89b775513d27acad7145b460e6) | 154/154 | operation、request/response/error schema |
| PAY-05 | 2026-07-18 | [`33df21dd2aebb948ce42517e7fbecb18d75d614b`](https://github.com/paygentic/sdk-python/commit/33df21dd2aebb948ce42517e7fbecb18d75d614b) | [`df23654ee6fc915f1bc4ce1bee029ea988011078`](https://github.com/paygentic/sdk-python/commit/df23654ee6fc915f1bc4ce1bee029ea988011078) | 150/150 | operation removal、response schema |
| PAY-06 | 2026-07-08 | [`105b37c27ee83a75d8b0558de0251e92cde8bad1`](https://github.com/paygentic/sdk-python/commit/105b37c27ee83a75d8b0558de0251e92cde8bad1) | [`45b362c59c1f321743cfc4aba52ab7b4f0d0bb9a`](https://github.com/paygentic/sdk-python/commit/45b362c59c1f321743cfc4aba52ab7b4f0d0bb9a) | 149/149 | request/response/error schema |

## 边界候选：A 与 D

| sample_id | 分类 / 独立源 | 资产和规模 | 历史边界 | 可还原 / MVP 可回放 | 决定 |
| --- | --- | --- | --- | --- | --- |
| BANK-01 | A（弱证据）/ `erwinkramer/bank-api` | [`.arazzo/v1.arazzo.yaml`](https://github.com/erwinkramer/bank-api/blob/d26843871fa3186743d1f58f53d975cf422cb9b2/.arazzo/v1.arazzo.yaml)；1.1.0，1 source，1 workflow/3 steps | 唯一触及该文件的历史提交是 [`367764011e8590807c660186a09feec66ec8f966`](https://github.com/erwinkramer/bank-api/commit/367764011e8590807c660186a09feec66ec8f966)，仅重命名/修改 Arazzo 辅助文件，未形成相关 OpenAPI parent/head 对 | 否 / 否 | 作为手写形态候选保留，但在维护者确认前不计入已验证 A 类，不进入 M5b 指标 |
| AE-01 | D / `api-evangelist` | [roadmap #205](https://github.com/api-evangelist/roadmap/issues/205)；4,956 个 workflow 的策展 corpus | Issue 记录 refine/split 后的大规模 source relocation，但不是单一仓库的精确 OpenAPI parent/head + head Arazzo 样本 | 否 / 否 | 保留为需求和压力证据；不按 545 个 provider 计独立用户，不进入 M5b 样本数 |
| AE-02 | D / `api-evangelist` | [`stripe-attach-payment-method-workflow.yml`](https://github.com/api-evangelist/stripe/blob/454b2faee2179f27ba341c65eecddaf48d4e84de/arazzo/stripe-attach-payment-method-workflow.yml)；1.0.1，3 source，1 workflow/3 steps | [`324cd181849f74bbeb71a184318364ee3363cbdf`](https://github.com/api-evangelist/stripe/commit/324cd181849f74bbeb71a184318364ee3363cbdf) → [`454b2faee2179f27ba341c65eecddaf48d4e84de`](https://github.com/api-evangelist/stripe/commit/454b2faee2179f27ba341c65eecddaf48d4e84de)；该提交是 Arazzo source repoint，没有 OpenAPI 变更 | 否 / 否 | 保留为 workflow-only 修复边界；当前三输入设计不评估 base/head Arazzo diff |

## M5b 恢复入口

M5b 可以开始，但不等于已通过 G1。执行顺序是：

1. 只对 PCH-01–06 和 PAY-01–06 建立独立 gold set，先记录真实受影响的 workflow/step、
   依赖路径和是否需要修改 Arazzo；
2. 标注人在未看 Procedure CI 输出时冻结 gold set；
3. 再运行结构化源/生成器、Arazzo validator 和 oasdiff 基线；
4. 如果仍需先修改产品代码才能运行 Procedure CI，记录覆盖失败，不在 M5b 内偷渡功能；
5. 只在存在两个经确认的独立 A 类维护者、对照指标和真实审阅收益后进入 G1。

## 角色与使用情景

| 角色 | 触发条件 | 输入 | 本文档给出的输出 | 决定 |
| --- | --- | --- | --- | --- |
| M5 研究者 | 准备人工标注历史 API 变化 | 公开仓库与 commit | 可还原边界、资产类型和基线候选 | 哪些样本可进入 M5b |
| API/DevEx 维护者 | OpenAPI 变更后需判断多步流程 | base/head OpenAPI + 当前 Arazzo | 本文档不提供产品报告，只判断其资产是否属于 A 类候选 | 是否值得参与试点 |
| 生成器维护者 | 同一结构化源生成 OpenAPI/Arazzo | B 类历史提交 | 生成出口的可还原对照 | 是否需要额外 generator QA |
| SDK contract-test 维护者 | 测试会随 OpenAPI 自动重建 | C 类历史提交 | 负向对照 | 现有重建机制是否已满足需求 |
| 产品投资决策者 | M5b/M5c 证据齐备 | 标注、基线、A 类维护者与审阅收益 | A 是目标、B 是次要 QA、C 是负向对照、D 是压力语料的分层证据 | 继续产品化或收尾为 research tool |

本文档的“保留”只表示可进入标注，不表示需求成立、维护者认可或工具通过。
