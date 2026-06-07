# EcomAI Intelligence Platform — Agent 指南

## 项目概览

电商智脑平台：FastAPI 后端 + Vue 3 多端（用户端 / 管理端 / 运营 BI）。本地开发见 [README-local.md](README-local.md)。

## Cursor 持久规则

本项目继承全局规则（与 `~/.cursor/.cursor.md` 一致）：

1. **Conversation 归档**：每轮对话结束前更新 `.cursor/conversations/<session_id>/Conversation.md`。
2. **Skills 三层加载**：第一层 `SKILLS_INDEX.md` → 第二层 `INTRO.md`（≤2 个）→ 第三层 `SKILL.md`（仅 1 个）；可用各工具 skill，但禁止跳层与批量加载。
3. **新增 Skill 后**：执行 `python C:\Users\23628\.cursor\scripts\skills-maintain.py` 刷新第一层索引与各 INTRO。

项目规则文件：`.cursor/rules/`  
项目 Hooks：`.cursor/hooks.json`（指向用户级 hook 脚本）

## 工程约定

- 密钥放在 `ecom-api/.env`，不要提交。
- 改完相关模块后运行对应验证（前端 `npm run build`，后端按 README-local）。
- 大改动前先 Plan，确认后再实现。
