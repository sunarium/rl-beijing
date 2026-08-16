# 北京浮生记 v1.2.2 — API 契约

> **版本**: 1.0.0  
> **状态**: 草案  
> **适用人群**: 前端开发者 / 自动化 Agent 开发者

## 设计原则

本 API 同时服务于 **两种客户端**：

| 客户端 | 目标 | 核心需求 |
|--------|------|----------|
| **前端 (Human Play)** | Web UI 渲染与交互 | 完整状态快照供整体渲染；消息分类型（日记/新闻/确认）供模态/非模态展示 |
| **自动化 Agent** | 程序化自动游玩 | 自描述接口；无歧义的结构化响应；可预测的状态机；无需解析自然语言即可决策 |

**核心设计决策**：

1. **全状态响应** — 每个命令返回完整状态快照，前端和 Agent 无需缓存或 diff
2. **结构化消息** — 消息从不是纯文本 blob；每条消息携带 `type`、`category`、结构化 `data`、可选的 `text` 展示文案
3. **无歧义动作验证** — 错误以标准化的 `ProblemDetail` 格式返回，含 `code`、`params`（用于前端 i18n）和 `message`（用于 Agent 日志）
4. **确定可重放** — RNG 默认由后端管理，但支持 `X-RNG-Seed` 头或显式 `rngSequence` 参数注入，使 Agent 能复现特定场景进行训练/测试

---

## 1. 接口总览

### 1.1 基础 URL

```
http://<host>:<port>/api/v1
```

### 1.2 资源模型

```
/api/v1/
├── games              ← 游戏生命周期（创建、列表、查询）
│   ├── :gameId        ← 单个游戏实例
│   │   ├── state      ← 只读状态快照（不触发副作用）
│   │   └── actions    ← 玩家动作端点
│   └── leaderboard    ← 高分榜
└── docs               ← OpenAPI/Swagger 文档（可选）
```

### 1.3 内容类型

- `Content-Type: application/json`（请求与响应）
- `Accept: application/json`

---

## 2. 游戏生命周期

### 2.1 创建新游戏

```
POST /api/v1/games
```

#### 请求体（可选）

