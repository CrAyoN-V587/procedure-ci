# Procedure CI

状态：严格 MVP 与 M5b 已完成；停止产品化，保留 0.1.0 为研究/作品集工具
类型：P2 开发者工具 / Agent 工程
开始日期：2026-08-29
最近更新：2026-08-31
时间箱：严格 MVP 已完成；M5 在 fast-fail 后提前收尾，不再安排新功能开发

## 30 秒上下文

一句话目标：把 OpenAPI 变更映射到受影响的 Arazzo workflow/step，输出确定性、可定位、可供 PR 审阅的影响报告。

当前阶段：M5b 已按冻结协议完成代表性对照。12 个样本全部属于 B/C 类 Arazzo 1.0.1
生成资产，当前 CLI 原始样本可运行覆盖为 0/12；complete gold 和已验证 A 类维护者均为 0。
技术缝隙存在，但相对 validator/generator/oasdiff 的产品增量没有得到可运行证据。

下一步：无计划内产品开发。只维护现有 0.1.0；若用户或维护者主动提供符合 A 类资格且位于
既定 OpenAPI 3.1 + Arazzo 1.1.x 边界内的样本，再按 [M5b 冻结协议](docs/M5-GOLD.md)
做只读回放并重新评审 G1。

最近验证：2026-08-31 在 gold 提交后运行 Redocly 2.49.0、oasdiff 1.30.0、Pachca
generator 与当前 CLI 的代表性基线；实现代码未变更，结果见 [M5b 对照](docs/M5-BASELINES.md)。

## 问题和价值

- 要解决的问题：OpenAPI PR 会报告 endpoint/schema 变化，但维护者仍需人工判断哪些多步业务流程、哪个步骤以及哪条跨步骤数据依赖需要复查。
- 目标用户：把 OpenAPI 和 Arazzo 保存在 Git 中的 API 平台、Developer Experience、SDK 或 Agent 工具团队。
- 触发场景：API 的 operation、request/response schema、认证或 example 改变，PR 审阅者需要看到具体受影响流程。
- 为什么仍值得验证：现有工具分别覆盖 API diff、Arazzo 验证/执行、生成和自动同步，但没有发现
  成熟工具把 OpenAPI entity change 映射为 Arazzo step-level transitive impact。
- 证据边界：API Evangelist 已记录 4,956 个 workflow corpus 中 5,153 个本地 sourceDescriptions
  在 transform 后悬空，证明漂移真实；但现有 validator 重新运行即可发现，且大量公开 Arazzo 来自
  单一策展流程或生成器。尚无两个独立 A 类维护者，也没有留存或付费证据。

## 学习与作品集信号

- 重点练习能力：标准阅读、语义索引、依赖图、结构化诊断、fixture 驱动开发和 CI 集成。
- 希望证明的工程能力：能定义清晰的数据契约，区分确定错误与待审阅风险，并用历史变更和指标验证工具价值。
- 个人增量：不是再做 parser/runner，而是实现 `OpenAPI entity → transitive dependency → Arazzo step → review report`。

## 范围

包含：

- OpenAPI 3.1 和采用到的 Arazzo 1.1.x 子集；
- 单个本地 base/head OpenAPI 文档、单个本地当前 Arazzo 文档、内部 `$ref`；
- 首版要求稳定且唯一的 `operationId`；
- base/head 语义图、实体变化、反向影响映射；
- operation、parameter、request、response、security、example 和传递 schema 依赖；
- 当前 head 的确定性引用和 example 校验；
- JSON 与 Markdown 报告；
- 稳定 CLI 使用示例；GitHub Action 只有在 G1 通过且报告被真实用于 PR 决策后才考虑。

不包含：

- 自定义 Procedure YAML/IR；
- 从 PDF、网页或自然语言自动生成流程；
- LLM 参与 CI 通过/失败判定；
- 生产 API 执行、Arazzo runner 或录制回放；
- 通用 OpenAPI breaking-change 分类；
- 完整 Arazzo validator、编辑器、生成器或 Markdown 转换器；
- AsyncAPI、远程 URL、外部 `$ref`、多仓库和跨文档 workflow；
- FastAPI、数据库、Dashboard、多租户、插件系统或 Skill 同步市场。

## 成功标准

