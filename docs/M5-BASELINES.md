# Procedure CI M5b 对照基线与停止评审

- 执行日期：2026-08-31
- gold 冻结提交：`e535370`
- 对照样本：PCH-01（B 类）与 PAY-05（C 类）
- 结论：M5b fast-fail 完成；停止产品化，保留 0.1.0 为研究/作品集工具

## 摘要

对照实验与历史 head 资产共同显示一个技术缝隙：oasdiff 能发现 PAY-05 的 operation 删除，
Redocly 默认 lint 认为 Arazzo 结构有效，而被分类为自动重建资产的历史 head Arazzo 仍保留
对已删除 operation 的引用。本轮 Speakeasy Registry run 因外部认证未执行，不能据此声称
实际重建已验证；可确认的是 `OpenAPI diff → workflow step` 的连接问题真实存在。

但本项目没有证明自己能为真实用户填补该缝隙：12 个样本全部是 B/C 类 Arazzo 1.0.1
生成资产，0 个 A 类维护者；Procedure CI 对原始样本的可运行覆盖率为 0/12；代表性 gold
为 0 个 complete、1 个 partial、1 个 unresolvable。precision、recall 与增量决策价值因此都
不可计算。按预先写入的停止条件，本项目不再投入 Arazzo 1.0、OpenAPI 3.0、source-name
兼容、oasdiff adapter 或 GitHub Action。

## 工具与执行边界

| 基线 | 固定版本/来源 | 本轮用途 |
| --- | --- | --- |
| Redocly CLI | `2.49.0` | 默认 recommended 配置下 lint head Arazzo |
| oasdiff | `1.30.0` Windows amd64 官方 release asset | summary 与 breaking-change 对照；关闭 external refs |
| Pachca generator | 仓库声明的 `bun@1.3.4`、`check:generated --force` | 重建结构化源的生成出口 |
| Paygentic generator | `.speakeasy/workflow.yaml` 声明 `speakeasyVersion: 1.761.4` | 只读检查；registry source 需要外部认证，不发起生成 |
| Procedure CI | 当前仓库 0.1.0 | 原始输入与只改 Arazzo 版本标记的合成探针 |

所有第三方 checkout、工具与输出位于仓库外的临时目录；本仓库不复制第三方原始数据、
生成机器路径或完整工具输出。合成探针只改副本的 `arazzo: 1.0.1` 为 `1.1.0`，不计为样本。

## 对照结果

| 样本 / 基线 | 结果 | 可解释边界 |
| --- | --- | --- |
| PCH-01 / generator | TypeSpec、CLI 与 277 个文档资产完成重建；Arazzo 文件 `git diff --exit-code` 为 0 | 总门槛在 Next.js standalone 创建 symlink 时因 Windows `EPERM` 退出 1，故只证明 Arazzo 生成出口一致，不能声称完整 `check:generated` 通过 |
| PAY-05 / generator | `blocked_external_auth`；未调用 Speakeasy Registry | head Arazzo 相对 base 只有 2 加/2 删，均为 `paymentTerm` 值变化；被删除的 `getFeePrice` 仍有 1 个 step 引用 |
| PCH-01 / Redocly | 输出“Arazzo 有效”，随后 Node/libuv assertion，进程退出 `-1073740791` | 结构 lint 结果可观察，但进程级基线不可记为 clean pass |
| PAY-05 / Redocly | Arazzo 有效，退出 0 | 默认 lint 未报告 head OpenAPI 中已不存在的 `getFeePrice` 引用 |
| PCH-01 / oasdiff | 74 endpoint、47 path、27 schema modified；17 条 breaking 信号（14 error、3 warning） | 提供 API 级变化和位置，不映射 workflow/step |
| PAY-05 / oasdiff | 1 endpoint deleted、10 modified；1 path deleted、6 modified；1 schema deleted、5 modified；3 条 error | 明确报告 API path 删除，以及 `createPrice`/`updatePrice` 的 request enum 收窄，不映射 stale step |
| PCH-01 / Procedure CI 原始输入 | 退出 2：OpenAPI 3.0.0 不受支持 | `not_analyzed`，不是命中、漏报或 `unknown` |
| PCH-01 / 版本标记探针 | 退出 2：仍先被 OpenAPI 3.0.0 阻塞 | 只改 Arazzo 版本不能形成有效回放 |
| PAY-05 / Procedure CI 原始输入 | 退出 2：Arazzo 1.0.1 不受支持 | `not_analyzed` |
| PAY-05 / 版本标记探针 | 退出 2：source description 不满足单一合法 OpenAPI source 约束 | 证明第二阻塞存在；探针不进入任何覆盖率或指标 |

## 冻结后的作者动作观察

这些观察在 [gold set](M5-GOLD.md) 冻结后才读取，只用于解释现有维护流程，不反向修改标签：

- PCH-01 的 Arazzo 历史差异是 5 行新增；但该样本在冻结前已被误看，仍保持
  `unresolvable`，不进入指标。
- PAY-05 的 Arazzo 历史差异是 2 行新增、2 行删除，只更新 `createPrice` 的请求与预期响应
  示例；这个带自动重建标记的历史 head 资产中，OpenAPI 已无 `getFeePrice`，Arazzo 仍保留
  同名 workflow/step。本轮没有验证 Registry 实际重建。
- 因此 Redocly 的“结构有效”、历史资产的“自动重建标记”和 oasdiff 的“operation 删除”是三个
  不同层级的信号。维护者仍要人工把删除信号连接到 stale step；本轮未证明实际 Registry 重建
  结果，也未证明 Procedure CI 能在
  可接受兼容成本下自动完成连接。

## 指标判定

| 指标 | 结果 | 判定 |
| --- | ---: | --- |
| 可还原历史样本 | 12 | 达到 M5a 数量门槛 |
| 当前 CLI 原始样本可运行覆盖 | 0/12 | fast-fail |
| complete gold | 0 | 不满足至少 10 个完整样本 |
| A 类维护者 | 0 | 不满足 G1 |
| precision / recall | 不可计算 | 禁止报告数值 |
| 相邻工具之外的 Procedure CI 决策增量 | 0 条已证明 | 不满足 G1 |
| 报告改变真实审阅决定 | 0 次 | 不满足 G1 |

这里的“0 条已证明”不等于技术缝隙不存在，而是没有可运行、独立且面向 A 类用户的证据链。
继续扩版本支持才能开始计算指标，会倒置“先验证需求、再扩功能”的顺序。

## 投资决策

**不继续产品化。** 当前最值得保留的是已经完成且有 40 项回归的 0.1.0 严格 MVP、
语料分层方法、gold 污染记录和对照实验，而不是新的兼容层。

允许的后续仅有：

- 修复 0.1.0 已有边界内的确定性 bug；
- 用户或维护者主动提供 A 类、OpenAPI 3.1 + Arazzo 1.1.x 样本时，按同一冻结协议只读回放；
- 新证据同时满足 G1 后，另立项目决策，不从本轮默认延伸。

M5c 的外部维护者联系未执行：它会产生外部消息，而且当前已有“公开规模主要来自 B/C/D
生成资产”和“0/12 可运行覆盖”两个停止信号。停止后不再为凑门槛扩大外部协调。

## 角色与使用情景审查

| 角色 | 真实触发场景 | 当前可用资产 | 建议动作 | 禁止误读 |
| --- | --- | --- | --- | --- |
| API/DevEx 维护者 | OpenAPI PR 删除或修改 operation，需要定位多步流程 | oasdiff API 信号 + Procedure CI 0.1.0（仅支持既定 3.1/1.1 子集） | 在支持子集内试用；其他情况先用 diff + 明确的 workflow 引用检查 | 退出 2 不是安全或影响结论 |
| B 类生成器维护者 | 同一结构化源生成 OpenAPI 与 Arazzo | 上游 generator sync gate | 把生成一致性门槛放在 PR 中；只有同步后仍缺 step 决策才考虑 impact 工具 | 文件数量不是独立用户数量 |
| C 类 SDK contract-test 维护者 | OpenAPI 变化后自动重建 Arazzo tests | 历史 head + 自动重建配置 + validator + oasdiff | 在有 Registry 权限的流水线增加“删除 operation 后 stale test 必须消失”的生成器回归 | 配置声明不等于本轮重建已执行 |
| M5 研究者 | 比较不同层级工具的增量 | corpus、冻结记录、本报告 | 先冻结 gold；污染/部分样本单列；退出 2 记 `not_analyzed` | 不得用合成探针计算指标 |
| 产品投资决策者 | 判断是否继续投入兼容和集成 | 0/12 覆盖、0 complete gold、0 A 类维护者 | 停止产品化，保留研究资产 | 不能因存在技术缝隙就推断有产品需求 |
| 作品集审阅者 | 评估工程判断而非 feature 数量 | 0.1.0 源码、40 项测试、调研与停止决策 | 关注范围纪律、诊断语义和证据诚实性 | 项目“完成”不代表产品市场验证通过 |

## 可复查命令模板

```powershell
npx.cmd --yes @redocly/cli@2.49.0 lint <head-arazzo> --format summary
oasdiff.exe summary <base-openapi> <head-openapi> --format json --allow-external-refs=false
oasdiff.exe breaking <base-openapi> <head-openapi> --format singleline --allow-external-refs=false
.venv\Scripts\python.exe -m procedure_ci check `
  --base-openapi <base-openapi> `
  --head-openapi <head-openapi> `
  --arazzo <head-arazzo> `
  --format json
```

Pachca 的完整命令是其仓库自己的 `bun run check:generated --force`；Paygentic 的 registry
生成需要外部认证，本轮没有执行。完整第三方输出和临时 checkout 不是项目制品。
