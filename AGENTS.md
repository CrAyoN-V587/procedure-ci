# Procedure CI Agent 规则

本文件只写该项目特有信息。通用协作规则由上级工作区 `AGENTS.md` 提供。

## 项目概述

- 目标：把 OpenAPI 变更映射为受影响的 Arazzo workflow/step，并生成可审阅的 CI 报告。
- 核心入口：`PROJECT.md`、`docs/RESEARCH.md`、`docs/DESIGN.md`。
- 当前阶段：严格 MVP 核心已实现，等待真实历史样本和用户试点；不自动扩展范围。

## 环境和命令

- 当前已验证：Windows、Python 3.12.7、pip 26.1（系统）、Git 2.55.0；项目 `.venv` 使用 pip 24.2。
- 当前未具备：Python 3.14、`uv`。
- 安装/准备：`.venv\Scripts\python.exe -m pip install -e ".[dev]"`。
- 运行：`.venv\Scripts\python.exe -m procedure_ci check --base-openapi PATH --head-openapi PATH --arazzo PATH [--format json|markdown]`。
- 针对性测试：`.venv\Scripts\python.exe -m pytest -q tests/test_procedure_ci.py`。
- 完整测试：`.venv\Scripts\python.exe -m pytest -q`（配置固定项目内 `.pytest-tmp`）。
- 构建或检查：`.venv\Scripts\python.exe -m pip check` 和 `.venv\Scripts\ruff.exe check src tests`。

## 项目约定

- `src/procedure_ci/`：实现；按 loader、index、graph、compare、checks、report 分模块。
- `tests/fixtures/`：base/head OpenAPI、Arazzo 和确定性预期；fixture 是主要验收资产。
- `docs/`：研究、设计、决策和试点结果。
- 诊断状态必须区分 `error`、`review`、`unknown` 和 `info`；不把不支持的语义报告为通过。
- 核心分析必须离线、只读且确定性；LLM 不进入通过/失败判定。
- MVP 只接受本地文件和内部 `$ref`，禁止自动抓取远程引用。
- CLI 当前只有三个输入：base OpenAPI、head OpenAPI 和当前 Arazzo；不读取 base/head Arazzo。
- Arazzo 只接受 1.1.x，且必须有恰一个 `type: openapi` 的 `sourceDescriptions`；支持 plain
  operationId 和官方 `$sourceDescriptions.<name>.<operationId>` 写法；source name 必须匹配
  `[A-Za-z0-9_-]+`，URL 必须是非空字符串。
- Arazzo 动态 payload 只报告 `unknown`，字面量 payload 才进入 JSON Schema 校验；不执行表达式。
- 未实现的 Arazzo key/runtime expression 必须报告 `UNSUPPORTED_ARAZZO_FEATURE: unknown`，不得静默通过。
- runtime MVP 只接受官方 `$response.header.<name>`、`$response.body`、`$response.body#/...`
  等已列表达式；`$response.headers.*`、selector、非字符串 output、参数/reusable `$ref` 和
  非 `application/json` requestBody 均保守报告 unknown。

## 研究与立项工作流

后续评估新方向时按以下顺序推进：

1. 浏览近期 GitHub Star 增长较快的项目，记录快照日期、增长信号和来源；Star 只用于发现候选，不直接代表需求。
2. 不限制候选与既有项目相关；先解释项目服务的用户、触发场景、替代方案和增长背后的需求。
3. 对候选 idea 分别写清需求、技术路径、MVP 边界、耗时、证据强弱和停止条件，再判断是否值得投入。
4. 对入选 idea 做二次专项调研，优先核对公开标准、成熟相邻工具和真实使用样本，避免重复造轮子。
5. 编码前先建立独立项目目录，补齐 `PROJECT.md`、调研、设计和关键决策；先通过 M0 可行性与用户验证门槛，再初始化实现。

本项目是该流程的首个落地：趋势调研只帮助发现 API/Agent 工作流方向，最终方案依据 Arazzo 标准、竞品缺口和真实漂移表面收敛为 Arazzo Impact CI。

## 修改边界

- 当前允许：完善设计、M0 依赖验证、fixture、最小 CLI 核心和必要的回归测试。
- 当前不允许：FastAPI 服务、数据库、Dashboard、生产 API 执行、AsyncAPI、外部 `$ref`、多仓库、Skill 市场或同步层。
- 不自造工作流 DSL；Arazzo 1.1 是流程源格式。
- 不重写通用 OpenAPI breaking-change 引擎；必要时与 `oasdiff` 输出集成。
- 不实现完整 Arazzo validator、runner、编辑器或生成器。

## Git

- 当前目录已初始化为本地 Git 仓库，分支为 `main`；尚未配置远程仓库。
- 严格 MVP 源码、测试和设计文档已形成首个可验证里程碑提交。
- 提交粒度按可验证里程碑：M0 fixture、解析索引、影响引擎、报告、试点。
- 提交前至少运行当前里程碑的 fixture 测试；远程连接和公开发布另行处理。