```json
{
  "agentName": "optional-agent-tag",        // Agent 标识，仅用于日志/统计
  "options": {
    "seed": null                             // 可选：确定 RNG 种子（测试/复现用）
  }
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `agentName` | `string` | `null` | 调用方标识，不会影响游戏逻辑 |
| `options.seed` | `int \| null` | `null` | 不为 null 时，启用确定 RNG（用于训练/测试场景复现） |

#### 响应 `201 Created`

```json
{
  "gameId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "createdAt": "2026-08-16T12:00:00Z",
  "state": { /* 见 §3 状态快照 */ },
  "messages": [],
  "gameOver": false
}
```

---

### 2.2 查询游戏状态（只读，无副作用）

```
GET /api/v1/games/:gameId
```

用于 Agent 在决策前检查当前状态，**不消耗回合，不触发任何事件**。  
前端轮询或页面刷新后重建 UI 也使用此端点。

#### 响应 `200 OK`

```json
{
  "gameId": "a1b2c3d4-...",
  "createdAt": "2026-08-16T12:00:00Z",
  "state": { /* 见 §3 */ },
  "gameOver": false
}
```

#### 错误

| 状态码 | 说明 |
|--------|------|
| `404` | 游戏不存在或已过期 |

---

### 2.3 执行玩家动作

```
POST /api/v1/games/:gameId/actions
```

#### 请求体

```json
{
  "action": "moveTo",
  "params": {
    "loc": 3
  }
}
```

#### 可用动作清单

| 动作 | 参数 | 触发日常事件？ | 说明 |
|------|------|:---:|------|
| `startGame` | `{}` | 否 | 重置游戏到初始状态（同 POST /games） |
| `toggleMap` | `{}` | 否 | 切换城市地图（1↔2） |
| `moveTo(loc)` | `{ "loc": 1..10 }` | **是** | 移动到指定地点，触发完整日常序列 |
| `buy` | `{ "goodsId": 0..7, "count": n }` | 否 | 买入商品 |
| `sell` | `{ "goodsId": 0..7, "count": n }` | 否 | 卖出商品 |
| `bankDeposit` | `{ "amount": n }` | 否 | 存款 |
| `bankWithdraw` | `{ "amount": n }` | 否 | 取款 |
| `repayDebt` | `{ "amount": n }` | 否 | 邮局还款 |
| `buyHealth` | `{ "points": n }` | 否 | 医院治疗 |
| `rentHouse` | `{}` | 否 | 房屋中介（扩容量） |
| `visitNetcafe` | `{}` | 否 | 网吧 |
| `openBossShield` | `{}` | 否 | 老板遮挡画面（纯前端，后端只记录状态） |
| `setup` | `{ "hackActs": bool, "closeSound": bool }` | 否 | 游戏设置 |
| `submitScore` | `{ "name": "玩家名" }` | 否 | 提交高分 |

**Agent 特别提示**：只有 `moveTo` 会触发日常事件序列（价格生成、商业/健康/偷钱/黑客事件），其他动作都是瞬时操作且不消耗天数。Agent 循环应设计为 `moveTo` → 解析 state + messages → 决策（买卖/存取等）→ 再 `moveTo`。

#### 响应 `200 OK`

```json
{
  "gameId": "a1b2c3d4-...",
  "state": { /* 见 §3 */ },
  "messages": [ /* 见 §4 */ ],
  "gameOver": false,
  "action": "moveTo",
  "params": { "loc": 3 }
}
```

#### 游戏结束

当游戏状态满足以下任一条件时，`gameOver` 为 `true`：

| 条件 | 说明 |
|------|------|
| `state.timeLeft ≤ 0` | 天数耗尽，触发结算 |
| `state.health < 0` | 健康死亡 |
| `state.cash + state.bank - state.debt ≤ 0` | 破产（得分 ≤ 0） |

游戏结束后，除 `startGame` 和 `submitScore` 外，所有动作返回 `409 Conflict`。

#### 错误响应

| 状态码 | 场景 | `code` 字段 |
|--------|------|-------------|
| `400` | 参数不合法（如 `loc` 超出 1–10） | `INVALID_PARAM` |
| `400` | 数量超出范围 | `INVALID_COUNT` |
| `404` | 游戏不存在 | `GAME_NOT_FOUND` |
| `409` | 游戏已结束（除 startGame / submitScore） | `GAME_OVER` |
| `409` | 游戏未开始（未发送 startGame 即发 action） | `GAME_NOT_STARTED` |
| `422` | 规则拒绝：现金不足 | `INSUFFICIENT_CASH` |
| `422` | 规则拒绝：仓库已满 | `COAT_FULL` |
| `422` | 规则拒绝：健康过低且剩余天数 > 3（强制住院） | `FORCED_HOSPITAL` |
| `422` | 规则拒绝：商品不在当前地点在售列表中 | `NOT_ON_SALE` |
| `422` | 规则拒绝：网吧已达上限 3 次 | `NETCAFE_MAX` |
| `422` | 规则拒绝：名声/仓库容量已达上限 | `CAP_REACHED` |
| `422` | 规则拒绝：姓名已提交（submitScore 后不可再提交） | `SCORE_ALREADY_SUBMITTED` |

所有错误的响应体格式一致：

```json
{
  "error": {
    "code": "INSUFFICIENT_CASH",
    "message": "现金不足，需要 3500 但仅有 2000",
    "params": {
      "required": 3500,
      "actual": 2000
    }
  }
}
```

- `message`：人类可读（前端直接展示或 Agent 日志记录）
- `params`：结构化参数，前端可用于 i18n 模板填充，Agent 可用于条件判断

---

### 2.4 查询高分榜

```
GET /api/v1/games/leaderboard
```

#### 查询参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | `int` | `10` | 返回条数（原版固定 10 条） |

#### 响应 `200 OK`

```json
{
  "entries": [
    {
      "rank": 1,
      "name": "玩家名",
      "score": 88888,
      "health": 100,
      "title": "德高望重"
    }
  ],
  "total": 10
}
```

---

## 3. 状态快照

每个状态响应包含以下结构。Agent 可据此作决策而无需任何外部上下文。

```json
{
  "cash": 2000,
  "debt": 5000,
  "bank": 0,
  "health": 100,
  "healthMax": 100,
  "fame": 100,
  "fameMin": 0,
  "fameMax": 100,
  "coat": 100,
  "coatMax": 140,
  "total": 0,
  "holdings": [
    { "goodsId": 0, "name": "进口香烟", "count": 0, "avgPrice": 0 },
    { "goodsId": 1, "name": "走私汽车", "count": 0, "avgPrice": 0 },
    /* ... 8 种商品 ... */
  ],
  "prices": [ 234, 0, 12, 0, 7890, 456, 987, 0 ],
  "timeLeft": 40,
  "currentLoc": null,
  "city": 1,
  "cityName": "北京地铁",
  "visitWangba": 0,
  "settings": {
    "hackActs": false,
    "closeSound": false
  },
  "score": -3000,
  "gameOver": false
}
```

### 字段说明

| 字段 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `cash` | `int` | ≥ 0 | 当前现金 |
| `debt` | `int` | ≥ 0 | 当前债务 |
| `bank` | `int` | ≥ 0 | 银行存款 |
| `health` | `int` | ±∞ | 健康值；< 0 即死亡 |
| `healthMax` | `int` | 100 | 健康上限 |
| `fame` | `int` | [0, 100] | 名声 |
| `fameMin` / `fameMax` | `int` | — | 名声可达到的边界 |
| `coat` | `int` | [100, 140] | 当前仓库容量 |
| `coatMax` | `int` | 140 | 容量上限 |
| `total` | `int` | [0, coat] | 持仓总数 |
| `holdings` | `array` | 8 元素 | 每种商品的持仓明细（见 §3.1） |
| `prices` | `int[8]` | 见 §3.2 | 当前地点各商品黑市价；**`prices[i] == 0` 表示不在售** |
| `timeLeft` | `int` | [0, 40] | 剩余天数；= 0 结算 |
| `currentLoc` | `int \| null` | 1–10 或 null | 当前地点；游戏未开始为 null |
| `city` | `int` | 1 或 2 | 1=北京地铁, 2=地面 |
| `cityName` | `string` | — | 城市名中文 |
| `visitWangba` | `int` | [0, 3] | 网吧已访问次数 |
| `settings` | `object` | — | 玩家设置 |
| `score` | `int` | ±∞ | 得分 = cash + bank − debt |
| `gameOver` | `bool` | — | 是否已结算/死亡/破产 |

### 3.1 持仓明细

```json
{
  "goodsId": 0,
  "name": "进口香烟",
  "count": 5,
  "avgPrice": 230
}
```

- `avgPrice`：加权平均买入价（整数除法，与 C++ `int` 截断一致）

### 3.2 商品索引与初始价格范围

| `goodsId` | 名称 | 价格范围 |
|-----------|------|----------|
| 0 | 进口香烟 | 100–449 |
| 1 | 走私汽车 | 15000–29999 |
| 2 | 盗版VCD、游戏 | 5–54 |
| 3 | 假白酒（剧毒！） | 1000–3499 |
| 4 | 《上海小宝贝》（禁书） | 5000–13999 |
| 5 | 进口玩具 | 250–849 |
| 6 | 水货手机 | 750–1499 |
| 7 | 伪劣化妆品 | 65–244 |

**在售规则**：正常每日从 8 种中剔除 3 种（`RandomNum(8)` 置 0），剩余 5 种在售（`onSale[i] = true`）；剩余天数 ≤ 2 时 0 剔除，8 种全在售。  \nAgent 通过 `prices[i] == 0` 判断是否在售。

---

## 4. 消息队列

每个动作响应中的 `messages` 数组是 **前端渲染和 Agent 决策的全部依据**。消息绝不只以纯文本形式存在，每条消息都有机器可读的结构。

### 4.1 消息通用结构

```json
{
  "id": "msg-001",
  "type": "diary | news",
  "category": "move | hospital | death | buy | sell | bank | debt | rent | netcafe | score | fame | hack | business_event | health_event | theft_event | shield | setup",
  "text": "消息文本……（前端可直接展示，Agent 可记录日志）",
  "data": {}
}
```

### 4.2 消息类型

#### `diary` — 日记（每日概要）

```json
{
  "id": "msg-001",
  "type": "diary",
  "category": "move",
  "text": "第 39 天：你来到了 王府井。",
  "data": {
    "day": 39,
    "loc": 3,
    "locName": "王府井"
  }
}
```

#### `news` — 新闻事件（商业/健康/偷钱/黑客）

```json
{
  "id": "msg-002",
  "type": "news",
  "category": "business_event",
  "text": "打击盗版！工商局查获大量盗版VCD，价格暴涨 4 倍！",
  "data": {
    "eventType": "business",
    "eventId": 3,
    "goodsId": 2,
    "effect": "multiply",
    "multiplier": 4
  }
}
```

健康事件：

```json
{
  "id": "msg-003",
  "type": "news",
  "category": "health_event",
  "text": "你突发重感冒，住院治疗中……",
  "data": {
    "eventType": "health",
    "eventId": 1,
    "healthLost": 20,
    "forcedHospital": false
  }
}
```

偷钱事件：

```json
{
  "id": "msg-004",
  "type": "news",
  "category": "theft_event",
  "text": "你被小偷偷走了 200 元！",
  "data": {
    "eventType": "theft",
    "eventId": 0,
    "target": "cash",
    "ratio": 10,
    "lost": 200
  }
}
```

> 注意：确认框（AfxMessageBox）是前端 UI/UX 层的问题，API 不包含任何确认/弹窗消息类型。后端遇到需要用户确认的场景时（如强制住院），直接执行规则逻辑并返回对应的 `news` 消息记录已发生的操作。前端如需展示确认弹窗，由前端层根据状态和消息推断，不在 API 契约中体现。

---

## 5. 头部约定

| 请求头 | 说明 |
|--------|------|
| `X-Agent-Tag` | 调用方标识（如 `my-bot-v1`），后端计入统计但不影响游戏逻辑，仅用于可观测性 |
| `X-Idempotency-Key` | 可选：幂等键，防止重复提交动作（网络重试安全） |

---

## 6. 地点与地图

### 6.1 地点编号

| id | 名称（地铁·city=1） | 名称（地面·city=2） |
|----|---------------------|---------------------|
| 1 | 苹果园 | 香山 |
| 2 | 古城 | 八大处 |
| 3 | 王府井 | 颐和园 |
| 4 | 前门 | 圆明园 |
| 5 | 崇文门 | 雍和宫 |
| 6 | 积水潭 | 动物园 |
| 7 | 西直门 | 紫竹院 |
| 8 | 安定门 | 地坛 |
| 9 | 东直门 | 北海 |
| 10 | 建国门 | 天坛 |

### 6.2 城市切换

- `toggleMap` 在 city=1（地铁）和 city=2（地面）之间切换
- 切换不消耗天数，不触发事件
- 每个城市的地点在售商品独立

---

## 7. 游戏流程与随机数契约

### 7.1 一次 `moveTo` 的完整处理顺序

```
输入: moveTo(loc)
  │
  ├─ 1. 更新 currentLoc = loc
  ├─ 2. 天数 -1（timeLeft--）
  ├─ 3. 利息结算（债务 +10%, 存款 +1%）
  ├─ 4. 价格生成（8+3 次随机）
  ├─ 5. 商业事件（至多 18 次随机，命中即触发）
  ├─ 6. 健康事件（至多 12 次随机，每日至多 1 条）
  │     └─ 如 health < 85 且剩余天数 > 3 → 强制住院（额外 3 次随机）
  ├─ 7. 偷钱事件（至多 7 次随机，每日至多 1 条）
  ├─ 8. 黑客事件（如设置开启，1/25 概率触发）
  └─ 9. 输出: 更新后的 state + 期间产生的所有 messages
