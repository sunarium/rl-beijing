# language: zh-CN
# 来源: SelectionDlg.cpp makeDrugPrices / RandomNum
@backend @rule-engine
功能: 市场与价格
  黑市每天重新生成 8 种商品的价格。每种价格 = 基础价 + 均匀随机偏移。
  随机语义：`RandomNum(upper)` 返回 `[0, upper)` 内的整数（`rand() % upper`）。每格价格的最小值 = 基础价，最大值 = 基础价 + upper - 1。
  剔除语义：正常每天把 3 个商品的价置 0（不可交易）；最后 2 天全部 8 种在售。

  背景:
    假如 系统按天重新生成价格
    # 来源: SelectionDlg.cpp:1187

  # ===== 随机数函数契约 =====

  @verified
  场景: 随机数函数契约
    # 来源: SelectionDlg.cpp:94-105
    那么 RandomNum(upper) 返回 [0, upper) 的整数
    而且 全局只以 time(NULL) 播种 rand() 一次
    而且 后端所有随机数统一经可注入函数 random(upper) 产出（见 13_前后端边界契约）

  # ===== 八种商品价格 =====

  @verified
  场景大纲: 八种商品价格公式与区间
    # 来源: SelectionDlg.cpp:1191-1198
    当 重新生成价格
    那么 商品 <名称> 的价格 = <公式>，落在 [<下限>, <上限>]

    例子:
      | id | 名称 | 公式 | 下限 | 上限 |
      | 0 | 进口香烟 | 100 + RandomNum(350) | 100 | 449 |
      | 1 | 走私汽车 | 15000 + RandomNum(15000) | 15000 | 29999 |
      | 2 | 盗版VCD、游戏 | 5 + RandomNum(50) | 5 | 54 |
      | 3 | 假白酒（剧毒！） | 1000 + RandomNum(2500) | 1000 | 3499 |
      | 4 | 《上海小宝贝》（禁书） | 5000 + RandomNum(9000) | 5000 | 13999 |
      | 5 | 进口玩具 | 250 + RandomNum(600) | 250 | 849 |
      | 6 | 水货手机 | 750 + RandomNum(750) | 750 | 1499 |
      | 7 | 伪劣化妆品 | 65 + RandomNum(180) | 65 | 244 |

  # ===== 剔除与在售 =====

  @verified
  场景: 正常日期生成 5 种在售商品
    # 来源: SelectionDlg.cpp:1200-1205
    当 处于正常日期（剩余天数大于 2）
    那么 连续 3 次 RandomNum(8) 命中的商品价被置 0
    而且 同一商品可被重复命中（命中后仍可能再次归零）
    而且 在售商品 = 价格非 0 的商品，正常为 5 种

  @verified
  场景: 最后两天生成全部 8 种商品
    # 来源: SelectionDlg.cpp:1452-1457
    假如 剩余天数 m_nTimeLeft 小于等于 2
    当 生成价格
    那么 不做剔除，8 种商品全部在售

  @verified
  场景: 黑市列表只展示在售商品
    # 来源: DisplayDrugs
    那么 黑市列表只列出价格非 0 的商品
    而且 列表按商品 id 升序排列
