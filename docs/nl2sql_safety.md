# NL2SQL 安全策略（阶段五）

## 执行边界

1. **仅 SELECT**：拒绝 INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/CREATE/REPLACE/GRANT/REVOKE
2. **单语句**：禁止 `;` 多语句与注释注入 `--`、`/*`
3. **表白名单**：仅 `docs/mall_schema_for_llm.json` 中 `allowed_tables` 列出的表
4. **强制 LIMIT**：若无 LIMIT 自动追加 `LIMIT 500`；LIMIT 值上限 500
5. **超时**：单次查询 5 秒
6. **无子查询写操作**：禁止 INTO OUTFILE、LOAD DATA、FOR UPDATE

## 模型调用

- 使用火山引擎豆包（OpenAI 兼容 Chat Completions）
- API Key 仅存服务端 `.env`，不下发前端
- Prompt 注入 schema 片段 + 指标字典摘要 + few-shot，要求 JSON 输出

## 路由优先级

1. **模板路由**：命中大屏 8 模块同类问题时，直接调用 `ops_service`，保证与大屏口径 100% 一致
2. **NL2SQL**：未命中模板时，由豆包生成 SQL，经 Guard 后只读执行

## 降级

- LLM 不可用：模板路由仍可用；NL2SQL 返回友好错误与示例问题
- SQL 校验失败：不返回原始 SQL 给用户，记录服务端日志

## 验收

- 内置 10 题题库，目标命中 ≥ 7/10
- 助手展示 `route`（template / nl2sql）便于调试
