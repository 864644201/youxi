# 🃏 牛牛 - 在线纸牌游戏

基于 Python 的局域网多人牛牛纸牌游戏，浏览器直接打开，无需安装客户端，支持 2-20 人同时在线对战。

## 功能特性

- **局域网多人对战** — 同一 WiFi 下所有人可一起玩
- **浏览器游戏** — 无需安装任何软件，打开浏览器即可
- **2-20 人支持** — 灵活的人数配置
- **实时同步** — WebSocket 实时通信，操作即时反馈
- **完整牌型** — 支持五小牛、炸弹牛、五花牛、牛牛等全部牌型
- **回合制** — 支持多轮连续游戏，房主控制节奏
- **三种下注模式** — 经典、加注、锦标赛，创建房间时选择
- **虚拟筹码系统** — 每人有独立筹码，赢家通吃奖池
- **房间聊天** — 房间内实时文字聊天
- **自定义规则** — 房主可设置初始筹码和底注

## 快速开始

### 环境要求

- Python 3.10+
- 同一局域网（WiFi）

### 安装与启动

```bash
# 1. 克隆仓库
git clone https://github.com/864644201/111.git
cd 111

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务器
python server.py
```

启动后终端会显示：

```
========================================
  牛牛游戏服务器已启动!
  本机访问: http://localhost:8000
  局域网访问: http://192.168.1.100:8000
  把上面的地址发给朋友!
========================================
```

### 加入游戏

1. **房主** — 打开本机地址 `http://localhost:8000`，输入昵称，选择游戏模式（经典/加注/锦标赛），设置初始筹码和底注，点击「创建房间」
2. **其他玩家** — 浏览器打开局域网地址（如 `http://192.168.1.100:8000`），输入昵称和房间号，点击「加入房间」
3. **房主点击**「开始游戏」
4. **经典/锦标赛模式**：每人查看自己的牌，点击「亮牌」
5. **加注模式**：看牌后选择跟注、加注或弃牌，再亮牌
6. 全部亮牌后自动排名，赢家获得奖池筹码，房主可点击「下一轮」

## 游戏规则

### 基本规则

- 使用一副标准扑克牌（52 张，不含大小王）
- 每人发 5 张牌
- 从 5 张牌中选 3 张，使其点数之和为 10 的倍数（即"有牛"）
- 剩余 2 张牌的点数之和模 10 即为"牛数"

### 牌面点数

| 牌面 | A | 2-9 | 10 | J | Q | K |
|------|---|-----|----|----|----|----|
| 点数 | 1 | 牌面值 | 10 | 10 | 10 | 10 |

### 牌型大小（从大到小）

| 牌型 | 说明 | 示例 |
|------|------|------|
| 五小牛 | 5 张牌点数都 ≤ 5，且总点数 ≤ 10 | A♠ A♥ A♦ 2♣ 2♥ |
| 炸弹牛 | 4 张牌点数相同 | 7♠ 7♥ 7♦ 7♣ K♠ |
| 五花牛 | 5 张牌都是 J、Q、K | J♥ Q♠ K♦ J♣ Q♥ |
| 牛牛 | 3 张之和为 10 的倍数，剩下 2 张之和也是 10 的倍数 | 10♥ 5♠ 5♦ J♣ Q♥ |
| 牛九 ~ 牛一 | 3 张之和为 10 的倍数，剩下 2 张之和模 10 = 牛数 | 3♠ 7♥ 10♦ 4♣ 5♥ → 牛九 |
| 无牛 | 无法选出 3 张牌之和为 10 的倍数 | A♥ 2♠ 4♦ 6♣ 8♥ |

### 同牌型比较

- 牌型相同时，比较最大单张牌的大小
- 点数相同则比较花色：♠ > ♥ > ♦ >♣

## 下注模式

创建房间时可选择三种下注模式：

### 经典模式

最简单的玩法，适合快速开局。

