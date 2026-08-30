# Procedure CI 进度

本文件是实现阶段的恢复入口；设计背景和证据见 `PROJECT.md`、`RESEARCH.md` 和
`DESIGN.md`。所有结果均为本地离线验证；项目已初始化本地 Git `main` 分支，尚未接入远程仓库。

## 当前状态（2026-08-30）

严格 MVP 核心已经完成：

- `ruamel.yaml` + `jsonschema` 依赖 spike 已完成，写入 `pyproject.toml`；项目要求 Python 3.12+，
  当前只在 Python 3.12.7 验证；
- 安全本地 loader 支持 JSON/YAML、YAML 1.2、大小/节点上限和内部引用诊断；
- OpenAPI 3.1 索引支持 operationId、组件 Schema、参数、请求/响应传递引用和认证方案；
- Arazzo 1.1.x operationId 同步子集支持 workflow/step、outputs、runtime output 引用和依赖环检查；
- Arazzo 只接受恰一个 `type: openapi` source description，并支持 plain operationId 与官方
  `$sourceDescriptions.<name>.<operationId>` 写法；超出 MVP 的 key/runtime expression 明确报告
  `UNSUPPORTED_ARAZZO_FEATURE: unknown`。
- base/head OpenAPI 实体比较支持 behavior/example/documentation 分类；
- 依赖图将 Schema、参数和安全方案变化映射到当前 Arazzo step，并沿 producer 的 response/output
  引用和显式 `dependsOn` 任意深度传播到 consumer；base/head 图取可达依赖并集，以保留删除实体
  的旧路径；
- 字面量 request payload 使用 JSON Schema 校验，含运行时表达式的 payload 报告 `unknown`；
- CLI 接受三个输入：`--base-openapi`、`--head-openapi`、`--arazzo`；
- JSON/Markdown 报告排序稳定，退出码为 `0`（无确定错误）、`1`（确定错误）、`2`（输入/工具失败）。

## 实际验证

执行目录：项目根目录。

```text
.venv\Scripts\python.exe -m pip check
No broken requirements found.

.venv\Scripts\ruff.exe check src tests
All checks passed!

.venv\Scripts\ruff.exe format --check src tests
16 files already formatted

.venv\Scripts\python.exe -m pytest -q
40 passed
```

代表性 CLI：

```text
.venv\Scripts\python.exe -m procedure_ci check \
  --base-openapi tests/fixtures/webhook_onboarding/base/openapi.yaml \
  --head-openapi tests/fixtures/webhook_onboarding/head/openapi.yaml \
  --arazzo tests/fixtures/webhook_onboarding/workflow.yaml \
  --format json
```

基线输出为 `affectedSteps=0`、`errors=0`，且重复执行 JSON 字节一致。测试还验证了
操作删除和无效字面量 payload 的退出码 `1`，缺失输入的退出码 `2`，外部引用和动态
payload 的 `unknown` 语义。

## 代码入口

```text
src/procedure_ci/
  loader.py          本地安全加载、JSON Pointer 和引用枚举
  oas_index.py       OpenAPI 操作/组件索引和引用诊断
  arazzo_index.py    Arazzo workflow/step/output 索引
  graph.py           当前 Arazzo step 到 OpenAPI entity 的依赖边
  compare.py         base/head 实体变化
  checks.py          影响规则、样例校验和退出判定所需诊断
  report_json.py     版本化 JSON
  report_markdown.py 可审阅 Markdown
  cli.py             三输入 CLI
```

## 已知限制

- 只接受 OpenAPI 3.1、Arazzo 1.1.x 的同步 OpenAPI operationId 子集；sourceDescriptions 必须恰有
  一个 `type: openapi` 条目；
- 只读取显式本地文件和文档内部 `$ref`，不读取 sourceDescription URL；
- 不处理外部引用、AsyncAPI、复杂运行时表达式、跨文档 workflow；
- 不执行 API、Shell、模板或 Arazzo runner；
- 通用 OpenAPI breaking-change 分类和完整 Arazzo validator 不在范围内；
- `$ref` 递归深度超过 `MAX_REF_DEPTH` 会按输入错误退出 2；完整 Arazzo key、runtime expression
  和跨 workflow output 语义会保守报告 `unknown`，不执行或猜测；
- Arazzo 官方 response runtime 只支持 `$response.header.<name>`、`$response.body` 和
  `$response.body#/...`；非标准 `$response.headers.*`、selector、非字符串 output、参数/
  reusable `$ref` 和非 JSON request body 会报告 `UNSUPPORTED_ARAZZO_FEATURE: unknown`。
- OpenAPI `$dynamicRef`、`$anchor` 和可能改变引用基址的 `$id` 不解析，报告
  `UNSUPPORTED_OAS_FEATURE: unknown`。
- `jsonschema` 对 OpenAPI Schema 的扩展语义只做有限兼容，未知语义会保守报告；
- 当前夹具是脱敏合成样本，尚未证明真实团队采用 Arazzo 或愿意为 step-level impact 付费。

## 下一步

只做 M5 验证：收集至少 10 个真实或脱敏历史 API 变更，记录人工标注的受影响 step，
计算 precision/recall/unknown 比例和审阅耗时，并访谈目标团队。满足停止条件时降级为
`arazzo-impact-lab`；没有试点证据前不增加 GitHub Action、服务端、数据库或网络访问。
