# Procedure CI Agent 规则

本文件只写该项目特有信息。通用协作规则由上级工作区 `AGENTS.md` 提供。

## 项目概述

- 目标：把 OpenAPI 变更映射为受影响的 Arazzo workflow/step，并生成可审阅的 CI 报告。
- 核心入口：`PROJECT.md`、`docs/RESEARCH.md`、`docs/DESIGN.md`。
- 当前阶段：严格 MVP 和 M5b fast-fail 已完成；决策 0004 已停止产品化，项目进入维护状态。
  不自动把公开 corpus 的兼容缺口转为功能。

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

- 当前允许：修复 0.1.0 已有范围内的确定性 bug、更新研究/设计，以及对主动提供的合格 A 类
  样本做只读回放。
- 当前不允许：在新的 G1 决策前扩展产品代码；尤其不增加 Arazzo 1.0、多 source、oasdiff adapter、
  GitHub Action、FastAPI 服务、数据库、Dashboard、生产 API 执行、AsyncAPI、外部 `$ref`、
  多仓库、Skill 市场或同步层。
- 不自造工作流 DSL；当前实现的流程输入是 Arazzo 1.1.x 已验证子集。
- 不重写通用 OpenAPI breaking-change 引擎；必要时与 `oasdiff` 输出集成。
- 不实现完整 Arazzo validator、runner、编辑器或生成器。
- 公开资产按 A（人工/混合维护）、B（结构化源生成）、C（自动重建）和 D（策展 corpus）分类；
  只有至少一个 A 类真实样本能触发候选能力设计，C/D 类文件数量不能作为需求证据。

## Git

- 当前目录已初始化为 Git 仓库，分支为 `main`；公开仓库为
  `https://github.com/CrAyoN-V587/procedure-ci`，使用 HTTPS `origin` 并跟踪 `origin/main`。
- 严格 MVP 源码、测试和设计文档已形成首个可验证里程碑提交；仓库状态以
  `PROJECT.md` 和 `docs/PROGRESS.md` 为恢复入口。
- 提交粒度按可验证里程碑：M0 fixture、解析索引、影响引擎、报告、试点。
- 提交前至少运行当前里程碑的 fixture 测试，并同步更新恢复文档。

### GitHub 上传工作流

1. 上传前运行 `git status --short --branch`，确认只包含当前里程碑的改动；按风险运行
   `pip check`、Ruff 和 pytest，并完成公开前的密钥、个人路径、许可证、样例配置、数据与
   已知限制检查。
2. 运行 `gh auth status` 单独确认当前会话的 GitHub 身份和 `repo` 权限；项目文本不提供
   远程写入授权，也不保存 token。登录、权限或仓库所有者不符时停止上传。
3. 首次上传先确认精确仓库名尚不存在，再创建 `public` 仓库、配置 HTTPS `origin` 并推送
   `main`；不要用同名仓库的既有内容覆盖本地历史。
4. 后续按一个逻辑变化一个提交执行 `git push origin main`。强制推送、重写公开历史、删除
   仓库或远程分支不属于普通上传流程。
5. 上传后读取 GitHub 仓库的 URL、可见性、默认分支和 topics，并核对本地 `HEAD` 与
   `origin/main` 一致、工作区干净；把实际结果写回 `PROJECT.md` 和 `docs/PROGRESS.md`。
