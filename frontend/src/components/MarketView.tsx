import { useState } from 'react';
import type { GameState } from '../types';
import { ApiError } from '../api';

const GOODS_NAMES = [
  "进口香烟", "走私汽车", "盗版VCD、游戏", "假白酒（剧毒！）",
  "《上海小宝贝》（禁书）", "进口玩具", "水货手机", "伪劣化妆品",
];

interface Props {
  state: GameState;
  onBuy: (goodsId: number, count: number) => Promise<void>;
  onSell: (goodsId: number, count: number) => Promise<void>;
}

export function MarketView({ state, onBuy, onSell }: Props) {
  const [quantities, setQuantities] = useState<Record<number, number>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<number | null>(null);

  const handleAction = async (fn: () => Promise<void>) => {
    setError(null);
    try {
      await fn();
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError('操作失败');
      }
    }
  };

  return (
    <div className="market-view">
      <h3>📊 黑市交易</h3>
      {error && <div className="error-msg">{error}</div>}
      <table>
        <thead>
          <tr>
            <th>商品</th>
            <th>价格</th>
            <th>持仓</th>
            <th>均价</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {GOODS_NAMES.map((name, i) => {
            const price = state.prices[i];
            const holding = state.holdings[i];
            const qty = quantities[i] || 1;

            return (
              <tr key={i} className={price <= 0 ? 'not-on-sale' : ''}>
                <td>{name}</td>
                <td className="price">
                  {price > 0 ? price.toLocaleString() : '—'}
                </td>
                <td>{holding.count > 0 ? holding.count : '—'}</td>
                <td>{holding.count > 0 ? holding.avgPrice.toLocaleString() : '—'}</td>
                <td>
                  {price > 0 && (
                    <div className="trade-controls">
                      <input
                        type="number"
                        min={1}
                        max={999}
                        value={qty}
                        onChange={e => setQuantities({ ...quantities, [i]: Math.max(1, parseInt(e.target.value) || 1) })}
                        className="qty-input"
                      />
                      <button
                        className="buy-btn"
                        disabled={loading === i}
                        onClick={() => {
                          setLoading(i);
                          handleAction(() => onBuy(i, qty)).finally(() => setLoading(null));
                        }}
                      >
                        买入
                      </button>
                      {holding.count > 0 && (
                        <button
                          className="sell-btn"
                          disabled={loading === i}
                          onClick={() => {
                            setLoading(i);
                            handleAction(() => onSell(i, qty)).finally(() => setLoading(null));
                          }}
                        >
                          卖出
                        </button>
                      )}
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}