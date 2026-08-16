"""
Pydantic 模型 — 请求/响应契约。
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


# ── 商品常量 ─────────────────────────────────────────────

GOODS = [
    {"id": 0, "name": "进口香烟", "base": 100, "range": 350},
    {"id": 1, "name": "走私汽车", "base": 15000, "range": 15000},
    {"id": 2, "name": "盗版VCD、游戏", "base": 5, "range": 50},
    {"id": 3, "name": "假白酒（剧毒！）", "base": 1000, "range": 2500},
    {"id": 4, "name": "《上海小宝贝》（禁书）", "base": 5000, "range": 9000},
    {"id": 5, "name": "进口玩具", "base": 250, "range": 600},
    {"id": 6, "name": "水货手机", "base": 750, "range": 750},
    {"id": 7, "name": "伪劣化妆品", "base": 65, "range": 180},
]

GOODS_NAMES = [g["name"] for g in GOODS]


# ── 商业事件登记表（18 条） ────────────────────────────────

BUSINESS_EVENTS = [
    {"id": 0, "freq": 170, "drug": 5, "plus": 2, "minus": 0, "add": 0, "msg": "专家提议提高大学生\"动手素质\"，进口玩具颇受欢迎!"},
    {"id": 1, "freq": 139, "drug": 3, "plus": 3, "minus": 0, "add": 0, "msg": "有人自豪地说：生病不用打针吃药，喝假白酒（剧毒）就可以!"},
    {"id": 2, "freq": 100, "drug": 4, "plus": 5, "minus": 0, "add": 0, "msg": "医院的秘密报告：\"《上海小宝贝》功效甚过伟哥\"!"},
    {"id": 3, "freq": 41, "drug": 2, "plus": 4, "minus": 0, "add": 0, "msg": "文盲说：\"2000年诺贝尔文学奖？呸！不如盗版VCD港台片。\""},
    {"id": 4, "freq": 37, "drug": 1, "plus": 3, "minus": 0, "add": 0, "msg": "《北京经济小报》社论：\"走私汽车大力推进汽车消费!\""},
    {"id": 5, "freq": 23, "drug": 7, "plus": 4, "minus": 0, "add": 0, "msg": "《北京真理报》社论：\"提倡爱美，落到实处\"，伪劣化妆品大受欢迎!"},
    {"id": 6, "freq": 37, "drug": 4, "plus": 8, "minus": 0, "add": 0, "msg": "8858.com电子书店也不敢卖《上海小宝贝》，黑市一册可卖天价!"},
    {"id": 7, "freq": 15, "drug": 7, "plus": 7, "minus": 0, "add": 0, "msg": "谢不疯在晚会上说：\"我酷!我使用伪劣化妆品!\"，伪劣化妆品供不应求!"},
    {"id": 8, "freq": 40, "drug": 3, "plus": 7, "minus": 0, "add": 0, "msg": "北京有人狂饮山西假酒，可以卖出天价!"},
    {"id": 9, "freq": 29, "drug": 6, "plus": 7, "minus": 0, "add": 0, "msg": "北京的大学生们开始找工作，水货手机大受欢迎！！!"},
    {"id": 10, "freq": 35, "drug": 1, "plus": 8, "minus": 0, "add": 0, "msg": "北京的富人疯狂地购买走私汽车！价格狂升!"},
    {"id": 11, "freq": 17, "drug": 0, "plus": 0, "minus": 8, "add": 0, "msg": "市场上充斥着来自福建的走私香烟!"},
    {"id": 12, "freq": 24, "drug": 5, "plus": 0, "minus": 5, "add": 0, "msg": "北京的孩子们都忙于上网学习，进口玩具没人愿意买。"},
    {"id": 13, "freq": 18, "drug": 2, "plus": 0, "minus": 8, "add": 0, "msg": "盗版业十分兴旺，\"中国硅谷\"——中关村全是卖盗版VCD的村姑!"},
    {"id": 14, "freq": 160, "drug": 1, "plus": 0, "minus": 0, "add": 2, "msg": "厦门的老同学资助俺两部走私汽车！发了！！"},
    {"id": 15, "freq": 45, "drug": 0, "plus": 0, "minus": 0, "add": 6, "msg": "工商局扫荡后，俺在黑暗角落里发现了老乡丢失的进口香烟。"},
    {"id": 16, "freq": 35, "drug": 3, "plus": 0, "minus": 0, "add": 4, "msg": "俺老乡回家前把一些山西假白酒（剧毒）给俺!"},
    {"id": 17, "freq": 140, "drug": 6, "plus": 0, "minus": 0, "add": 1, "msg": "媒体报道：又有日本出口到中国的产品出事了! 出事后日本人死不认帐,拒绝赔偿。村长得知此消息，托人把他用的水货手机（无任何厂商标识）硬卖给您，收您2500元。"},
]


# ── 健康事件登记表（12 条） ────────────────────────────────

HEALTH_EVENTS = [
    {"id": 0, "freq": 117, "hunt": 3, "msg": "大街上两个流氓打了俺!", "sound": "kill.wav"},
    {"id": 1, "freq": 157, "hunt": 20, "msg": "俺在过街地道被人打了蒙棍!", "sound": "death.wav"},
    {"id": 2, "freq": 21, "hunt": 1, "msg": "工商局的追俺超过三个胡同。", "sound": "dog.wav"},
    {"id": 3, "freq": 100, "hunt": 1, "msg": "北京拥挤的交通让俺心焦!", "sound": "harley.wav"},
    {"id": 4, "freq": 35, "hunt": 1, "msg": "开小巴的打俺一耳光!", "sound": "hit.wav"},
    {"id": 5, "freq": 313, "hunt": 10, "msg": "一群民工打了俺!", "sound": "flee.wav"},
    {"id": 6, "freq": 120, "hunt": 5, "msg": "附近胡同的一个小青年砸俺一砖头!", "sound": "death.wav"},
    {"id": 7, "freq": 29, "hunt": 3, "msg": "附近写字楼一个假保安用电棍电击俺!", "sound": "el.wav"},
    {"id": 8, "freq": 43, "hunt": 1, "msg": "北京臭黑的小河熏着我了!", "sound": "vomit.wav"},
    {"id": 9, "freq": 45, "hunt": 1, "msg": "守自行车的王大婶嘲笑俺没北京户口!", "sound": "level.wav"},
    {"id": 10, "freq": 48, "hunt": 1, "msg": "北京高温40度!俺热...", "sound": "lan.wav"},
    {"id": 11, "freq": 33, "hunt": 1, "msg": "申奥添了新风景，北京又来沙尘暴!", "sound": "breath.wav"},
]

# 住院地点细节数组 coffee[30]
COFFEE_DETAILS = [
    "发廊里", "早点摊上", "报摊上", "烤羊肉摊上", "公共汽车里",
    "人力车上", "女厕所里", "男厕所里", "电话亭里", "三陪女怀里",
    "出租车里", "小巴里", "美容院里", "小商亭里", "小商场门口",
    "民工脚下", "无照游商摊里", "草地上", "电线杆顶端", "小饭馆里",
    "马路边", "人行道上", "街心公园里", "广告牌下", "公共汽车站里",
    "长途汽车站里", "卖盗版游戏的旁边", "网络公司尸体旁边", "行骗的知本家旁边", "",
]


# ── 偷钱事件登记表（7 条） ────────────────────────────────

THEFT_EVENTS = [
    {"id": 0, "freq": 60, "target": "cash", "ratoi": 10, "msg": "俺怜悯地铁口扮演成乞丐的老太太。"},
    {"id": 1, "freq": 125, "target": "cash", "ratoi": 10, "msg": "一个汉子在街头拦住俺：“哥们，给点钱用!”。"},
    {"id": 2, "freq": 100, "target": "cash", "ratoi": 40, "msg": "一个大个子碰了俺一下，说：“别挤了!”。"},
    {"id": 3, "freq": 65, "target": "cash", "ratoi": 20, "msg": "三个带红袖章的老太太揪住俺：“你是外地人?罚款!”"},
    {"id": 4, "freq": 35, "target": "bank", "ratoi": 15, "msg": "两个猛男揪住俺：“交长话附加费、上网费。”"},
    {"id": 5, "freq": 27, "target": "bank", "ratoi": 10, "msg": "副主任说：“办经商证?晚上不要去我家给我送钱哦。”"},
    {"id": 6, "freq": 40, "target": "cash", "ratoi": 5, "msg": "北京空气污染得厉害,俺去氧吧吸氧..."},
]


# ── 称号映射 ──────────────────────────────────────────────

FAME_TITLES = [
    (100, 999, "德高望重"),
    (90, 99, "杰出青年"),
    (80, 89, "一般般"),
    (60, 79, "不佳"),
    (40, 59, "争议人物"),
    (20, 39, "差"),
    (10, 19, "江湖唾弃"),  # 原版缺陷: 10-19 因死分支实际落于此
    (0, 9, "江湖唾弃"),
]


def fame_title(fame: int) -> str:
    for lo, hi, title in FAME_TITLES:
        if lo <= fame <= hi:
            return title
    return "江湖唾弃"


# ── 地点名称 ──────────────────────────────────────────────

# loc[] 数组：前 10 = 地铁模式，后 10 = 地面模式，索引 20 = ""
LOC_NAMES = [
    # 地铁 (city=1), 索引 0-9
    "建国门", "北京站", "西直门", "崇文门", "东直门",
    "复兴门", "积水潭", "长椿街", "公主坟", "苹果园",
    # 地面 (city=2), 索引 10-19
    "永安里", "方 庄", "海淀大街", "永定门", "三元东桥",
    "文津街", "北辰西路", "菜户营", "翠微路", "八角地铁",
    # 索引 20
    "",
]

# 地图按钮名称（与 loc[] 数组不一致——原版缺陷）
MAP_BUTTON_NAMES = {
    # city=1 地铁
    1: ["西直门", "复兴门", "积水潭", "东直门", "建国门",
        "北京站", "崇文门", "长椿街", "公主坟", "苹果园"],
    # city=2 地面
    2: ["海淀大街", "府右街", "亚运村", "三元西桥", "永安里",
        "方 庄", "永定门", "玉泉营", "翠微路", "八角西路"],
}

MAP_TITLES = {1: "北京市地铁示意图", 2: "北京市地面示意图"}
MAP_TOGGLE_TEXT = {1: "\"我要逛京城\"", 2: "\"我要进地铁\""}

# 默认高分表（score.txt 缺失时使用）
DEFAULT_LEADERBOARD = [
    {"rank": 1, "name": "赖皮张", "score": 12500720, "health": 98, "title": "争议人物"},
    {"rank": 2, "name": "萧峰", "score": 830050, "health": 100, "title": "杰出青年"},
    {"rank": 3, "name": "二黑", "score": 500447, "health": 78, "title": "德高望重"},
    {"rank": 4, "name": "Andy Rocky", "score": 239403, "health": 97, "title": "很差"},
    {"rank": 5, "name": "li xing", "score": 34900, "health": 35, "title": "江湖唾弃"},
    {"rank": 6, "name": "li xing", "score": 13400, "health": 100, "title": "江湖唾弃"},
    {"rank": 7, "name": "li", "score": 2300, "health": 77, "title": "不佳"},
    {"rank": 8, "name": "li", "score": 45, "health": 12, "title": "杰出青年"},
    {"rank": 9, "name": "li", "score": 34, "health": 100, "title": "一般般"},
    {"rank": 10, "name": "li", "score": 3, "health": 100, "title": "杰出青年"},
]


# ── API 模型 ──────────────────────────────────────────────


class CreateGameRequest(BaseModel):
    agentName: Optional[str] = None
    seed: Optional[int] = None


class ActionRequest(BaseModel):
    action: str = Field(..., description="动作名: startGame|toggleMap|moveTo|buy|sell|bankDeposit|bankWithdraw|repayDebt|buyHealth|rentHouse|visitNetcafe|openBossShield|setup|submitScore")
    params: dict = Field(default_factory=dict, description="动作参数")


class HoldingItem(BaseModel):
    goodsId: int
    name: str
    count: int
    avgPrice: int


class GameSettings(BaseModel):
    hackActs: bool = False
    closeSound: bool = False


class GameState(BaseModel):
    cash: int
    debt: int
    bank: int
    health: int
    healthMax: int = 100
    fame: int
    fameMin: int = 0
    fameMax: int = 100
    coat: int
    coatMax: int = 140
    total: int
    holdings: list[HoldingItem]
    prices: list[int]
    timeLeft: int
    currentLoc: int | None
    city: int
    cityName: str
    visitWangba: int
    settings: GameSettings
    score: int


class Message(BaseModel):
    id: str
    type: Literal["diary", "news"]
    category: str
    text: str
    data: dict = Field(default_factory=dict)


class ActionResponse(BaseModel):
    gameId: str
    state: GameState
    messages: list[Message]
    gameOver: bool
    action: str
    params: dict


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    score: int
    health: int
    title: str


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
    total: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    params: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail