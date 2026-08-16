# language: zh-CN
# 来源: SelectionDlg.cpp OnAdd / MoveListItems
@backend @rule-engine
功能: 买卖交易
  买入与卖出、同类货物合并的加权均价、以及卖出对名声的影响。
  卖出价格一律使用"当前所在地点的当前黑市价"，而不是买入时的价格。

  背景:
    假如 游戏进行中、存在黑市与仓库
    # 来源: SelectionDlg.cpp:650

  # ===== 买入 =====

  @verified
  场景: 未选中商品提示
    # 来源: SelectionDlg.cpp:668-675
    当 未选中任何黑市商品直接购买
    那么 弹日记「我还没有选定买什么物品呢。」

  @verified
  场景: 现金不足提示
    # 来源: SelectionDlg.cpp:678-691
    假如 我的现金 < 单选商品单价
    当 购买
    那么 若银行有存款，弹「俺带的现金不够，去银行提点钱吧。」
    而且 若银行无存款，弹「俺的现金不够，银行又没有存款，咋办哩?」

  @verified
  场景: 最大可买数计算
    # 来源: SelectionDlg.cpp:693-697
    当 购买单价为 price 的商品
    那么 最大可买数 = min(仓库剩余容量 myCoat−myTotal, 现金整除 price)
    而且 其中 现金整除 price 使用整数除法向下取整

  @verified
  场景: 购买成功扣款与入库
    # 来源: SelectionDlg.cpp:708-712
    当 确认购买 count 个
    那么 现金减 price×count
    而且 持仓总数 myTotal 加 count（且被钳制不超过 myCoat）
    而且 货物移入仓库列表

  @verified
  场景: 同类商品合并采用加权平均价
    # 来源: SelectionDlg.cpp:802
    假如 仓库已有同一种商品、均价 oldPrice、数量 oldCount
    当 以 price 买入 count 个并合并
    那么 合并后均价 = (price×count + oldPrice×oldCount) 整除 (count+oldCount)
    而且 使用整数除法（截断）

  @verified
  场景: 仓库满时禁止购买
    # 来源: SelectionDlg.cpp:693
    假如 myTotal 等于 myCoat
    那么 最大可买数 = min(0, 现金整除 price) = 0
    而且 无法继续购入

  # ===== 卖出 =====

  @verified
  场景: 卖出按当前地点当前黑市价结算
    # 来源: SelectionDlg.cpp:869
    当 在当前地点卖出 count 个商品
    那么 现金 += count × 当前地点当前黑市单价
    而且 持仓总数 myTotal 减 count

  @verified
  场景: 卖出非在售商品被禁止
    # 来源: SelectionDlg.cpp:943-945
    假如 该商品在当前地点的价格被置 0（不在售）
    当 尝试卖出
    那么 弹日记「哦？仿佛没有人在这里做<商品名>生意。」
    而且 卖出被禁止

  @verified
  场景: 免费商品按当前黑市价卖出
    # 来源: SelectionDlg.cpp:824-869
    假如 仓库有通过事件免费获得的商品（买入价记为 0）
    当 卖出
    那么 仍按当前地点当前黑市价结算（与买入价无关）

  @verified
  场景: 卖出禁书扣 7 点名声
    # 来源: SelectionDlg.cpp:883-905
    当 卖出《上海小宝贝》（禁书）每 1 单位
    那么 名声减 7
    而且 首次卖出时弹「买卖《上海小宝贝》（禁书）,污染社会,俺的名声变坏了啊!」
    而且 名声低于 60 时以红字显示
    而且 名声下限为 0

  @verified
  场景: 卖出假酒扣 10 点名声
    # 来源: SelectionDlg.cpp:904-930
    当 卖出假白酒（剧毒！）每 1 单位
    那么 名声减 10
    而且 首次卖出时弹「买卖假白酒（剧毒！）,危害社会，俺的名声下降了.」
    而且 名声下限为 0

  @verified
  场景: 全部卖光后删除仓库条目
    # 来源: SelectionDlg.cpp:883-887
    当 卖出后该商品数量为 0
    那么 从仓库列表中删除该条目
