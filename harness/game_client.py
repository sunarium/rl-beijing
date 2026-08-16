"""
HTTP client for the game backend + semantic tool definitions for the LLM agent.
"""
from __future__ import annotations

import json
import httpx

# ── Constants ──────────────────────────────────────────────────────────────

GOODS_NAMES = [
    "进口香烟", "走私汽车", "盗版VCD游戏",
    "假白酒剧毒", "上海小宝贝禁书", "进口玩具",
    "水货手机", "伪劣化妆品",
]

GOODS_NAME_TO_ID = {name: i for i, name in enumerate(GOODS_NAMES)}

LOCATIONS = {
    1: ["建国门", "北京站", "西直门", "崇文门", "东直门",
        "复兴门", "积水潭", "长椿街", "公主坟", "苹果园"],
    2: ["永安里", "方庄", "海淀大街", "永定门", "三元东桥",
        "文津街", "北辰西路", "菜户营", "翠微路", "八角地铁"],
}

CITY_NAMES = {1: "北京市地铁示意图", 2: "北京市地面示意图"}


# ── Game API Client ────────────────────────────────────────────────────────

class GameClient:
    """Thin HTTP wrapper around the game backend."""

    def __init__(self, base_url: str):
        self._client = httpx.Client(base_url=base_url, timeout=30.0)

    def create_game(self, seed: int | None = None) -> tuple[str, dict]:
        resp = self._client.post("/api/v1/games", json={"seed": seed})
        resp.raise_for_status()
        data = resp.json()
        game_id = data["gameId"]
        state = data["state"]
        state["_gameOver"] = data.get("gameOver", False)
        return game_id, state

    def post_action(self, game_id: str, action: str, params: dict | None = None) -> dict:
        resp = self._client.post(
            f"/api/v1/games/{game_id}/actions",
            json={"action": action, "params": params or {}},
        )
        resp.raise_for_status()
        data = resp.json()
        # Normalise game_over into state dict
        if "state" in data:
            data["state"]["_gameOver"] = data.get("gameOver", False)
        return data

    def get_state(self, game_id: str) -> dict:
        resp = self._client.get(f"/api/v1/games/{game_id}")
        resp.raise_for_status()
        data = resp.json()
        state = data.get("state", {})
        state["_gameOver"] = data.get("gameOver", False)
        return state

    def submit_score(self, game_id: str, name: str) -> dict:
        resp = self._client.post(
            f"/api/v1/games/{game_id}/submit",
            json={"action": "submitScore", "params": {"name": name}},
        )
        resp.raise_for_status()
        return resp.json()

    def close(self):
        self._client.close()


# ── State Formatter ────────────────────────────────────────────────────────

def format_state(state: dict) -> str:
    """Pretty-print game state as Chinese text for the LLM."""
    lines = []
    s = state
    lines.append(f"📍 当前状态")
    lines.append(f"  现金: {s['cash']:,}元")
    lines.append(f"  存款: {s['bank']:,}元")
    lines.append(f"  债务: {s['debt']:,}元")
    lines.append(f"  健康: {s['health']}/100")
    lines.append(f"  名声: {s['fame']}/100")
    lines.append(f"  仓库: {s['total']}/{s['coat']}")
    lines.append(f"  剩余天数: {s['timeLeft']}天")
    loc = s.get("currentLoc")
    city = s.get("city", 1)
    city_name = CITY_NAMES.get(city, "")
    if loc is not None and 1 <= loc <= 10:
        loc_name = LOCATIONS[city][loc - 1]
        lines.append(f"  当前位置: {loc_name} ({city_name})")
    else:
        lines.append(f"  当前位置: 尚未出发")
    lines.append(f"  当前得分: {s['score']:,}元")
    lines.append("")

    # Prices
    prices = s.get("prices", [])
    lines.append("🏪 黑市价格")
    for i, price in enumerate(prices):
        status = f"{price:,}元" if price > 0 else "暂缺"
        lines.append(f"  {GOODS_NAMES[i]}: {status}")
    lines.append("")

    # Holdings
    holdings = s.get("holdings", [])
    lines.append("📦 持仓")
    has_goods = False
    for h in holdings:
        if h["count"] > 0:
            has_goods = True
            lines.append(f"  {h['name']}: {h['count']}个 (均价{h['avgPrice']:,}元)")
    if not has_goods:
        lines.append("  空仓")
    lines.append("")

    return "\n".join(lines)


def format_messages(msgs: list[dict]) -> str:
    """Format diary/news messages for the LLM."""
    if not msgs:
        return ""
    lines = ["📰 消息"]
    for m in msgs:
        prefix = "📔" if m.get("type") == "diary" else "📢"
        lines.append(f"  {prefix} {m['text']}")
    return "\n".join(lines)