```

### 7.2 随机数消耗顺序（可逐位重放）

| 步骤 | 消耗 | 说明 |
|------|------|------|
| ① 价格生成 | 8 × `RandomNum(priceRange)` + 3 × `RandomNum(8)` | 正常日 3 个剔除；最后 2 天无剔除 |
| ② 商业事件 | 至多 18 × `RandomNum(950)` | 命中（`%freq==0`）即触发；若目标价=0 跳过但消耗随机数 |
| ③ 健康事件 | 至多 12 × `RandomNum(1000)` | 命中即 break；强制住院 +3 随机数 |
| ④ 偷钱事件 | 至多 7 × `RandomNum(1000)` | 命中即 break |
| ⑤ 黑客事件 | `RandomNum(1000)` + `RandomNum(20/15)` + `RandomNum(20)` | 仅设置开启且触发 |
| ⑥ 网吧 | `RandomNum(10)` | 仅当访问网吧 |

> Agent 可利用种子复现机制进行策略训练：给定种子和动作序列，每日事件完全确定。

---

## 8. 错误码速查

| `code` | HTTP 状态码 | 说明 | Agent 可采取的行动 |
|--------|------------|------|-------------------|
| `INVALID_PARAM` | 400 | 参数值不在合法范围 | 修正参数后重试 |
| `INVALID_COUNT` | 400 | 数量超出范围 | 修正数量后重试 |
| `GAME_NOT_FOUND` | 404 | gameId 无效或游戏已过期 | 创建新游戏 |
| `GAME_OVER` | 409 | 游戏已结束 | 检查 score，决定 submitScore 或 startGame |
| `GAME_NOT_STARTED` | 409 | 尚未调用 startGame | 先发送 startGame |
| `INSUFFICIENT_CASH` | 422 | 现金不足 | 检查 state.cash，凑足资金或调整方案 |
| `COAT_FULL` | 422 | 仓库容量不足 | 检查 state.coat - state.total，减少购买数量 |
| `FORCED_HOSPITAL` | 422 | 强制住院（health<85 且 timeLeft>3） | Agent 应通过 rentHouse 或 buyHealth 解决 |
| `NOT_ON_SALE` | 422 | 商品不在当前地点在售列表 | 检查 state.prices[goodsId]，为 0 则换地点 |
| `NETCAFE_MAX` | 422 | 网吧已达上限 3 次 | 不要再发送 visitNetcafe |
| `CAP_REACHED` | 422 | 名声/容量已达上限 | 检查 state.fame / state.coat |
| `SCORE_ALREADY_SUBMITTED` | 422 | 已提交过高分 | 或 startGame 重置 |

---

## 9. 完整示例：Agent 游玩循环

### 9.1 创建游戏

```http
POST /api/v1/games
Content-Type: application/json

