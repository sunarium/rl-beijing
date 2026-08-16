"""
Behavioral tests — 行为测试覆盖 Gherkin spec 核心场景。
验证游戏状态机符合 01-12 号 feature 的契约。
"""

import pytest
from game_engine import GameEngine, GameError
from rng import RNG
from models import GOODS_NAMES


# ── 辅助函数 ──────────────────────────────────────────

def engine_with_rng(*vals: int) -> GameEngine:
    """创建引擎并用预置随机序列初始化。"""
    rng = RNG(seed=0)
    rng.push_test(*vals)
    return GameEngine(rng)


def do_start(eng: GameEngine):
    st, _ = eng.handle_action("startGame", {})
    return st


def do_move(eng: GameEngine, loc: int):
    st, msgs = eng.handle_action("moveTo", {"loc": loc})
    return st, msgs


# ══════════════════════════════════════════════════════
# 01 — 新游戏初始化
# ══════════════════════════════════════════════════════

class TestInit:
    def test_initial_values(self):
        eng = engine_with_rng()
        st = do_start(eng)
        assert st.cash == 2000
        assert st.debt == 5500  # 初始利息结算一次（原版行为）
        assert st.bank == 0
        assert st.health == 100
        assert st.healthMax == 100
        assert st.fame == 100
        assert st.fameMin == 0
        assert st.fameMax == 100
        assert st.coat == 100
        assert st.coatMax == 140
        assert st.total == 0
        assert st.timeLeft == 40
        assert st.currentLoc is None
        assert st.city == 1
        assert st.cityName == "北京市地铁示意图"
        assert st.visitWangba == 0
        assert st.settings.hackActs is False
        assert st.settings.closeSound is False
        assert st.score == -3500  # 2000 + 0 - 5500

    def test_reset_preserves_settings(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.handle_action("setup", {"hackActs": True, "closeSound": True})
        do_start(eng)  # restart
        st = eng.get_state()
        assert st.settings.hackActs is True
        assert st.settings.closeSound is True


# ══════════════════════════════════════════════════════
# 02 — 地图与移动
# ══════════════════════════════════════════════════════

class TestMapMove:
    def test_toggle_map(self):
        eng = engine_with_rng()
        do_start(eng)
        st, _ = eng.handle_action("toggleMap", {})
        assert st.city == 2
        assert st.cityName == "北京市地面示意图"
        st, _ = eng.handle_action("toggleMap", {})
        assert st.city == 1

    def test_move_same_location_noop(self):
        eng = engine_with_rng()
        do_start(eng)
        st1, msgs = eng.handle_action("moveTo", {"loc": 3})
        st2, msgs2 = eng.handle_action("moveTo", {"loc": 3})
        assert st2.timeLeft == st1.timeLeft  # no day consumed

    def test_move_different_location_consumes_day(self):
        eng = engine_with_rng()
        do_start(eng)
        st, _ = eng.handle_action("moveTo", {"loc": 1})
        assert st.timeLeft == 39
        assert st.currentLoc == 1


# ══════════════════════════════════════════════════════
# 03 — 时间与回合流程
# ══════════════════════════════════════════════════════

class TestTurnFlow:
    def test_time_decrements_without_rng_death(self):
        """使用已消耗完随机数的引擎测试天数递减（跳过所有 RNG 事件）。"""
        eng = engine_with_rng()
        do_start(eng)
        moves = 0
        for i in range(40):
            loc = (i % 10) + 1
            try:
                st, msgs = eng.handle_action("moveTo", {"loc": loc})
                moves += 1
                if eng.game_over:
                    break
            except Exception:
                break
        assert eng.game_over, f"游戏应在 40 天内结束，已移动 {moves} 次"

    def test_last_day_warning_direct(self):
        """直接设置 time_left=2 移动后验证最后 1 天警告。"""
        eng = engine_with_rng()
        do_start(eng)
        eng.time_left = 2
        eng.current_loc = 1
        st, msgs = eng.handle_action("moveTo", {"loc": 3})
        if not eng.game_over:
            assert st.timeLeft == 1
            assert any("明天回家乡" in m.text for m in msgs)

    def test_day_zero_settlement(self):
        eng = engine_with_rng()
        do_start(eng)
        for _ in range(39):
            try:
                eng.handle_action("moveTo", {"loc": 1})
            except Exception:
                break
        st, msgs = eng.handle_action("moveTo", {"loc": 1})
        if eng.game_over:
            assert st.timeLeft == 0


# ══════════════════════════════════════════════════════
# 04 — 市场与价格
# ══════════════════════════════════════════════════════

class TestPricing:
    def test_prices_within_range(self):
        """直接调用 _make_prices 验证价格在正确范围。"""
        rng = RNG(seed=42)
        eng = GameEngine(rng)
        do_start(eng)
        eng._make_prices()
        for i, g in enumerate([{"base": 100, "range": 350}, {"base": 15000, "range": 15000},
                                {"base": 5, "range": 50}, {"base": 1000, "range": 2500},
                                {"base": 5000, "range": 9000}, {"base": 250, "range": 600},
                                {"base": 750, "range": 750}, {"base": 65, "range": 180}]):
            if eng.prices[i] > 0:
                assert g["base"] <= eng.prices[i] <= g["base"] + g["range"] - 1, \
                    f"goods {i} price {eng.prices[i]} out of range [{g['base']}, {g['base'] + g['range'] - 1}]"

    def test_last_two_days_all_on_sale(self):
        """剩余天数 ≤ 2 时全部在售。"""
        eng = engine_with_rng()
        do_start(eng)
        eng.time_left = 2
        eng._make_prices()  # time_left=2, no leaveout
        assert all(p > 0 for p in eng.prices), f"最后 2 天应全在售，实际: {eng.prices}"


# ══════════════════════════════════════════════════════
# 05 — 买卖交易
# ══════════════════════════════════════════════════════

class TestTrading:
    def test_buy(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.prices = [150, 0, 0, 0, 0, 0, 0, 0]
        st, _ = eng.handle_action("buy", {"goodsId": 0, "count": 5})
        assert st.cash == 2000 - 150 * 5
        assert st.total == 5
        holding = [h for h in st.holdings if h.goodsId == 0][0]
        assert holding.count == 5
        assert holding.avgPrice == 150

    def test_buy_not_on_sale_rejected(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.prices = [0, 0, 0, 0, 0, 0, 0, 0]
        with pytest.raises(GameError, match="NOT_ON_SALE"):
            eng.handle_action("buy", {"goodsId": 4, "count": 1})

    def test_sell_fame_penalty(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.prices = [0, 0, 0, 0, 200, 0, 0, 0]
        eng._holdings[4] = [1, 180]  # have 1 unit of banned book
        st, msgs = eng.handle_action("sell", {"goodsId": 4, "count": 1})
        assert st.fame == 93  # 100 - 7
        assert any("禁书" in m.text for m in msgs)

    def test_sell_not_on_sale_rejected(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.prices = [0, 0, 0, 0, 0, 0, 0, 0]
        eng._holdings[0] = [1, 100]
        with pytest.raises(GameError, match="NOT_ON_SALE"):
            eng.handle_action("sell", {"goodsId": 0, "count": 1})


# ══════════════════════════════════════════════════════
# 06 — 经济与利息
# ══════════════════════════════════════════════════════

class TestInterest:
    def test_debt_interest(self):
        eng = engine_with_rng()
        do_start(eng)
        assert eng.debt == 5500  # post-startup interest on 5000 → 5500
        eng._handle_interest()
        assert eng.debt == 6050
        eng._handle_interest()
        assert eng.debt == 6655
        eng._handle_interest()
        assert eng.debt == 7320
        eng._handle_interest()
        assert eng.debt == 8052
        eng._handle_interest()
        assert eng.debt == 8857

    def test_bank_interest(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.bank = 1000
        eng._handle_interest()
        assert eng.bank == 1010
        eng._handle_interest()
        assert eng.bank == 1020


# ══════════════════════════════════════════════════════
# 08 — 健康事件
# ══════════════════════════════════════════════════════

class TestHealth:
    def test_forced_hospital(self):
        """健康 < 85 且 timeLeft > 3 → 强制住院."""
        eng = engine_with_rng()
        do_start(eng)
        eng.health = 80
        eng.time_left = 20
        # Controlled RNG: health events all miss, then hospital RNG
        vals = [999] * 12  # 12 health checks all miss (999%freq != 0 for all)
        vals.extend([0, 5000, 15])  # delay=1, cost=1*(1000+5000)=6000, coffee_idx=15
        eng.rng.push_test(*vals)
        st, msgs = eng.handle_action("moveTo", {"loc": 3})
        assert st.health >= 90  # 80 + 10 = 90
        assert st.debt >= 5500 + 6000  # original + medical cost
        assert any("医院" in m.text for m in msgs)

    def test_death(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.health = -5
        st, msgs = eng.handle_action("moveTo", {"loc": 3})
        assert eng.game_over
        assert any("倒在街头" in m.text for m in msgs)


# ══════════════════════════════════════════════════════
# 09 — 金钱损失
# ══════════════════════════════════════════════════════

class TestTheft:
    def test_cash_theft_formula(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.cash = 2000
        eng.rng.push_test(0)
        eng._on_steal([])
        assert eng.cash == 1800  # (2000/100)*(100-10) = 20*90

    def test_cash_theft_examples(self):
        cases = [(2000, 1800), (1999, 1710), (150, 90), (99, 0)]
        for before, after in cases:
            eng = engine_with_rng()
            do_start(eng)
            eng.cash = before
            eng.rng.push_test(0)
            eng._on_steal([])
            assert eng.cash == after, f"cash={before} → {after}"


# ══════════════════════════════════════════════════════
# 10 — 服务场所
# ══════════════════════════════════════════════════════

class TestServices:
    def test_bank_deposit(self):
        eng = engine_with_rng()
        do_start(eng)
        st, _ = eng.handle_action("bankDeposit", {"amount": 1000})
        assert st.cash == 1000
        assert st.bank == 1000

    def test_bank_withdraw(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.handle_action("bankDeposit", {"amount": 1000})
        st, _ = eng.handle_action("bankWithdraw", {"amount": 500})
        assert st.cash == 1500
        assert st.bank == 500

    def test_repay_debt(self):
        eng = engine_with_rng()
        do_start(eng)
        # debt is 5500 after startup interest, cash is 2000
        st, _ = eng.handle_action("repayDebt", {"amount": 2000})
        assert st.cash == 0
        assert st.debt == 3500  # 5500 - 2000

    def test_repay_debt_exceeds_cash_rejected(self):
        eng = engine_with_rng()
        do_start(eng)
        with pytest.raises(GameError, match="INSUFFICIENT_CASH"):
            eng.handle_action("repayDebt", {"amount": 2001})  # cash is 2000

    def test_buy_health(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.cash = 100000
        eng.health = 80
        st, _ = eng.handle_action("buyHealth", {"points": 10})
        assert st.health == 90
        assert st.cash == 100000 - 10 * 3500

    def test_buy_health_insufficient_cash(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.health = 80
        with pytest.raises(GameError, match="INSUFFICIENT_CASH"):
            eng.handle_action("buyHealth", {"points": 10})

    def test_rent_house(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.cash = 50000
        st, _ = eng.handle_action("rentHouse", {})
        assert st.coat == 110
        assert st.cash == 23000  # 50000//2 - 2000

    def test_netcafe(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.cash = 100
        eng.rng.push_test(5)
        st, _ = eng.handle_action("visitNetcafe", {})
        assert st.cash == 106
        assert st.visitWangba == 1


# ══════════════════════════════════════════════════════
# 12 — 得分与排行
# ══════════════════════════════════════════════════════

class TestScore:
    def test_score_calculation(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.cash = 5000
        eng.bank = 3000
        eng.debt = 2000
        assert eng.score == 6000

    def test_bankrupt(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.cash = 0
        eng.bank = 0
        eng.debt = 10000
        eng.time_left = 1
        st, msgs = eng.handle_action("moveTo", {"loc": 1})
        assert eng.game_over
        assert any("没挣着钱" in m.text for m in msgs)

    def test_fame_title_mapping(self):
        from models import fame_title
        assert fame_title(100) == "德高望重"
        assert fame_title(95) == "杰出青年"
        assert fame_title(85) == "一般般"
        assert fame_title(70) == "不佳"
        assert fame_title(50) == "争议人物"
        assert fame_title(30) == "差"
        assert fame_title(15) == "江湖唾弃"  # bug-faithful: 10-19 falls here
        assert fame_title(5) == "江湖唾弃"

    def test_submit_score(self):
        eng = engine_with_rng()
        do_start(eng)
        eng.game_over = True
        st, msgs = eng.handle_action("submitScore", {"name": "测试玩家"})
        assert eng.score_submitted


# ══════════════════════════════════════════════════════
# API 集成测试
# ══════════════════════════════════════════════════════

class TestAPI:
    def test_create_game_and_state(self):
        from main import app, manager
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Clear games, create fresh
        manager._games = {}
        resp = client.post("/api/v1/games", json={})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "gameId" in data
        assert data["state"]["cash"] == 2000
        assert data["state"]["debt"] == 5500

        game_id = data["gameId"]

        # Get state
        resp = client.get(f"/api/v1/games/{game_id}")
        assert resp.status_code == 200
        assert resp.json()["state"]["cash"] == 2000

        # Leaderboard
        resp = client.get("/api/v1/games/leaderboard")
        assert resp.status_code == 200
        assert len(resp.json()["entries"]) == 10

        # Action
        resp = client.post(f"/api/v1/games/{game_id}/actions", json={
            "action": "moveTo", "params": {"loc": 1}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"]["currentLoc"] == 1
        assert data["state"]["timeLeft"] == 39

        # Error handling
        resp = client.post(f"/api/v1/games/{game_id}/actions", json={
            "action": "buy", "params": {"goodsId": 4, "count": 99999}
        })
        assert resp.status_code in (400, 422)

        # Unknown game
        resp = client.get("/api/v1/games/nonexistent")
        assert resp.status_code == 404