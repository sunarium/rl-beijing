# language: zh-CN
# 来源: 迁移设计（后端=规则引擎+状态，前端=渲染+交互）
@boundary
功能: 前后端边界契约
  定义前后端迁移的结构性契约：状态所有权、命令接口、消息队列、RNG 契约与每日随机数消耗顺序。
  后端实现 01-12 的全部规则并持有全部状态；前端只负责渲染与输入。

  # ===== 状态所有权 =====

  @boundary @backend
  场景: 后端状态所有权
    # 来源: 详见 01/04/13（状态字段源自 SelectionDlg.h）
    那么 后端持有并负责以下全部数值状态（前端不持有任何持久游戏状态）:
      | 状态 | 说明 |
      | MyCash | 现金 |
      | MyDebt | 债务 |
      | MyBank | 存款 |
      | m_nMyHealth | 健康 |
      | m_MyFame | 名声 |
      | myCoat | 仓库容量 |
      | myTotal | 持仓总数 |
      | 持仓明细 | (商品,数量,加权均价) |
      | m_DrugPrice[8] | 8 种商品当日价格 |
      | m_nTimeLeft | 剩余天数 |
      | m_MyCurrentLoc | 当前地点 |
      | m_City | 地图标识(1/2) |
      | m_nVisitWangba | 网吧访问次数 |
      | m_bHackActs / m_bCloseSound | 设置开关 |
      | score.txt | 高分持久化 |

  @boundary @frontend
  场景: 前端渲染所有权
    # 来源: 详见 02/10/11/12（渲染相关条目）
    那么 前端负责地图/按钮文案、LED 数值显示、弹窗/日记/新闻渲染、音效播放、鼠标键盘输入捕获、老板遮挡画面、以及前十名的姓名输入
    而且 前端收到完整状态快照后整体渲染

  @boundary @backend
  场景: 消息队列契约
    # 来源: 各规则中的弹窗调用（CRijiDlg/CNewsDlg/AfxMessageBox）
    那么 后端不直接弹任何对话框
    而且 每个命令返回"状态快照 + 待显示消息列表"
    而且 消息分三类: 日记(CRijiDlg) / 新闻(CNewsDlg) / 确认框(AfxMessageBox)
    而且 前端负责把消息渲染为模态/非模态界面并回传用户选择（如确认/取消、输入金额、输入姓名）

  # ===== 命令接口 =====

  @boundary
  场景: 命令清单契约
    # 来源: 各 On* 处理器（见 01-12）
    那么 每个用户动作映射为一个后端命令，命令内处理顺序与 C++ 完全一致:
      | 命令 | 对应原版动作 | 备注 |
      | startGame | 新游戏 | 返回初始状态快照 |
      | toggleMap | 我要逛京城/进地铁 | 不触发日常事件 |
      | moveTo(loc) | 点击地点 | 触发完整日常序列，可能返回多条消息 |
      | buy(goodsId,count) | 买入 | |
      | sell(goodsId,count) | 卖出 | |
      | bankDeposit(n) / bankWithdraw(n) | 存/取款 | |
      | repayDebt(n) | 邮局还款 | |
      | buyHealth(points) | 医院治疗 | |
      | rentHouse() | 房屋中介 | |
      | visitNetcafe() | 网吧 | |
      | openBossShield() | 老板遮挡 | 纯前端 |
      | setup(hack,sound) | 游戏设置 | |
      | submitScore(name) | 前十名写入 | score.txt |

  @boundary
  场景: 状态快照契约
    # 来源: 03 的固定处理顺序
    那么 每个命令在完成全部内部处理后返回一次完整状态快照
    而且 顺序保证与 C++ 处理器中的处理顺序一致（见 03 的固定顺序）

  # ===== RNG 契约 =====

  @boundary
  场景: 随机数抽取契约
    # 来源: SelectionDlg.cpp:94-105（RandomNum）
    那么 后端把所有随机数收敛到单一可注入函数 random(upper)（返回 [0, upper) 整数）
    而且 为测试提供钩子 nextRandom(v)：压入下一个返回值
    而且 任何场景只要通过钩子给出确定抽取序列，即可完整复现对应的一天/动作

  @boundary @verified
  场景: 每日随机数消耗顺序（可逐位重放）
    # 来源: SelectionDlg.cpp HandleNormalEvents / DoRandomStuff / DoRandomEvent / OnSteal
    那么 一次移动日的随机数消耗严格按以下顺序进行:
      | 步骤 | 消耗 | 说明 |
      | ① 价格生成 | 8 × RandomNum(区间) + 3 × RandomNum(8) | 每个商品一个偏移；若 last2天 不做剔除则无 ×RandomNum(8) |
      | ② 商业事件 | 至多 18 × RandomNum(950) | 目标价 0 时跳过却仍消耗；房间满提早 return 会中断后续抽取 |
      | ③ 健康事件 | 至多 12 × RandomNum(1000) | 命中即 break；强制住院额外消耗 RandomNum(2)、RandomNum(8500)、RandomNum(29) |
      | ④ 偷钱事件 | 至多 7 × RandomNum(1000) | 命中即 break |
      | ⑤ 黑客事件 | RandomNum(1000) 触发 + RandomNum(20)/RandomNum(15) 选 num + RandomNum(20) 判加减 | 仅当设置开启且触发 |
      | ⑥ 网吧 | RandomNum(10) | 仅当访问网吧 |
    而且 各随机用途的区间参见 04/07/08/09/11

  @boundary
  场景: 地点编号契约
    # 来源: SelectionDlg.cpp:1556-1574（loc[]）
    那么 后端用 1-10 表示当前黑市位置，且住院文案的名称为 loc[10×(m_City−1)+当前地点−1]
    而且 前端用同一编号渲染对应按钮（名称见 02）
