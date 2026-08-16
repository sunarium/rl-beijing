"""
游戏引擎 — 完整的状态机与规则实现。

覆盖 01-12 全部 Gherkin 特征，严格遵循：
- 每日处理顺序（03）
- 价格生成与剔除（04）
- 买卖与加权均价（05）
- 利息截断语义（06）
- 商业/健康/偷钱/黑客事件（07-09）
- 服务场所（10-11）
- 得分与排行（12）
"""

from models import (
    GOODS, GOODS_NAMES, BUSINESS_EVENTS, HEALTH_EVENTS, THEFT_EVENTS,
    COFFEE_DETAILS, LOC_NAMES, MAP_BUTTON_NAMES, MAP_TITLES, MAP_TOGGLE_TEXT,
    DEFAULT_LEADERBOARD, fame_title, HoldingItem, GameState, GameSettings, Message,
)
from rng import RNG


# ── 错误码 ──────────────────────────────────────────────

class GameError(Exception):
    def __init__(self, code: str, message: str, params: dict | None = None):
        self.code = code
        self.message = message
        self.params = params or {}


# ── 持有明细（内部表示） ────────────────────────────────

class Holding:
    count: int = 0
    avg_price: int = 0


# ── 游戏引擎 ────────────────────────────────────────────

class GameEngine:
    def __init__(self, rng: RNG | None = None):
        self.rng = rng or RNG()
        self._reset()

    def _reset(self):
        # 保留设置（原版行为：新游戏不清零设置项）
        saved_hack = getattr(self, 'hack_acts', False)
        saved_sound = getattr(self, 'close_sound', False)
        # 基础状态
        self.cash = 2000
        self.debt = 5000
        self.bank = 0
        self.health = 100
        self.fame = 100
        self.coat = 100
        self.time_left = 40
        self.current_loc = -1  # -1 = 未开始
        self.city = 1
        self.visit_wangba = 0
        self.hack_acts = saved_hack
        self.close_sound = saved_sound
        self._started = True
        self.game_over = False
        self.score_submitted = False

        # 持仓 [count, avg_price] for each goodsId
        self._holdings = [[0, 0] for _ in range(8)]

        # 当日价格
        self.prices = [0] * 8

        # 消息计数器（保证 id 唯一）
        self._msg_seq = 0

        # 首次卖出标记（用于首次卖出弹窗）
        self._first_sell = {3: True, 4: True}

        # 初始利息结算一次（原版行为: 启动时调用 HandleCashAndDebt）
        self._handle_interest()

    # ── 消息辅助 ──────────────────────────────────────────

    def _next_msg_id(self) -> str:
        self._msg_seq += 1
        return f"msg-{self._msg_seq:03d}"

    def _diary(self, category: str, text: str, data: dict | None = None) -> Message:
        return Message(
            id=self._next_msg_id(),
            type="diary",
            category=category,
            text=text,
            data=data or {},
        )

    def _news(self, category: str, text: str, data: dict | None = None) -> Message:
        return Message(
            id=self._next_msg_id(),
            type="news",
            category=category,
            text=text,
            data=data or {},
        )

    # ── 属性 ──────────────────────────────────────────────

    @property
    def total(self) -> int:
        return sum(h[0] for h in self._holdings)

    @property
    def score(self) -> int:
        return self.cash + self.bank - self.debt

    def get_title(self) -> str:
        return fame_title(self.fame)

    def get_loc_name(self, loc: int | None = None) -> str:
        """获取住院文案用的地点名称（loc[] 数组）。"""
        if loc is None:
            loc = self.current_loc
        if loc < 1 or loc > 10:
            return ""
        idx = 10 * (self.city - 1) + (loc - 1)
        return LOC_NAMES[idx]

    def get_button_names(self) -> list[str]:
        return MAP_BUTTON_NAMES.get(self.city, [])

    def city_name(self) -> str:
        return MAP_TITLES.get(self.city, "")

    # ── 状态快照 ──────────────────────────────────────────

    def get_state(self) -> GameState:
        return GameState(
            cash=self.cash,
            debt=self.debt,
            bank=self.bank,
            health=self.health,
            fame=self.fame,
            coat=self.coat,
            total=self.total,
            holdings=[
                HoldingItem(
                    goodsId=i,
                    name=GOODS_NAMES[i],
                    count=self._holdings[i][0],
                    avgPrice=self._holdings[i][1],
                )
                for i in range(8)
            ],
            prices=list(self.prices),
            timeLeft=self.time_left,
            currentLoc=self.current_loc if self.current_loc >= 0 else None,
            city=self.city,
            cityName=self.city_name(),
            visitWangba=self.visit_wangba,
            settings=GameSettings(hackActs=self.hack_acts, closeSound=self.close_sound),
            score=self.score,
        )

    # ── 利息（06） ──────────────────────────────────────

    def _handle_interest(self):
        """债务 +10%，存款 +1%，使用 C double 截断语义。"""
        self.debt = self.debt + int(self.debt * 0.10)
        self.bank = self.bank + int(self.bank * 0.01)

    # ── 价格生成（04） ──────────────────────────────────

    def _make_prices(self):
        """生成 8 种商品价格 + 剔除 3 种（除非最后 2 天）。"""
        for i in range(8):
            self.prices[i] = GOODS[i]["base"] + self.rng.random(GOODS[i]["range"])

        # 正常日（time_left > 2）：剔除 3 种
        if self.time_left > 2:
            for _ in range(3):
                idx = self.rng.random(8)
                self.prices[idx] = 0

    # ── 商业事件（07） ──────────────────────────────────

    def _do_random_stuff(self, msgs: list[Message]):
        """判定 18 条商业事件，每日可多条。"""
        for ev in BUSINESS_EVENTS:
            x = self.rng.random(950)
            if x % ev["freq"] != 0:
                continue

            drug = ev["drug"]
            # 目标商品价 0 时跳过（仍消耗了随机数）
            if self.prices[drug] <= 0:
                continue

            if ev["plus"] > 0:
                self.prices[drug] *= ev["plus"]
                msgs.append(self._news("business_event", ev["msg"], {
                    "eventType": "business", "eventId": ev["id"],
                    "goodsId": drug, "effect": "multiply", "multiplier": ev["plus"],
                }))
            elif ev["minus"] > 0:
                self.prices[drug] //= ev["minus"]
                msgs.append(self._news("business_event", ev["msg"], {
                    "eventType": "business", "eventId": ev["id"],
                    "goodsId": drug, "effect": "divide", "divisor": ev["minus"],
                }))
            elif ev["add"] > 0:
                # 赠送
                space = self.coat - self.total
                if space <= 0:
                    msgs.append(self._diary("business_event",
                        f"可惜!俺租的房子太小，只能放{space}个物品。"))
                    # 原版: 空间满时 return 中断后续商业事件
                    break
                actual = min(ev["add"], space)
                old_count, old_price = self._holdings[drug]
                if old_count > 0:
                    self._holdings[drug][0] += actual
                else:
                    self._holdings[drug] = [actual, 0]
                msgs.append(self._news("business_event", ev["msg"], {
                    "eventType": "business", "eventId": ev["id"],
                    "goodsId": drug, "effect": "gift", "count": actual,
                }))
                # 末条（id=17）附加债务
                if ev["id"] == 17:
                    self.debt += 2500
                    msgs.append(self._diary("debt", "村长托人硬卖水货手机，收您2500元。"))

    # ── 健康事件（08） ──────────────────────────────────

    def _do_random_event(self, msgs: list[Message]) -> bool:
        """判定 12 条健康事件。返回 True 表示强制住院已发生（跳过偷钱）。"""
        for ev in HEALTH_EVENTS:
            x = self.rng.random(1000)
            if x % ev["freq"] != 0:
                continue
            # 命中
            self.health -= ev["hunt"]
            msgs.append(self._news("health_event", ev["msg"], {
                "eventType": "health", "eventId": ev["id"],
                "healthLost": ev["hunt"], "forcedHospital": False,
            }))
            break  # 每日至多 1 条

        # 健康 < 0 → 死亡
        if self.health < 0:
            msgs.append(self._diary("death",
                "俺倒在街头,身边日记本上写着：\"北京，我将再来!\""))
            self.game_over = True
            return False

        # 健康 < 20 且 > 0 → 警告
        if 0 < self.health < 20:
            msgs.append(self._diary("health_warning",
                "俺的健康..健康危机..快去医.."))

        # 强制住院判定：health < 85 且 time_left > 3
        if self.health < 85 and self.time_left > 3:
            delay = 1 + self.rng.random(2)  # 1 或 2 天
            medical_cost = delay * (1000 + self.rng.random(8500))
            self.debt += medical_cost
            self.health += 10
            if self.health > 100:
                self.health = 100
            self.time_left -= delay

            # 住院文案
            loc_name = self.get_loc_name()
            coffee_idx = self.rng.random(29)
            coffee_detail = COFFEE_DETAILS[coffee_idx]
            msgs.append(self._diary("hospital",
                f"好心的市民把我抬到医院，医生让我治疗{delay}天。"))
            msgs.append(self._diary("hospital",
                f"由于不注意身体,我被人发现昏迷在{loc_name}附近的{coffee_detail}。"))
            msgs.append(self._diary("hospital",
                f"村长让人为我垫付了住院费用{medical_cost}元。"))

            # 住院后若 health 仍 < 0 → 死亡
            if self.health < 0:
                msgs.append(self._diary("death",
                    "俺倒在街头,身边日记本上写着：\"北京，我将再来!\""))
                self.game_over = True
                return True

            # 住院后若 time_left <= 0 → 结算
            if self.time_left <= 0:
                self.time_left = 0
                self._settle(msgs)
                return True

            return True  # 强制住院已发生，跳过偷钱事件

        return False

    # ── 偷钱事件（09） ──────────────────────────────────

    def _on_steal(self, msgs: list[Message]):
        """判定 7 条偷钱事件，每日至多 1 条。"""
        for ev in THEFT_EVENTS:
            x = self.rng.random(1000)
            if x % ev["freq"] != 0:
                continue

            ratoi = ev["ratoi"]
            if ev["target"] == "cash":
                lost = (self.cash // 100) * (100 - ratoi)
                self.cash = lost
                msgs.append(self._news("theft_event", ev["msg"], {
                    "eventType": "theft", "eventId": ev["id"],
                    "target": "cash", "ratio": ratoi, "lost": lost,
                }))
                if self.cash < 0:
                    self.cash = 0
                    msgs.append(self._diary("cash", "俺不好办了。"))
            elif ev["target"] == "bank" and self.bank > 0:
                lost = (self.bank // 100) * (100 - ratoi)
                self.bank = lost
                msgs.append(self._news("theft_event", ev["msg"], {
                    "eventType": "theft", "eventId": ev["id"],
                    "target": "bank", "ratio": ratoi, "lost": lost,
                }))
            # 两种情况都 break（空存款也 break）
            break

    # ── 黑客事件（09） ──────────────────────────────────

    def _hacker(self, msgs: list[Message]):
        """黑客事件（仅 m_bHackActs = TRUE 时触发）。"""
        if not self.hack_acts:
            return
        x = self.rng.random(1000)
        if x % 25 != 0:
            return

        if self.bank < 1000:
            return

        if self.bank > 100000:
            num = self.bank // (2 + self.rng.random(20))
            if self.rng.random(20) % 3 != 0:
                self.bank -= num
                msgs.append(self._news("hack",
                    "黑客入侵银行网络，疯狂修改数据库，我的存款减少了{num}。",
                    {"eventType": "hack", "lost": num}))
            else:
                self.bank += num
                msgs.append(self._news("hack",
                    "黑客入侵银行网络，疯狂修改数据库，我的存款增加了{num}。",
                    {"eventType": "hack", "gained": num}))
        else:
            num = self.bank // (1 + self.rng.random(15))
            self.bank += num
            msgs.append(self._news("hack",
                "黑客入侵银行网络，疯狂修改数据库，我的存款增加了{num}。",
                {"eventType": "hack", "gained": num}))

    # ── 结算（12） ──────────────────────────────────────

    def _settle(self, msgs: list[Message]):
        """天数耗尽或退出时的结算。"""
        final_score = self.score

        # 自动清仓（timeLeft=0 时强制卖出剩余货物）
        if self.total > 0:
            items = []
            for i in range(8):
                cnt = self._holdings[i][0]
                if cnt > 0 and self.prices[i] > 0:
                    self.cash += cnt * self.prices[i]
                    items.append(GOODS_NAMES[i])
                    self._holdings[i][0] = 0
            if items:
                msgs.append(self._diary("settle",
                    f"系统替我卖了剩余货物: {', '.join(items)}。"))

        if final_score <= 0:
            msgs.append(self._news("score",
                "《北京游戏报》报道: 玩家“无名氏”在北京没挣着钱，被遣送回家。",
                {"score": final_score, "bankrupt": True}))
            self.game_over = True
            return

        if final_score > 10000000:
            msgs.append(self._news("score",
                f"您挣的钱{final_score}元人民币很高，建议您发给作者进行高手排行。",
                {"score": final_score, "cheat": True}))

        msgs.append(self._diary("score",
            f"您的最终得分: {final_score}。健康: {self.health}。称号: {self.get_title()}。"))
        self.game_over = True

    def _check_debt(self, msgs: list[Message]):
        """债务 > 100000 时讨债。"""
        if self.debt > 100000:
            self.health -= 30
            msgs.append(self._diary("debt",
                "俺欠钱太多，村长叫一群老乡揍了俺一顿!"))
            if self.health < 0:
                msgs.append(self._diary("death",
                    "俺倒在街头,身边日记本上写着：\"北京，我将再来!\""))
                self.game_over = True

    # ── 命令处理 ────────────────────────────────────────

    def handle_action(self, action: str, params: dict) -> tuple[GameState, list[Message]]:
        """处理动作，返回 (新状态, 消息列表)。"""
        msgs: list[Message] = []

        # ── startGame ────────────────────────────────
        if action == "startGame":
            self._reset()
            msgs.append(self._diary("start", "新游戏开始。"))
            return self.get_state(), msgs

        # ── 游戏结束保护 ─────────────────────────────
        if self.game_over:
            if action == "startGame":
                self._reset()
                msgs.append(self._diary("start", "新游戏开始。"))
                return self.get_state(), msgs
            if action == "submitScore":
                # 允许提交高分
                pass
            else:
                raise GameError("GAME_OVER", "游戏已结束，请先 startGame 开始新游戏。")

        if not self._started and action not in ("startGame", "setup"):
            raise GameError("GAME_NOT_STARTED", "游戏未开始，请先发送 startGame。")

        # ── toggleMap ────────────────────────────────
        if action == "toggleMap":
            self.city = 2 if self.city == 1 else 1
            msgs.append(self._diary("map", f"切换至{MAP_TITLES[self.city]}。"))
            return self.get_state(), msgs

        # ── moveTo(loc) ──────────────────────────────
        if action == "moveTo":
            loc = self._get_param(params, "loc", int, 1, 10)
            return self._handle_move_to(loc, msgs)

        # ── buy(goodsId, count) ──────────────────────
        if action == "buy":
            goods_id = self._get_param(params, "goodsId", int, 0, 7)
            count = self._get_param(params, "count", int, 1, 9999)
            return self._handle_buy(goods_id, count, msgs)

        # ── sell(goodsId, count) ─────────────────────
        if action == "sell":
            goods_id = self._get_param(params, "goodsId", int, 0, 7)
            count = self._get_param(params, "count", int, 1, 9999)
            return self._handle_sell(goods_id, count, msgs)

        # ── bankDeposit(n) ───────────────────────────
        if action == "bankDeposit":
            amount = self._get_param(params, "amount", int, 0, self.cash)
            return self._handle_bank_deposit(amount, msgs)

        # ── bankWithdraw(n) ──────────────────────────
        if action == "bankWithdraw":
            amount = self._get_param(params, "amount", int, 0, self.bank)
            return self._handle_bank_withdraw(amount, msgs)

        # ── repayDebt(n) ─────────────────────────────
        if action == "repayDebt":
            amount = self._get_param(params, "amount", int, 0, max(self.cash, self.debt))
            return self._handle_repay_debt(amount, msgs)

        # ── buyHealth(points) ────────────────────────
        if action == "buyHealth":
            points = self._get_param(params, "points", int, 1, 100 - self.health)
            return self._handle_buy_health(points, msgs)

        # ── rentHouse() ──────────────────────────────
        if action == "rentHouse":
            return self._handle_rent_house(msgs)

        # ── visitNetcafe() ───────────────────────────
        if action == "visitNetcafe":
            return self._handle_netcafe(msgs)

        # ── openBossShield() ─────────────────────────
        if action == "openBossShield":
            msgs.append(self._diary("shield", "老板来了！画面已遮挡。"))
            return self.get_state(), msgs

        # ── setup(hack, sound) ───────────────────────
        if action == "setup":
            if "hackActs" in params:
                self.hack_acts = bool(params["hackActs"])
            if "closeSound" in params:
                self.close_sound = bool(params["closeSound"])
            msgs.append(self._diary("setup", "游戏设置已更新。"))
            return self.get_state(), msgs

        # ── submitScore(name) ────────────────────────
        if action == "submitScore":
            name = str(params.get("name", "无名氏"))
            return self._handle_submit_score(name, msgs)

        raise GameError("INVALID_ACTION", f"未知动作: {action}")

    # ── 参数辅助 ──────────────────────────────────────

    def _get_param(self, params: dict, key: str, typ: type, lo=None, hi=None):
        if key not in params:
            raise GameError("INVALID_PARAM", f"缺少参数: {key}")
        val = params[key]
        if not isinstance(val, (int, float, str)):
            raise GameError("INVALID_PARAM", f"参数 {key} 类型错误")
        if typ == int:
            val = int(val)
        if lo is not None and val < lo:
            raise GameError("INVALID_PARAM", f"参数 {key} 不能小于 {lo}")
        if hi is not None and val > hi:
            raise GameError("INVALID_PARAM", f"参数 {key} 不能大于 {hi}")
        return val

    # ── moveTo 完整序列 ──────────────────────────────

    def _handle_move_to(self, loc: int, msgs: list[Message]) -> tuple[GameState, list[Message]]:
        if self.current_loc == loc:
            msgs.append(self._diary("move", "你已经在当前地点。"))
            return self.get_state(), msgs

        self.current_loc = loc

        # ① 天数归零检查
        if self.time_left <= 0:
            self._settle(msgs)
            return self.get_state(), msgs

        msgs.append(self._diary("move",
            f"第 {40 - self.time_left + 1} 天：你来到了 {MAP_BUTTON_NAMES[self.city][loc-1]}。",
            {"day": 40 - self.time_left + 1, "loc": loc}))

        # ① 价格生成
        self._make_prices()

        # ② 利息结算
        self._handle_interest()

        # ③ 商业事件
        self._do_random_stuff(msgs)

        # ④ 刷新黑市列表（无状态变更，仅用于展示）

        # ⑤ 健康事件（+强制住院检查）
        hospitalized = self._do_random_event(msgs)
        if self.game_over:
            return self.get_state(), msgs

        # ⑥ 偷钱 & 黑客事件（强制住院时跳过）
        if not hospitalized:
            self._on_steal(msgs)
            self._hacker(msgs)

        # ⑦ 讨债（债务 > 100000）
        self._check_debt(msgs)
        if self.game_over:
            return self.get_state(), msgs

        # ⑧ 天数 -1
        self.time_left -= 1

        # ⑨ 天数警告/结算
        if self.time_left == 0:
            self._settle(msgs)
        elif self.time_left == 1:
            msgs.append(self._diary("warning",
                "俺明天回家乡，快把全部卖掉。"))

        return self.get_state(), msgs

    # ── 买入 ─────────────────────────────────────────

    def _handle_buy(self, goods_id: int, count: int, msgs: list[Message]) -> tuple[GameState, list[Message]]:
        price = self.prices[goods_id]
        if price <= 0:
            raise GameError("NOT_ON_SALE",
                f"{GOODS_NAMES[goods_id]}当前不在售。",
                {"goodsId": goods_id})

        max_buy = min(self.coat - self.total, self.cash // price)
        if max_buy <= 0:
            raise GameError("INSUFFICIENT_CASH",
                "现金不足或仓库已满。",
                {"cash": self.cash, "coatFree": self.coat - self.total})

        if count > max_buy:
            count = max_buy

        cost = price * count
        self.cash -= cost
        old_count, old_price = self._holdings[goods_id]
        if old_count > 0:
            # 加权平均
            new_avg = (price * count + old_price * old_count) // (count + old_count)
            self._holdings[goods_id] = [old_count + count, new_avg]
        else:
            self._holdings[goods_id] = [count, price]

        msgs.append(self._diary("buy",
            f"买入 {count} 个 {GOODS_NAMES[goods_id]}，花费 {cost} 元。",
            {"goodsId": goods_id, "count": count, "cost": cost}))

        return self.get_state(), msgs

    # ── 卖出 ─────────────────────────────────────────

    def _handle_sell(self, goods_id: int, count: int, msgs: list[Message]) -> tuple[GameState, list[Message]]:
        price = self.prices[goods_id]
        if price <= 0:
            raise GameError("NOT_ON_SALE",
                f"哦？仿佛没有人在这里做{GOODS_NAMES[goods_id]}生意。",
                {"goodsId": goods_id})

        old_count, _ = self._holdings[goods_id]
        if old_count <= 0:
            raise GameError("INVALID_COUNT",
                f"没有可卖的{GOODS_NAMES[goods_id]}。",
                {"goodsId": goods_id, "holding": old_count})

        if count > old_count:
            count = old_count

        revenue = price * count
        self.cash += revenue
        self._holdings[goods_id][0] -= count

        msgs.append(self._diary("sell",
            f"卖出 {count} 个 {GOODS_NAMES[goods_id]}，收入 {revenue} 元。",
            {"goodsId": goods_id, "count": count, "revenue": revenue}))

        # 名声扣减
        if goods_id == 4:  # 禁书
            fame_loss = 7 * count
            if self._first_sell.get(4):
                msgs.append(self._diary("fame",
                    "买卖《上海小宝贝》（禁书）,污染社会,俺的名声变坏了啊!"))
                self._first_sell[4] = False
            self.fame = max(0, self.fame - fame_loss)
        elif goods_id == 3:  # 假酒
            fame_loss = 10 * count
            if self._first_sell.get(3):
                msgs.append(self._diary("fame",
                    "买卖假白酒（剧毒！）,危害社会，俺的名声下降了."))
                self._first_sell[3] = False
            self.fame = max(0, self.fame - fame_loss)

        return self.get_state(), msgs

    # ── 银行存款 ─────────────────────────────────────

    def _handle_bank_deposit(self, amount: int, msgs: list[Message]) -> tuple[GameState, list[Message]]:
        if amount > self.cash:
            raise GameError("INSUFFICIENT_CASH",
                "现金不足，无法存款。",
                {"cash": self.cash, "requested": amount})
        self.cash -= amount
        self.bank += amount
        msgs.append(self._diary("bank", f"存款 {amount} 元。", {"amount": amount}))
        return self.get_state(), msgs

    def _handle_bank_withdraw(self, amount: int, msgs: list[Message]) -> tuple[GameState, list[Message]]:
        if amount > self.bank:
            raise GameError("INSUFFICIENT_CASH",
                "存款不足，无法取款。",
                {"bank": self.bank, "requested": amount})
        self.bank -= amount
        self.cash += amount
        msgs.append(self._diary("bank", f"取款 {amount} 元。", {"amount": amount}))
        return self.get_state(), msgs

    # ── 邮局还款 ─────────────────────────────────────

    def _handle_repay_debt(self, amount: int, msgs: list[Message]) -> tuple[GameState, list[Message]]:
        if amount > self.cash:
            raise GameError("INSUFFICIENT_CASH",
                f"村长老婆狂吞\"雪中丐\"补钙片，冷笑道：“你还得起吗?”",
                {"cash": self.cash, "requested": amount})
        actual = min(amount, self.debt)
        if actual <= 0:
            msgs.append(self._diary("debt", "你已没有债务。"))
            return self.get_state(), msgs
        self.cash -= actual
        self.debt -= actual
        msgs.append(self._diary("debt", f"还款 {actual} 元。", {"amount": actual}))
        return self.get_state(), msgs

    # ── 医院治疗 ─────────────────────────────────────

    def _handle_buy_health(self, points: int, msgs: list[Message]) -> tuple[GameState, list[Message]]:
        if self.health >= 100:
            msgs.append(self._diary("hospital",
                "小护士笑咪咪地望着俺：\"大哥！神经科这边挂号。\""))
            return self.get_state(), msgs

        max_points = 100 - self.health
        if points > max_points:
            points = max_points

        cost = points * 3500
        if cost > self.cash:
            raise GameError("INSUFFICIENT_CASH",
                "医生说，\"钱不够哎! 拒绝治疗。\"",
                {"cash": self.cash, "cost": cost})

        self.cash -= cost
        self.health += points
        msgs.append(self._diary("hospital", f"治疗 {points} 点健康，花费 {cost} 元。",
                                {"points": points, "cost": cost}))
        return self.get_state(), msgs

    # ── 房屋中介 ─────────────────────────────────────

    def _handle_rent_house(self, msgs: list[Message]) -> tuple[GameState, list[Message]]:
        if self.coat >= 140:
            msgs.append(self._diary("rent",
                "中介说，您的房子比局长的还大!还租房?"))
            return self.get_state(), msgs

        if self.cash < 30000:
            msgs.append(self._diary("rent",
                "中介说，您没有三万现金就想租房? 一边凉快去!"))
            return self.get_state(), msgs

        if self.cash <= 30000:
            self.cash -= 25000
        else:
            self.cash = self.cash // 2 - 2000

        self.coat = min(140, self.coat + 10)
        msgs.append(self._diary("rent",
            f"我的房子可以放{self.coat}个物品了! 好象中介公司骗了我一些钱...",
            {"coat": self.coat}))
        return self.get_state(), msgs

    # ── 网吧 ─────────────────────────────────────────

    def _handle_netcafe(self, msgs: list[Message]) -> tuple[GameState, list[Message]]:
        if self.visit_wangba >= 3:
            msgs.append(self._diary("netcafe",
                "村长放出话来：你别总是在网吧里鬼混，快去做正经买卖!"))
            return self.get_state(), msgs

        if self.cash < 15:
            msgs.append(self._diary("netcafe",
                "进网吧至少身上要带15元，呵呵，取钱再来。"))
            return self.get_state(), msgs

        self.visit_wangba += 1
        reward = 1 + self.rng.random(10)
        self.cash += reward
        msgs.append(self._diary("netcafe",
            f"感谢电信改革，可以免费上网! 还挣了美国网络广告费{reward}元，嘿嘿!",
            {"reward": reward}))
        return self.get_state(), msgs

    # ── 提交高分 ─────────────────────────────────────

    def _handle_submit_score(self, name: str, msgs: list[Message]) -> tuple[GameState, list[Message]]:
        if self.score_submitted:
            raise GameError("SCORE_ALREADY_SUBMITTED", "已经提交过高分。")
        self.score_submitted = True
        msgs.append(self._diary("score", f"高分已提交: {name} — {self.score} 分。",
                                {"name": name, "score": self.score}))
        return self.get_state(), msgs


# ── 游戏会话管理 ──────────────────────────────────────

import uuid

class GameSessionManager:
    """管理多个游戏实例的内存存储。"""

    def __init__(self):
        self._games: dict[str, GameEngine] = {}
        self._leaderboard = [dict(e) for e in DEFAULT_LEADERBOARD]  # mutable copy

    def create_game(self, seed: int | None = None) -> tuple[str, GameEngine]:
        game_id = str(uuid.uuid4())
        rng = RNG(seed)
        engine = GameEngine(rng)
        # startGame should be an explicit action per spec
        self._games[game_id] = engine
        return game_id, engine

    def get_game(self, game_id: str) -> GameEngine | None:
        return self._games.get(game_id)

    def delete_game(self, game_id: str):
        self._games.pop(game_id, None)

    def get_leaderboard(self) -> list[dict]:
        """返回高分榜（得分降序排列）。"""
        sorted_board = sorted(self._leaderboard, key=lambda x: x["score"], reverse=True)
        for i, entry in enumerate(sorted_board[:10]):
            entry["rank"] = i + 1
        return sorted_board[:10]

    def submit_score(self, name: str, score: int, health: int, title: str) -> bool:
        """尝试插入高分榜。返回 True 表示进入前十名。"""
        if score <= 0:
            return False
        self._leaderboard.append({
            "name": name, "score": score, "health": health, "title": title
        })
        self._leaderboard = sorted(
            self._leaderboard, key=lambda x: x["score"], reverse=True
        )[:10]
        return True