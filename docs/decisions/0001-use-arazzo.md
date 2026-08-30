# 决策 0001：使用 Arazzo，不定义自有 Procedure IR

- 状态：M0 与 MVP 已接受
- 日期：2026-08-29

## 背景

最初设想是定义一种 Procedure YAML，把操作手册、Agent Skill 或 API 文档转换成可执行的 CI 检查。进一步调研发现，这个方向同时与文档执行、文档测试、Skill 生成和 API diff 等成熟工具重叠，而且自有格式会把大量时间消耗在规范、解析器、生态适配和迁移上。

OpenAPI Initiative 已发布 Arazzo 1.1，用来描述 API 调用序列、步骤依赖、输入输出和成功条件，并明确覆盖自动化与 AI Agent 等场景。其生态已有编辑器、校验器、生成器、解析器和 runner，但调研时尚未发现成熟工具把 **OpenAPI base/head 变化映射为受影响的 Arazzo 工作流步骤**。

## 决策

Procedure CI 的规范输入采用 Arazzo 1.1。产品核心收敛为：

```text
OpenAPI base/head
        +
Arazzo workflow
        |
        v
transitive dependency graph
        |
        v
affected workflow steps + explainable diagnostics
```

严格 MVP 只支持：

- OpenAPI 3.1；
- Arazzo 1.1 的同步 OpenAPI 子集；
- 一份本地 OpenAPI 和一份本地 Arazzo；
- 内部 `$ref`；
- 通过唯一 `operationId` 定位操作；
- 确定性静态分析和 JSON/Markdown 报告。

项目可以继续使用 “Procedure CI” 作为工作名，但文档必须明确其首个产品形态是 “Arazzo Impact CI”。

## 正面影响

- 复用公开标准，避免创造私有工作流语言；
- 输入语义、校验规则和生态边界更清楚；
- 能把研发集中在真正的缺口：传递依赖和步骤级影响解释；
- 更容易与现有 OpenAPI diff 和 Arazzo runner 组合；
- 失败时仍可沉淀标准夹具和互操作研究。

## 代价与限制

- Arazzo 尚新，真实团队采用率和付费需求没有得到验证；
- 完整规范支持面很大，MVP 必须主动拒绝外部引用、AsyncAPI 和复杂运行时表达式；
- 用户只有 OpenAPI、没有 Arazzo 时，产品不能直接产生价值；
- 若用户只关心接口 breaking changes，现有 OpenAPI diff 工具更合适。

## 被否决的方案

### 自定义 Procedure YAML

否决原因：没有第二个已验证的独特使用场景，不值得承担自有规范和迁移成本。

### Markdown runbook 直接执行

否决原因：已有成熟项目覆盖，且执行 Shell 或真实 API 会扩大安全与可复现范围。

### LLM 判断工作流是否失效

否决原因：CI 阻断结果需要确定性、可重复和可解释；LLM 可在未来用于非阻断说明，但不能成为门禁。

## 重新评估条件

出现以下情况时重新评估本决策：

- Arazzo 规范或生态发生不兼容变化；
- 目标用户普遍使用另一种公开工作流标准；
- 5 支目标团队中少于 2 支维护 Arazzo 或可转换的工作流；
- 成熟上游工具提供等价的步骤级影响分析。

若需求验证失败，项目降级为 `arazzo-impact-lab`，保留标准研究、夹具和解析实验；不恢复自定义 Procedure IR。