- [x] Webhook onboarding 的正负向 fixture 均得到稳定的 workflow/step 影响结果。
- [x] 无关 operation 变化不误报；二级 `$ref` schema 和 security 变化能传递到正确 step。
- [x] 悬空 operation、无效 example、无法解析的 runtime output 分别产生稳定诊断和源码位置。
- [x] JSON 输出具有版本化 schema；Markdown 报告能从变化定位到 workflow、step、依赖路径和建议动作。
- [x] 从 2 个独立维护源筛出 12 个可还原历史变化。
- [x] 在运行工具前冻结代表性 gold，并披露 PCH-01 的预冻结污染；因 0 个 complete 样本停止正式指标。
- [ ] 至少找到 2 个 A 类维护者，且在 3 个样本中证明相对 validator/generator/oasdiff 的增量
  step-level 决策价值；否则只按学习项目收尾。

## 计划

- [x] M0（3–5 天）：固定标准子集、Webhook fixture、6 个 mutation 和依赖 spike。
- [x] M1（1 周）：完成安全本地加载、OpenAPI/Arazzo 索引和带位置的结构化错误。
- [x] M2（1–2 周）：完成直接/传递依赖图、base/head entity compare 和 step impact。
- [x] M3（1–2 周）：完成 example、security、step output/runtime expression 的确定性检查。
- [x] M4（1 周）：稳定 JSON/Markdown 报告和退出码；Action 示例延期。
- [x] M5a（5–7 小时上限）：15 个候选按 A/B/C/D 分类，保留 12 个可还原 diff；未修改产品代码。
- [x] M5b（fast-fail）：代表性 gold、现有工具基线和 Procedure CI 覆盖探针；未修改产品代码。
- [x] G1（停止）：0/12 原始样本可运行、0 complete gold、0 A 类维护者，不进入 M5c 或下一功能。

## 技术和环境

- 操作系统：Windows；核心能力必须在 Windows 本地可验证。
- 当前可用语言：Python 3.12.7。
- 目标语言：Python 3.12+；当前只在 Python 3.12.7 验证，不人为阻断 Python 3.13/3.14。
- 当前包管理器：pip 26.1；`uv` 当前不可用；项目已使用隔离 `.venv` 安装 MVP 依赖。
- 已采用依赖：`ruamel.yaml` 0.18.17（YAML 1.2 安全加载）和 `jsonschema` 4.26.0（Draft 2020-12 字面量校验）；开发依赖为 pytest 8.4.2、Ruff 0.16.5。
- 安装/准备命令：`.venv\Scripts\python.exe -m pip install -e ".[dev]"`。
- 运行命令：`procedure-ci check --base-openapi PATH --head-openapi PATH --arazzo PATH [--format json|markdown]`。
- 针对性验证命令：`.venv\Scripts\python.exe -m pytest -q tests/test_procedure_ci.py`。
- 完整验证命令：`.venv\Scripts\python.exe -m pytest -q`（配置固定项目内 `.pytest-tmp`）。

## 当前状态

已完成：

- 二次竞品和标准调研；
- 放弃通用“文档转流程”和自定义流程 IR；
- 确定 Arazzo Impact CI 的产品切口；
- 完成产品范围、架构、数据模型、阶段、验收和停止条件设计；
- 创建独立项目目录和恢复文档。
- 完成 M0 依赖 spike 和隔离 `.venv`；
- 完成 loader、OpenAPI/Arazzo 索引、传递依赖图、差异分析、规则检查、JSON/Markdown 报告和三输入 CLI；
- 完成 Webhook onboarding 夹具与 40 项正负向回归测试；
- 完成 MIT 许可、公开前检查、GitHub 仓库配置和 `main` 首次推送；
- 完成 2026-08-31 第三次专项调研，增加公开 corpus 分层、竞品对照和继续投资门槛。
- 完成 M5a：15 个候选、12 个可还原 parent/head 对、2 个独立维护源，并单独记录
  当前 MVP 可直接回放数为 0。
- 完成 M5b：gold 先以提交 `e535370` 冻结；运行 Redocly、oasdiff、Pachca generator 和
  Procedure CI 代表性基线；记录 Speakeasy registry 为 `blocked_external_auth`。
- 接受决策 0004：停止产品化，不实现新的兼容、adapter、Action 或服务层。

停止依据：

- 已验证 A 类维护者为 0；
- Procedure CI 对 12 个原始样本均未完成分析，无法计算 precision/recall；
- 尚未证明 step-impact 相对现有 validator、generator 自动同步和 oasdiff 的增量审阅价值；
- 当前实现只接受 Arazzo 1.1.x、单 OpenAPI source 和同步 operationId 子集；公开语料大量使用
  1.0.1、多 source 或非标准表达式，但这些缺口不能在需求门槛前自动转为功能任务。