{
  "agentName": "trading-bot-v1"
}
```

### 9.2 初始移动

```http
POST /api/v1/games/a1b2c3d4/actions
Content-Type: application/json

{
  "action": "moveTo",
  "params": { "loc": 3 }
}
```

响应（简化）：

```json
{
  "gameId": "a1b2c3d4",
  "state": {
    "cash": 2000,
    "debt": 5500,
    "timeLeft": 39,
    "currentLoc": 3,
    "prices": [ 234, 0, 12, 0, 7890, 456, 987, 0 ],
    "holdings": [ /* 全 0 */ ],
    ...
  },
  "messages": [
    { "type": "diary", "category": "move", "text": "第 39 天：王府井", "data": { "day": 39, "loc": 3 } },
    { "type": "news", "category": "business_event", "data": { "eventId": 2, "goodsId": 4, "effect": "multiply", "multiplier": 5 } }
  ],
  "gameOver": false
}
```

### 9.3 Agent 决策：买入

```http
POST /api/v1/games/a1b2c3d4/actions
Content-Type: application/json

{
  "action": "buy",
  "params": { "goodsId": 0, "count": 5 }
}
```

### 9.4 Agent 决策：卖出

```http
POST /api/v1/games/a1b2c3d4/actions
Content-Type: application/json