- 每轮自动扣除底注
- 亮牌后最大牌型赢走全部奖池
- 无需额外操作，纯粹比运气

### 加注模式

类似德州扑克的博弈玩法，增加策略深度。

- 发牌后进入下注阶段
- 每人可选择：**看牌**（不下注）、**跟注**（跟上当前最高下注）、**加注**（提高下注金额）、**弃牌**（放弃本轮）
- 所有人跟注后进入亮牌阶段
- 未弃牌玩家中最大牌型赢走奖池

### 锦标赛

淘汰赛模式，适合多轮竞技。

- 每轮扣除盲注（底注）
- 筹码归零即淘汰
- 最后剩下的一名玩家获胜
- 策略：合理分配筹码，在关键时刻加注

## 项目结构

```
111/
├── game.py           # 游戏核心逻辑（牌组、牌型评估、房间管理）
├── server.py         # FastAPI WebSocket 服务器
├── static/
│   └── index.html    # 前端界面（HTML/CSS/JS 一体化）
├── requirements.txt  # Python 依赖
├── CLAUDE.md         # Gstack 配置
└── README.md         # 本说明文件
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| 实时通信 | WebSocket |
| 服务器 | Uvicorn |
| 前端 | HTML + CSS + JavaScript（原生，无框架） |
| 游戏逻辑 | Python 纯算法 |

## 常见问题

### 朋友连不上？

- 确认所有人连的是同一个 WiFi
- 检查防火墙是否放行了 8000 端口
- 用启动时显示的局域网地址（不是 localhost）

### Windows 防火墙放行

首次运行时 Windows 会弹出防火墙提示，选择「允许访问」即可。如果没有弹出：

```powershell
# PowerShell（管理员）添加防火墙规则
netsh advfirewall firewall add rule name="牛牛游戏" dir=in action=allow protocol=TCP localport=8000
```

### 想用其他端口？

编辑 `server.py` 最后一行，修改 `port=8000` 为其他端口号。

## 开发

```bash
# 安装依赖
pip install fastapi uvicorn websockets

# 启动开发模式（自动重载）
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

## AI 编程技能

本项目集成了 **65 个 AI 编程技能**，分为两大框架：

### Superpowers-zh（20 个技能）

中文增强版 AI 编程工作流技能。

| 技能 | 说明 |
|------|------|
| `/brainstorming` | 在实现前探索用户意图、需求和设计 |
| `/test-driven-development` | 先写测试再写实现（TDD） |
| `/systematic-debugging` | 系统化调试，先调查根因再修复 |
| `/writing-plans` | 编写多步骤实现计划 |
| `/executing-plans` | 按计划执行，设置审查检查点 |
| `/verification-before-completion` | 完成前运行验证命令，用证据证明成功 |
| `/requesting-code-review` | 完成后请求代码审查 |
| `/receiving-code-review` | 处理代码审查反馈 |
| `/chinese-code-review` | 中文代码审查规范 |
| `/chinese-commit-conventions` | 中文 Git 提交规范 |
| `/chinese-documentation` | 中文技术文档写作规范 |
| `/chinese-git-workflow` | 国内 Git 平台工作流（Gitee、Coding 等） |
| `/finishing-a-development-branch` | 开发分支收尾（合并、PR、清理） |
| `/subagent-driven-development` | 使用子代理并行执行计划 |
| `/dispatching-parallel-agents` | 并行调度多个独立任务 |
| `/using-git-worktrees` | 隔离开发环境 |
| `/mcp-builder` | 构建 MCP 服务器 |
| `/workflow-runner` | 运行 YAML 多角色协作工作流 |
| `/writing-skills` | 创建和验证 AI 技能 |
| `/using-superpowers` | 如何查找和使用技能 |

### Gstack（45 个技能）

专业软件工程工作流技能框架。

#### 规划审查