- M5a 保留的 12 个样本全部为 Arazzo 1.0.1 的 B/C 类资产，未提供当前 1.1.x MVP 的
  直接回放样本。

下一步：

- 无计划内开发；维护现有 0.1.0。M5c 外部联系未执行，也不在停止后为凑门槛发送消息。

仓库状态：

- 公开仓库：`https://github.com/CrAyoN-V587/procedure-ci`；本地 `main` 通过 HTTPS `origin`
  跟踪 `origin/main`。上传和验证工作流见 `AGENTS.md` 的“GitHub 上传工作流”。
- 2026-08-31 的 M5b gold、对照基线与停止决策已按普通提交推送到 `main`；推送后再次核对
  仓库为 public、默认分支为 `main`，本地 `HEAD` 与远程 `main` 一致。

## 关键决策

| 决策 | 原因 | 日期 |
| --- | --- | --- |
| 使用 Arazzo 1.1，不定义自有 Procedure IR | Arazzo 已标准化多步 API 调用、输入输出、依赖和成功条件 | 2026-08-29 |
| 核心只做 step-level impact，不做生成、执行或完整验证器 | 相邻能力已有成熟或快速发展的工具，影响映射才是当前缺口 | 2026-08-29 |
| MVP 只支持 OpenAPI 3.1、本地单文档和内部 `$ref` | 控制标准解析复杂度，在 4–6 周内验证核心假设 | 2026-08-29 |
| 不持久化 lockfile/digest | base/head 已提供比较边界，更新 digest 不能证明流程正确 | 2026-08-29 |
| 确定错误才默认阻断 CI | “可能受影响”应进入人工审阅，不应伪装成确定失败 | 2026-08-29 |
| 三输入：base/head OpenAPI + 当前 Arazzo | 工作流是当前审查对象，不把 workflow 版本变化混入 API diff | 2026-08-30 |
| GitHub 仓库采用 public、main 和 HTTPS origin | 与同工作区公开开发者工具保持一致，便于审阅和作品集展示 | 2026-08-30 |
| 生成/策展 Arazzo 只作对照，不按文件数计算用户 | Pachca、Speakeasy 和 API Evangelist 证明语料存在，但维护方式与独立生产采用不同 | 2026-08-31 |
| 用独立维护者和对照回放约束功能扩展 | validator、generator 和 oasdiff 已覆盖相邻能力；未证明增量价值前不做 1.0、多 source、adapter 或 Action | 2026-08-31 |
| M5b fast-fail 后停止产品化 | 0/12 原始样本可运行、0 complete gold、0 A 类维护者；先扩兼容再验证会倒置证据门槛 | 2026-08-31 |

## 验证证据

