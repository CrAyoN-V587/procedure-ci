# 决策 0002：以当前 Arazzo 作为唯一工作流输入

- 状态：MVP 已接受
- 日期：2026-08-30

## 背景

严格 MVP 的问题是判断“当前仍在维护的 workflow 哪些步骤会被这次 OpenAPI PR 影响”。
工作流本身不是 API 版本差异的对象；要求 base/head 两份 Arazzo 会引入无关的 merge、
版本选择和 workflow 变化语义，也扩大了首版输入面。

## 决策

CLI 固定为三个输入：

```text
--base-openapi PATH
--head-openapi PATH
--arazzo PATH
```

分析以当前 Arazzo 建立 step → OpenAPI entity 依赖图，再将 base/head OpenAPI 的实体变化
映射到这些步骤。Arazzo 仅接受 1.1.x，且必须恰有一项 `type: openapi` 的
`sourceDescriptions`；步骤既可使用 plain `operationId`，也可使用官方
`$sourceDescriptions.<name>.<operationId>` 表达式。Arazzo 自身仍进行内部结构、输出引用、
依赖环和 operationId 绑定检查。
唯一 source description 的 `name` 必须匹配 `[A-Za-z0-9_-]+`，`url` 必须是非空字符串；MVP
只把它用于解析官方 operation expression，不读取或抓取该 URL。

## 结果

- PR 只需携带当前 workflow 文件，输出直接对应维护者要复查的版本；
- OpenAPI 变化和 workflow 变化的责任边界更清晰；
- 不能判断历史 workflow 是否已经被删除或迁移；这留到未来的 workflow diff 能力；
- 当前 Arazzo 的动态 payload 不做猜测，报告 `unknown`，字面量 payload 才做 JSON Schema 校验。
- base/head OpenAPI 分别建图后取可达依赖并集；producer response/output 变化沿
  `$steps.<stepId>.outputs.<name>` 传播到 consumer，并保留删除实体的旧路径。

## 重新评估条件

- 试点显示 workflow 版本变化本身是主要误报来源；
- 用户需要检查“workflow 是否随 API 变更同步提交”；
- Arazzo runner 或版本化工作流工具提供了稳定的 base/head 语义。
