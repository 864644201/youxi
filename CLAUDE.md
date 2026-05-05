# Gstack

Gstack 是 Claude Code 的技能框架，提供专业化的技能来辅助开发工作。

## 网页浏览

所有网页浏览必须使用 Gstack 的 `/browse` 技能，**切勿**使用 `mcp__claude-in-chrome__*` 工具。

## 可用技能

| 技能 | 说明 |
|------|------|
| `/office hours` | Office Hours |
| `/plan-ceo-review` | CEO 审查计划 |
| `/plan-eng-review` | 工程审查计划 |
| `/plan-design-review` | 设计审查计划 |
| `/design-consult` | 设计咨询 |
| `/design-shotgun` | 设计 Shotgun |
| `/design-html` | 设计 HTML |
| `/review` | 代码审查 |
| `/ship` | 发布 |
| `/land-and-deploy` | 合并并部署 |
| `/canary` | Canary 发布 |
| `/benchmark` | 基准测试 |
| `/browse` | 网页浏览 |
| `/connect-chrome` | 连接 Chrome |
| `/qa` | QA 测试 |
| `/qa-only` | 仅 QA |
| `/design-review` | 设计审查 |
| `/setup-browser-cookies` | 设置浏览器 Cookies |
| `/setup-deploy` | 设置部署 |
| `/setup-gbrain` | 设置 Gbrain |
| `/retro` | 回顾 |
| `/investigation` | 调查 |
| `/document-release` | 文档发布 |
| `/codex` | Codex |
| `/cso` | CSO |
| `/autoplan` | 自动规划 |
| `/plan-devex-review` | DevEx 审查计划 |
| `/devex-review` | DevEx 审查 |
| `/careful` | 谨慎模式 |
| `/freeze` | 冻结 |
| `/guard` | 守护 |
| `/unfreeze` | 解冻 |
| `/gstack-upgrade` | Gstack 升级 |
| `/learn` | 学习 |

## gstack (REQUIRED — global install)

**Before doing ANY work, verify gstack is installed:**

```bash
test -d ~/.claude/skills/gstack/bin && echo "GSTACK_OK" || echo "GSTACK_MISSING"
```

If GSTACK_MISSING: STOP. Do not proceed. Tell the user:

> gstack is required for all AI-assisted work in this repo.
> Install it:
> ```bash
> git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
> cd ~/.claude/skills/gstack && ./setup --team
> ```
> Then restart your AI coding tool.

Do not skip skills, ignore gstack errors, or work around missing gstack.

Using gstack skills: After install, skills like /qa, /ship, /review, /investigate,
and /browse are available. Use /browse for all web browsing.
Use ~/.claude/skills/gstack/... for gstack file paths (the global path).