| 日期 | 验证内容 | 命令或步骤 | 结果 |
| --- | --- | --- | --- |
| 2026-08-29 | 工具链现状 | `python --version`、`py -0p`、`python -m pip --version`、`uv --version`、`git --version` | Python 3.12.7、pip 26.1、Git 2.55.0 可用；Python 3.14 和 uv 不可用 |
| 2026-08-29 | Arazzo 标准定位 | 阅读 OAI Arazzo 1.1.0 官方规范与工具清单 | Arazzo 已覆盖流程表达、Agent 执行、生成、验证和运行；不得自造 IR 或重复相邻工具 |
| 2026-08-29 | 真实重复表面 | 对照 World Monitor 的 OpenAPI 3.1.0 与 `check-country-risk` Skill | Skill 重复记录 operation、auth、parameter、response 和 error 信息，证明 API 与 Agent 流程存在漂移表面；未证明其采用 Arazzo |
| 2026-08-29 | 相邻竞品 | 阅读 Runme、Doc Detective、Drift、oasdiff、arazzo-cli 等 | 未发现成熟工具直接输出 OpenAPI 变化到 Arazzo step 的传递影响；M0 已用夹具复核核心切口 |
| 2026-08-30 | 初始文档落盘检查 | 枚举项目文件并验证相对链接、空文件、日期和 `.git` | 文档和目录结构完整；该检查发生在 Git 初始化前 |
| 2026-08-30 | M0 依赖和实现验证 | `.venv\Scripts\python.exe -m pip check`、`.venv\Scripts\ruff.exe check src tests`、`.venv\Scripts\ruff.exe format --check src tests`、`.venv\Scripts\python.exe -m pytest -q`、代表性 CLI | 依赖无冲突；Ruff 检查和格式检查通过；40 项测试通过；CLI 生成稳定 JSON/Markdown，0/1/2 退出码路径已覆盖 |
| 2026-08-30 | Git 里程碑 | 初始化 `main` 并提交 `242fbf6` | 严格 MVP 的源码、40 项测试、夹具和设计文档形成可追溯基线；远程仓库未配置 |
| 2026-08-30 | 公开前检查和包构建 | 扫描当前候选文件与完整 Git 历史；`python -m build` | 凭据特征、本机绝对路径和不应公开的构建/缓存候选均为 0；sdist 和 wheel 构建成功且包含 MIT 许可证 |
| 2026-08-30 | GitHub 首次上传 | 创建 `CrAyoN-V587/procedure-ci`、配置 topics 和 HTTPS `origin`，对比 `git rev-parse HEAD` 与 `git ls-remote origin refs/heads/main` | 仓库为 public、默认分支为 `main`；本地和远程均指向 `d4f925a`，首次上传完成 |
| 2026-08-31 | 标准和竞品刷新 | Arazzo 1.0.1/1.1.0、OAI tooling、Redocly、libopenapi、Jentic、Speakeasy、oasdiff、PactFlow | 1.1 已发布但仍有语法歧义 Issue；验证/执行/生成/自动同步/diff 均有成熟相邻能力，step-impact 仍未发现直接等价物 |
| 2026-08-31 | 公开语料与历史 | GitHub code search、API Evangelist #205、Pachca/Paygentic/Bank API 文件和提交历史 | 找到真实漂移与大量语料；但语料高度集中于策展或生成流程，不能证明独立用户规模 |
| 2026-08-31 | M5a 语料筛选 | 核对 15 个候选的 commit、路径、Arazzo 版本和资产规模 | 保留 12 个可还原历史对，来自 2 个独立源；均为 B/C 类 1.0.1 资产，当前 MVP 可直接回放数为 0 |
| 2026-08-31 | M5a 文档与回归 | GitHub API 核对、本地 Markdown 链接检查、公开文本扫描、`git diff --check`、`pip check`、Ruff、pytest | 12/12 样本的 parent 和变更路径匹配；12 个 Markdown 本地链接缺失 0；凭据/个人绝对路径匹配 0；依赖、Ruff 和格式检查通过；40 项 pytest 通过 |
| 2026-08-31 | M5b 对照与停止评审 | gold 独立提交；Redocly 2.49.0、oasdiff 1.30.0、上游 generator、原始 CLI 与版本标记探针 | 原始覆盖 0/12；oasdiff 能发现 API 变化但不映射 step；带自动重建标记的 PAY-05 历史 head 仍保留 stale operation，Registry run 未执行；正式指标不可计算，决策停止产品化 |

## 暂停检查点

- 当前分支：`main`，跟踪 `origin/main`；远程为
  `https://github.com/CrAyoN-V587/procedure-ci.git`。
- 最近功能里程碑：`242fbf6`（严格 MVP）；最近研究冻结点：`e535370`（M5b gold）。
- 不能丢失的本地数据：`PROJECT.md`、`docs/RESEARCH.md`、`docs/DESIGN.md`、
  `docs/M5-CORPUS.md`、`docs/M5-GOLD.md`、`docs/M5-BASELINES.md` 和决策记录。
- 未验证假设：目标用户愿意维护 Arazzo，并认为 step-level 影响报告比通用 OpenAPI diff
  更有价值；该假设不再作为继续投资依据。
- 恢复时第一步：阅读 `PROJECT.md`、`docs/M5-BASELINES.md`、`docs/DESIGN.md` 和决策 0004；
  默认只维护 0.1.0，不恢复已停止的功能路线。

## 已知限制和后续

- Arazzo 1.1 于 2026-05 发布，生态增长快但公开资产高度集中；文件数不等于独立采用。
- 由于没有 2 个独立 A 类维护者，项目已按研究/作品集工具收尾。
- validator + generator + oasdiff 的层间仍有缝隙，但尚未证明本项目能提供增量用户决策。
- 不为真实样本先实现完整 resolver、runner 或 condition evaluator，也不扩展标准范围。
- 只有新的合格 A 类证据重新通过 G1 后，才单独设计 Arazzo 1.0、多 source、oasdiff adapter 或 GitHub Action；
  Skill renderer、Dashboard、服务端和真实 API 执行不在当前路线。
