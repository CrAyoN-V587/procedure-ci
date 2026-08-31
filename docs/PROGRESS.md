# Procedure CI 进度

本文件是实现阶段的恢复入口；设计背景和证据见 `PROJECT.md`、`RESEARCH.md` 和
`DESIGN.md`。核心分析结果均为本地离线验证；项目公开仓库为
`https://github.com/CrAyoN-V587/procedure-ci`，本地 `main` 跟踪 `origin/main`。

## 当前状态（2026-08-31）

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

功能代码仍为已验证的 0.1.0；2026-08-31 只更新研究、设计、M5a 语料清单和投资门槛，
没有扩大运行时能力。

## 2026-08-31 调研与设计刷新

- 核对 Arazzo 1.0.1/1.1.0、官方 tooling 和仍开放的 runtime expression/condition 语义问题；
- 对照 Redocly、libopenapi、Jentic/Arazzo Toolkit、Speakeasy、oasdiff 和 PactFlow Drift，确认验证、
  执行、生成、自动同步和通用 diff 已有强相邻能力；
- GitHub code search 显示 Arazzo 公开文件很多，但数量高度受命名和单一策展 corpus 影响，不能当作
  独立用户数量；
- API Evangelist #205 提供真实大规模漂移证据：4,956 个 workflow corpus 中曾有 5,153 个本地
  sourceDescriptions（92%）在 OpenAPI refine/split 后悬空，影响 545 个 provider；该问题也说明
  transform 后缺少重新验证，而不是市场缺少 validator；
- Pachca 的 10 次 Arazzo 文件提交来自结构化 workflow 源的多表面生成；Paygentic 的 29 次提交
  属于 Speakeasy 自动同步 contract tests；Bank API 是 1.1 多步样本，但只有一个历史提交；
- 决策 0003 已冻结功能扩展：只有至少 2 个独立 A 类维护者和与现有工具对照后的增量 step-impact
  证据，才能触发 Arazzo 1.0、多 source、oasdiff adapter 或 GitHub Action 设计。

## 2026-08-31 M5a 语料筛选

- [M5a 语料清单](M5-CORPUS.md) 共 15 个候选：A 1（弱证据）、B 6、C 6、D 2；
- 保留 12 个精确 parent/head OpenAPI + head Arazzo 边界，来自 `pachca/openapi` 和
  `paygentic` 两个独立维护源；
- 逐个核对完整 SHA、共同变更的 OpenAPI/Arazzo 路径、Arazzo 版本以及
  source/workflow/step 数；仓库内未复制第三方原始文件；
- 12 个样本均为 Arazzo 1.0.1 的 B/C 类生成资产，当前 1.1.x 严格 MVP 可直接回放数为 0；
- M5a 只登记生成器、Arazzo validator 和 oasdiff 基线，未运行它们；未写入受影响
  step 或工具输出，避免污染 M5b gold set。

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

python -m build  # 使用已验证的 Python 3.12.7 解释器
Successfully built procedure_ci-0.1.0.tar.gz and procedure_ci-0.1.0-py3-none-any.whl
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

M5a 本轮验证：

```text
GitHub API sample boundary check
12/12 parent SHA and OpenAPI/Arazzo changed paths matched

Markdown local-link check
12 Markdown files; 0 missing local links

public text scan
0 credential patterns; 0 personal absolute paths

.venv\Scripts\python.exe -m pip check
No broken requirements found.

.venv\Scripts\ruff.exe check src tests
All checks passed!

.venv\Scripts\ruff.exe format --check src tests
16 files already formatted

.venv\Scripts\python.exe -m pytest -q
40 passed in 3.64s
```

公开前检查覆盖当前候选文件和完整 Git 历史：凭据特征、本机绝对路径，以及误纳入的虚拟环境、
缓存或构建产物匹配均为 0。MIT 许可证同时写入仓库和 Python 制品元数据。

## GitHub 上传与恢复

- 公开仓库：`https://github.com/CrAyoN-V587/procedure-ci`；可见性为 public，默认分支为 `main`；
- HTTPS `origin`：`https://github.com/CrAyoN-V587/procedure-ci.git`；
- 首次上传基线：`d4f925a`，当时本地 `HEAD` 与远程 `refs/heads/main` 完全一致；
- 完整上传约束和首次/后续流程以项目 `AGENTS.md` 的“GitHub 上传工作流”为准；恢复后先运行
  `git status --short --branch` 和 `gh auth status`，验证当前改动、跟踪关系与会话权限，再按逻辑
  里程碑提交并执行 `git push origin main`；
- 推送后必须重新读取仓库可见性和默认分支，并比较本地 `HEAD` 与远程 `main`，不能只凭
  `git push` 的成功文案判断同步完成。

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

只做 M5b：对 PCH-01–06 和 PAY-01–06 先独立建立 gold set，冻结标签后再执行生成器、
Arazzo validator 和 oasdiff 基线。如果需要先扩展 Arazzo 1.0.1 才能运行 Procedure CI，记录
当前 MVP 的覆盖失败，不在 M5b 修改产品代码。M5c 外部维护者联系和 G1 决策均尚未完成。