| 技能 | 说明 |
|------|------|
| `/gstack-office-hours` | YC Office Hours — 产品想法验证和头脑风暴 |
| `/gstack-plan-ceo-review` | CEO 视角审查，找到真正的 10 星产品 |
| `/gstack-plan-eng-review` | 锁定架构、数据流、边界情况和测试 |
| `/gstack-plan-design-review` | 设计维度评分（0-10），解释 10 分是什么样 |
| `/gstack-plan-devex-review` | 开发者体验审查（TTHW、魔法时刻、摩擦点） |
| `/gstack-plan-tune` | 自动调整问题敏感度 |
| `/gstack-autoplan` | 一键运行 CEO → 设计 → 工程 → DX 全套审查 |
| `/gstack-design-consultation` | 从零构建完整设计系统 |

#### 实现与审查

| 技能 | 说明 |
|------|------|
| `/gstack-review` | 合并前 PR 审查，找 CI 会漏掉的 bug |
| `/gstack-codex` | 用 OpenAI Codex 获取第二意见 |
| `/gstack-investigate` | 系统化根因调试，先调查再修复 |
| `/gstack-design-review` | 真站视觉审计 + 修复循环 |
| `/gstack-design-shotgun` | 生成多个设计变体，对比迭代 |
| `/gstack-design-html` | 生成高质量 HTML/CSS |
| `/gstack-devex-review` | 真实开发者体验审计 |
| `/gstack-qa` | 打开真实浏览器，找 bug，修，再验证 |
| `/gstack-qa-only` | 只报告 bug，不改代码 |
| `/gstack-scrape` | 网页数据抓取 |
| `/gstack-skillify` | 将成功的抓取流程固化为永久技能 |

#### 发布与部署

| 技能 | 说明 |
|------|------|
| `/gstack-ship` | 跑测试、审查、推送、开 PR |
| `/gstack-land-and-deploy` | 合并 PR、等 CI、部署、验证生产环境 |
| `/gstack-canary` | 部署后监控循环 |
| `/gstack-landing-report` | 发布队列只读面板 |
| `/gstack-document-release` | 更新文档匹配已发布内容 |
| `/gstack-setup-deploy` | 一次性部署配置检测 |
| `/gstack-upgrade` | 更新 gstack 到最新版本 |

#### 运维与记忆

| 技能 | 说明 |
|------|------|
| `/gstack-context-save` | 保存当前工作状态（git、决策、剩余工作） |
| `/gstack-context-restore` | 从保存的状态恢复，跨会话 |
| `/gstack-learn` | 管理跨会话学习内容 |
| `/gstack-retro` | 每周回顾，含个人明细和发布连胜 |
| `/gstack-health` | 代码质量面板（类型检查、lint、测试、死代码） |
| `/gstack-benchmark` | 性能回归检测 |
| `/gstack-benchmark-models` | 跨模型基准测试（Claude/GPT/Gemini 对比） |
| `/gstack-cso` | OWASP Top 10 + STRIDE 安全审计 |
| `/gstack-setup-gbrain` | 设置跨机器会话记忆同步 |
| `/gstack-sync-gbrain` | 保持 gbrain 与仓库同步 |

#### 浏览器与代理

| 技能 | 说明 |
|------|------|
| `/gstack-browse` | 无头浏览器操作（导航、截图、交互） |
| `/gstack-open-gstack-browser` | 启动可视化 GStack Browser |
| `/gstack-setup-browser-cookies` | 导入浏览器 Cookie 用于认证测试 |
| `/gstack-pair-agent` | 配对远程 AI 代理 |

#### 安全与范围控制

| 技能 | 说明 |
|------|------|
| `/gstack-careful` | 销毁性命令前警告（rm -rf、DROP TABLE 等） |
| `/gstack-freeze` | 锁定只允许编辑一个目录 |
| `/gstack-guard` | 同时激活 careful + freeze |
| `/gstack-unfreeze` | 解除编辑限制 |
| `/gstack-make-pdf` | 将 Markdown 转为出版级 PDF |

## License

MIT