{
  "action": "sell",
  "params": { "goodsId": 0, "count": 5 }
}
```

### 9.5 游戏结束 → 提交高分

```http
POST /api/v1/games/a1b2c3d4/actions
Content-Type: application/json

{
  "action": "submitScore",
  "params": { "name": "trading-bot-v1" }
}
```

---

## 10. 附录：与原版 C++ 对照

| API 概念 | C++ 对应 |
|----------|----------|
| `POST /games` | `SelectionDlg::OnNewGame()` |
| `moveTo(loc)` | `OnTongzhi(nID)` + `HandleNormalEvents()` |
| `buy(goodsId,count)` | `OnMaiRu()` |
| `sell(goodsId,count)` | `OnMaiChu()` |
| `bankDeposit/Withdraw` | `OnCunkuan()` / `OnQukuan()` |
| `repayDebt(amount)` | `OnHuankuan()` |
| `buyHealth(points)` | `OnZhiliao()` |
| `rentHouse()` | `OnFangwu()` |
| `visitNetcafe()` | `OnWangba()` |
| `openBossShield()` | `OnLaoban()` |
| `setup(hack,sound)` | `OnShezhi()` |
| `submitScore(name)` | `OnTopTen()` |
| `messages[].data` | `CRijiDlg` / `CNewsDlg` / `AfxMessageBox` 调用参数 |
| `state.prices` | `m_DrugPrice[8]` |
| `state.holdings[].avgPrice` | `m_nAvePrice[8]`（加权均价） |
| 随机注入 `nextRandom(v)` | 测试钩子，覆盖 `RandomNum()` |

---

> **版本记录**
>
> | 日期 | 版本 | 变更 |
> |------|------|------|
> | 2026-08-16 | 1.0.0 | 初始草案 — 面向双客户端（前端 + Agent）的 API 契约 |