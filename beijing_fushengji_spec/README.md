# 北京浮生记 v1.2.2 — Gherkin 规格（前后端迁移契约）

本目录是用 **Gherkin（中文 zh-CN 方言）** 精确描述《北京浮生记 v1.2.2》游戏行为与数值设计的规范文档。它是把原版单进程 C++/MFC 桌面游戏迁移为**前后端（Web）架构**的**实现契约与验收基准**。

> 目标：**在不阅读任何 C++ 源码的前提下，仅依据本规范即可完整重实现游戏**，并能与前后端实现逐项对账。

## 文档组织

```
beijing_fushengji_spec/
├── README.md                    ← 本文档：索引、边界总述、标签、缺陷策略、校验命令
├── _数值总表.md                 ← 附录：全部数值/事件表汇总（信息性副本）
├── features/01_…  … 13_….feature   ← Gherkin 行为规范（权威）
├── tools/check_spec.js          ← 结构完整性校验脚本
└── .gherkin-lint.json           ← 可选 lint 配置
```

### Feature 索引

| # | 文件 | 一句话范围 | 标签 |
|---|---|---|---|
| 01 | 新游戏初始化 | 初始数值、设置默认值、重开复位 | `@backend @state` |
| 02 | 地图与移动 | 双地图切换、20 地点、移动=1天/原地不动 | `@frontend @state` |
| 03 | 时间与回合流程 | 40 天主循环固定顺序、天数递减、第0天清仓 | `@backend @state` |
| 04 | 市场与价格 | 8 种商品价格公式、leaveout 剔除、最后2天全 8 | `@backend @rule-engine` |
| 05 | 买卖交易 | 买入上限、加权均价、卖出价、名声扣减、非在售禁卖 | `@backend @rule-engine` |
| 06 | 经济与利息 | 债务+10%/日、存款+1%/日、截断语义 | `@backend @rule-engine` |
| 07 | 商业事件 | 18 条事件全表、`X%freq==0` 触发、倍/除/赠、末条+2500 | `@backend @rule-engine @stochastic` |
| 08 | 健康事件 | 12 条事件全表、每日至多1条、强制住院、死亡 | `@backend @rule-engine @stochastic` |
| 09 | 金钱损失与黑客事件 | 7 条偷钱全表、现金/存款分档、黑客三分支 | `@backend @rule-engine @stochastic` |
| 10 | 服务·金融与医疗 | 银行存取、邮局还款/村长评价、医院 3500/点 | `@backend @state` |
| 11 | 服务·生活与娱乐 | 房屋中介、网吧、老板遮挡 | `@backend @state @frontend` |
| 12 | 得分与排行 | score、破产、前十名、score.txt、称号、作弊提示 | `@backend @persistence @state` |
| 13 | 前后端边界契约 | 状态所有权、命令清单、RNG 契约、消息队列 | `@boundary` |

阅读建议：先读 **13**（边界与重放契约）了解前后端如何划分，再逐 01→12 看规则。

---

## 前后端边界总述（详见 13）

- **后端（Backend）**：拥有**全部数值状态**（cash/debt/bank/health/fame/coat/total/持仓/价格/timeLeft/currentLoc/city/visitWangba/hackActs/closeSound）与**全部规则**（每日主循环、价格、事件、利息、买卖、得分）。后端暴露**命令接口**，每个命令返回完整状态快照 + 待显示消息列表。
- **前端（Frontend）**：只负责**渲染与交互**——地图/按钮文案、弹窗/日记/新闻渲染、音效、输入捕获、老板遮挡、高分姓名输入。前端不持有任何持久游戏状态。
- **随机性**：后端把所有随机数收敛到单一可注入函数 `random(upper)`；测试钩子 `nextRandom(v)` 使场景确定化、每日可逐位重放（见 13 的"随机数消耗顺序"）。

### 命令清单（每命令→后端行为）

`startGame · toggleMap · moveTo(loc) · buy(goodsId,count) · sell(goodsId,count) · bankDeposit(n) · bankWithdraw(n) · repayDebt(n) · buyHealth(points) · rentHouse() · visitNetcafe() · openBossShield() · setup(hack,sound) · submitScore(name)`

---

## 标签词汇表（全库强制一致）

| 标签 | 含义 | 使用规则 |
|---|---|---|
| `@backend` | 规则/状态，必须在后端实现 | 每个 feature 至少一个 `@backend` 或 `@frontend` |
| `@frontend` | 渲染/交互，在前端实现 | 同上 |
| `@state` | 断言状态迁移/初始状态 | 有状态断言的场景加 |
| `@rule-engine` | 纯计算、无 I/O | 规则类 feature 加 |
| `@stochastic` | 涉及 RNG；场景经注入抽取值保证确定 | 随机事件文件加 |
| `@persistence` | 读写 `score.txt` | 排行文件加 |
| `@boundary` | 前后端契约场景 | 13 的每个场景加 |
| `@bug-faithful` | 复现原版缺陷 | 缺陷场景加 |
| `@verified` | 数值已二次核对源码 | 可选元标签（默认加于已核对场景） |

---

## 写作约定

1. **语言**：`# language: zh-CN`；关键字用 `功能/背景/场景/场景大纲/例子/假如/当/那么/而且/但是`；文件 UTF-8。
2. **文案原样**：所有弹窗、事件消息、地点名、商品名**逐字保留**（GBK→UTF-8 转码后不润色）。
3. **可追溯**：Feature 顶部 `# 来源: <文件>`；每个场景下 `# 来源: <文件>:<行>`（用注释，兼容性好）。
4. **确定性随机**：随机规则写成抽签值 `X` 的显式纯函数（`X % freq == 0`），`X` 是场景输入。
5. **数值权威**：Feature 内 Examples 表是权威数据；`_数值总表.md` 是速查副本，用 `tools/check_spec.js` 对齐。

---

## 缺陷处理策略

- **A 类（可复现、不崩溃、可观察）**：按原样写成契约场景 + `@bug-faithful`，场景注释给"原版行为 vs 建议"。例：`GetFameStr` 死分支（fame 10–19 实际落到「江湖唾弃」）。
- **B 类（潜在崩溃/越界）**：规范写"意图语义"，另用 `@bug-faithful` 场景记录原版缺陷并**建议修复**。例：商业事件 `exist` 标志未重置导致赠送可能错误并入。
- **C 类（环境/平台）**：仅此处"已知环境问题"提及，不入规范。已知：XP 下 Ticker 崩溃、`sound.cfg`/`Curvefit`/`DualListDemoDlg` 为死代码等（详见原工程结构报告）。

---

## 校验命令

```bash
# 1) 语法解析（必做）：官方解析器把全部 .feature 编译成 AST，报错即失败
npx @cucumber/gherkin --language zh-CN features/*.feature
# Python 备选：
#   pip install gherkin-official
#   python -c "import glob; from gherkin.parser import Parser; [Parser().parse(open(f).read()) for f in glob.glob('features/*.feature')]; print('OK')"

# 2) 结构完整性校验（必做）：语言头 / 来源注释 / 事件表行数 / 标签词汇 / 与数值总表一致
node tools/check_spec.js
```

**完成标准**：13 个 feature + `_数值总表.md` 全部通过官方解析器；每个场景带 `# 来源:`；三张事件表行数恰为 18/12/7；所有标签在词汇表内；不看 C++ 即可完整重实现并前后端对账。

## 原始工程（只读参考）

`/home/ubuntu/c/rl-beijing/beijing_fushengji_original/`（Win32 MFC；逻辑在 `SelectionDlg.cpp` 2360 行；唯一持久化为 `score.txt`）。
