# Procedure CI

Procedure CI 是一个严格 MVP 阶段的开发者工具项目。它分析 OpenAPI 变更对
[Arazzo](https://spec.openapis.org/arazzo/latest.html) 工作流的影响，并把结果定位到
具体 `workflowId`、`stepId` 和依赖项，供 pull request 审阅。

当前产品假设是：API 团队已经把多步集成流程写成 Arazzo，但在修改 OpenAPI 时，
现有工具很难直接回答“哪些流程步骤需要重新审阅”。

项目不生成工作流、不执行真实 API，也不定义新的流程 DSL。核心路径保持确定性：

```text
base/head OpenAPI + current Arazzo
                    ↓
          语义依赖图和实体变更
                    ↓
          workflow/step 影响报告
```

## 当前状态

- 状态：严格 MVP 核心已实现；M5a 已固定 12 个可还原历史变化，但均来自生成/
  自动重建的 Arazzo 1.0.1 资产，功能扩展仍冻结；
- 入口：三输入 `base OpenAPI + head OpenAPI + 当前 Arazzo`；
- 输出：稳定 JSON/Markdown，退出码 `0`（无确定错误）、`1`（确定错误）、`2`（输入/工具失败）；
- 边界：离线、只读、内部 `$ref`、OpenAPI 3.1、Arazzo 1.1.x 的 operationId 同步子集；
  source description 必须唯一、类型为 `openapi`，且有合法名称和非空 URL；
- 公开仓库：[`CrAyoN-V587/procedure-ci`](https://github.com/CrAyoN-V587/procedure-ci)；
  尚未实现 GitHub Action、API 服务或真实 API 执行。

## 本地运行

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m procedure_ci check `
  --base-openapi tests/fixtures/webhook_onboarding/base/openapi.yaml `
  --head-openapi tests/fixtures/webhook_onboarding/head/openapi.yaml `
  --arazzo tests/fixtures/webhook_onboarding/workflow.yaml `
  --format markdown
```

当前已验证环境：Windows、Python 3.12.7、pip 24.2（虚拟环境内）；项目要求 Python 3.12+，
尚未在 3.13/3.14 运行回归。依赖为
`ruamel.yaml` 0.18.17、`jsonschema` 4.26.0、pytest 8.4.2、Ruff 0.16.5。

## 验证

```powershell
.venv\Scripts\python.exe -m pip check
.venv\Scripts\ruff.exe check src tests
.venv\Scripts\python.exe -m pytest -q
```

Webhook onboarding 夹具覆盖无关变化、嵌套引用、必填字段、认证、删除操作、path
移动、外部引用、动态 payload、输出依赖环、重复 operationId、YAML 安全加载和循环引用；
同时验证官方 `$sourceDescriptions.<name>.<operationId>` 写法、producer 输出传播、参数/header
大小写归一化、官方 `$response.header.*`/`$response.body` 表达式和超限输入，详见
[夹具说明](tests/fixtures/webhook_onboarding/README.md)。

## 文档入口

- [PROJECT.md](PROJECT.md)：目标、范围、阶段和恢复入口；
- [docs/RESEARCH.md](docs/RESEARCH.md)：竞品、需求证据和立项判断；
- [docs/DESIGN.md](docs/DESIGN.md)：架构、数据模型、CLI、验收和风险；
- [docs/M5-CORPUS.md](docs/M5-CORPUS.md)：M5a 候选语料、精确历史边界、分层与 M5b 恢复入口；
- [docs/PROGRESS.md](docs/PROGRESS.md)：可恢复的实现进度和实际验证记录；
- [docs/decisions/0001-use-arazzo.md](docs/decisions/0001-use-arazzo.md)：采用 Arazzo、放弃自定义 IR 的决策。
- [docs/decisions/0002-three-input-current-arazzo.md](docs/decisions/0002-three-input-current-arazzo.md)：固定三输入和当前 Arazzo 语义的决策。
- [docs/decisions/0003-gate-expansion-on-independent-pilots.md](docs/decisions/0003-gate-expansion-on-independent-pilots.md)：用独立维护者和对照回放约束功能扩展。

## License

[MIT](LICENSE)