# ── Tool Definitions (semantic, for the LLM) ───────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "investigate_market",
            "description": "查看当前地点的黑市行情：哪些商品有货、价格多少、你的持仓情况。不消耗天数。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "travel",
            "description": "移动到北京的一个新地点。⚠️ 这会消耗1天时间（共40天），并触发每日事件序列：新价格生成→利息结算→商业事件→健康事件→偷钱事件→讨债检查。地点名取决于当前地图：地铁图有建国门/北京站/西直门/崇文门/东直门/复兴门/积水潭/长椿街/公主坟/苹果园；地面图有永安里/方庄/海淀大街/永定门/三元东桥/文津街/北辰西路/菜户营/翠微路/八角地铁。用toggle_map切换地图。",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_name": {
                        "type": "string",
                        "description": "目的地名称，例如'建国门'、'海淀大街'",
                    },
                },
                "required": ["location_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buy",
            "description": "在当前地点买入商品。只能买黑市有货的商品（价格>0）。购买上限 = min(仓库余量, 现金÷单价)。买入会加权平均持仓成本。",
            "parameters": {
                "type": "object",
                "properties": {
                    "goods_name": {
                        "type": "string",
                        "description": "商品中文名：进口香烟, 走私汽车, 盗版VCD游戏, 假白酒剧毒, 上海小宝贝禁书, 进口玩具, 水货手机, 伪劣化妆品",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "购买数量",
                    },
                },
                "required": ["goods_name", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sell",
            "description": "在当前地点卖出商品。价格按当前黑市价（非买入价）。卖禁书每件-7名声，卖假酒每件-10名声（名声最低0）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "goods_name": {
                        "type": "string",
                        "description": "商品中文名",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "卖出数量",
                    },
                },
                "required": ["goods_name", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bank_deposit",
            "description": "存款。存款每日增值1%利息，且比现金更安全（街頭偷钱只偷现金）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "integer",
                        "description": "存款金额，不能超过当前现金",
                    },
                },
                "required": ["amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bank_withdraw",
            "description": "取款。从银行取出存款到现金。",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "integer",
                        "description": "取款金额，不能超过当前存款",
                    },
                },
                "required": ["amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "repay_debt",
            "description": "还债。到邮局偿还债务。⚠️ 债务每日暴增10%利息！如果债务超过10万元，讨债人每天打掉你30点健康（可能致死）。尽早还债！",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "integer",
                        "description": "还款金额，不能超过当前现金或债务总额",
                    },
                },
                "required": ["amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buy_health",
            "description": "去医院治疗恢复健康。每点健康3500元。⚠️ 健康低于85且剩余天数>3时会强制住院（损失1-2天+巨额医疗费）。保持健康！",
            "parameters": {
                "type": "object",
                "properties": {
                    "points": {
                        "type": "integer",
                        "description": "治疗点数，每点3500元",
                    },
                },
                "required": ["points"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rent_warehouse",
            "description": "租房扩大仓库容量+10（最大140）。需要至少30000现金。费用：现金≤30000时25000元；现金>30000时(现金÷2)-2000元。仓库越大，一次能囤的货越多。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "visit_netcafe",
            "description": "去网吧上网。可赚1-11元广告费。最多去3次。不消耗天数。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_map",
            "description": "切换地铁/地面地图。每个地图有10个不同的地点，价格独立。不消耗天数。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ── Tool Dispatcher ────────────────────────────────────────────────────────

def resolve_tool(tool_name: str, args: dict, client: GameClient, game_id: str) -> tuple[str, list[dict]]:
    """Execute a semantic tool call and return (result_text, new_messages)."""
    if tool_name == "investigate_market":
        state = client.get_state(game_id)
        return format_state(state), []

    elif tool_name == "travel":
        loc_name = args.get("location_name", "")
        # First get current state to know which city we're on
        state = client.get_state(game_id)
        city = state.get("city", 1)
        loc_id = _find_location_id(loc_name, city)
        if loc_id is None:
            # Try the other city
            other = 2 if city == 1 else 1
            loc_id = _find_location_id(loc_name, other)
            if loc_id is not None:
                return f"错误：'{loc_name}'在当前地图不存在。请先用toggle_map切换到{CITY_NAMES[other]}。", []
            return f"错误：未知地点'{loc_name}'。有效地点见工具说明。", []
        resp = client.post_action(game_id, "moveTo", {"loc": loc_id})
        state = resp["state"]
        msgs = resp.get("messages", [])
        text = format_state(state) + "\n" + format_messages(msgs)
        return text, msgs

    elif tool_name == "buy":
        goods_name = args.get("goods_name", "")
        quantity = args.get("quantity", 1)
        goods_id = GOODS_NAME_TO_ID.get(goods_name)
        if goods_id is None:
            return f"错误：未知商品'{goods_name}'。有效商品：{'、'.join(GOODS_NAMES)}", []
        try:
            resp = client.post_action(game_id, "buy", {"goodsId": goods_id, "count": quantity})
            # Build concise result
            state = resp["state"]
            msgs = resp.get("messages", [])
            holding = [h for h in state["holdings"] if h["goodsId"] == goods_id][0]
            text = f"✅ 买入成功: {goods_name}×{quantity}，均价{holding['avgPrice']:,}元，现持{holding['count']}个"
            if msgs:
                text += "\n" + format_messages(msgs)
            return text, msgs
        except httpx.HTTPStatusError as e:
            body = _parse_error(e)
            return f"❌ 买入失败: {body}", []

    elif tool_name == "sell":
        goods_name = args.get("goods_name", "")
        quantity = args.get("quantity", 1)
        goods_id = GOODS_NAME_TO_ID.get(goods_name)
        if goods_id is None:
            return f"错误：未知商品'{goods_name}'。", []
        try:
            resp = client.post_action(game_id, "sell", {"goodsId": goods_id, "count": quantity})
            msgs = resp.get("messages", [])
            text = "✅ 卖出成功"
            if msgs:
                text += "\n" + format_messages(msgs)
            return text, msgs
        except httpx.HTTPStatusError as e:
            body = _parse_error(e)
            return f"❌ 卖出失败: {body}", []

    elif tool_name == "bank_deposit":
        amount = args.get("amount", 0)
        if amount <= 0:
            return "金额必须大于0", []
        try:
            resp = client.post_action(game_id, "bankDeposit", {"amount": amount})
            msgs = resp.get("messages", [])
            state = resp["state"]
            return f"✅ 存款{amount:,}元成功。现金余额: {state['cash']:,}元，存款余额: {state['bank']:,}元", msgs
        except httpx.HTTPStatusError as e:
            return f"❌ 存款失败: {_parse_error(e)}", []

    elif tool_name == "bank_withdraw":
        amount = args.get("amount", 0)
        if amount <= 0:
            return "金额必须大于0", []
        try:
            resp = client.post_action(game_id, "bankWithdraw", {"amount": amount})
            msgs = resp.get("messages", [])
            state = resp["state"]
            return f"✅ 取款{amount:,}元成功。现金余额: {state['cash']:,}元，存款余额: {state['bank']:,}元", msgs
        except httpx.HTTPStatusError as e:
            return f"❌ 取款失败: {_parse_error(e)}", []

    elif tool_name == "repay_debt":
        amount = args.get("amount", 0)
        if amount <= 0:
            return "金额必须大于0", []
        try:
            resp = client.post_action(game_id, "repayDebt", {"amount": amount})
            msgs = resp.get("messages", [])
            state = resp["state"]
            return f"✅ 还款{amount:,}元成功。债务余额: {state['debt']:,}元", msgs
        except httpx.HTTPStatusError as e:
            return f"❌ 还款失败: {_parse_error(e)}", []

    elif tool_name == "buy_health":
        points = args.get("points", 1)
        try:
            resp = client.post_action(game_id, "buyHealth", {"points": points})
            msgs = resp.get("messages", [])
            state = resp["state"]
            return f"✅ 治疗{points}点健康成功。健康: {state['health']}/100，花费: {points*3500:,}元", msgs
        except httpx.HTTPStatusError as e:
            return f"❌ 治疗失败: {_parse_error(e)}", []

    elif tool_name == "rent_warehouse":
        try:
            resp = client.post_action(game_id, "rentHouse", {})
            msgs = resp.get("messages", [])
            state = resp["state"]
            return f"✅ 租房成功！仓库容量: {state['total']}/{state['coat']}", msgs
        except httpx.HTTPStatusError as e:
            return f"❌ 租房失败: {_parse_error(e)}", []

    elif tool_name == "visit_netcafe":
        try:
            resp = client.post_action(game_id, "visitNetcafe", {})
            msgs = resp.get("messages", [])
            text = "✅ 网吧归来"
            if msgs:
                text += "\n" + format_messages(msgs)
            return text, msgs
        except httpx.HTTPStatusError as e:
            return f"❌ 网吧失败: {_parse_error(e)}", []

    elif tool_name == "toggle_map":
        resp = client.post_action(game_id, "toggleMap", {})
        msgs = resp.get("messages", [])
        state = resp["state"]
        text = format_state(state)
        if msgs:
            text += "\n" + format_messages(msgs)
        return text, msgs

    else:
        return f"未知工具: {tool_name}", []


def _find_location_id(name: str, city: int) -> int | None:
    """Find location ID (1-10) by Chinese name."""
    locs = LOCATIONS.get(city, [])
    for i, loc_name in enumerate(locs):
        if loc_name == name:
            return i + 1
    return None


def _parse_error(exc: httpx.HTTPStatusError) -> str:
    """Extract human-readable error from a game backend error response."""
    try:
        body = exc.response.json()
        err = body.get("error", {}) if isinstance(body, dict) else body.get("detail", {}).get("error", {})
        return err.get("message", str(exc))
    except Exception:
        return str(exc)