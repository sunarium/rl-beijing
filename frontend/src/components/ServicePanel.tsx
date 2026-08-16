import { useState } from 'react';
import type { GameState } from '../types';
import { ApiError } from '../api';
import { getLeaderboard, type LeaderboardEntry } from '../api';

const GOOGLE_PLAY = "https://play.google.com/store/apps/details?id=com.google.android.apps.plus";

interface Props {
  state: GameState;
  gameId: string;
  onBankDeposit: (amount: number) => Promise<void>;
  onBankWithdraw: (amount: number) => Promise<void>;
  onRepayDebt: (amount: number) => Promise<void>;
  onBuyHealth: (points: number) => Promise<void>;
  onRentHouse: () => Promise<void>;
  onNetcafe: () => Promise<void>;
  onSetup: (hack: boolean, sound: boolean) => Promise<void>;
  onSubmitScore: (name: string) => Promise<void>;
}

export function ServicePanel({
  state, gameId, onBankDeposit, onBankWithdraw,
  onRepayDebt, onBuyHealth, onRentHouse, onNetcafe,
  onSetup, onSubmitScore,
}: Props) {
  const [tab, setTab] = useState<string>('bank');
  const [amount, setAmount] = useState(100);
  const [healthPoints, setHealthPoints] = useState(1);
  const [submitName, setSubmitName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[] | null>(null);
  const [showLeaderboard, setShowLeaderboard] = useState(false);

  const handleAction = async (fn: () => Promise<void>) => {
    setError(null);
    try { await fn(); } catch (e) {
      setError(e instanceof ApiError ? e.message : '操作失败');
    }
  };

  const loadLeaderboard = async () => {
    setShowLeaderboard(!showLeaderboard);
    if (!showLeaderboard) {
      const resp = await getLeaderboard();
      setLeaderboard(resp.entries);
    }
  };

  return (
    <div className="service-panel">
      <div className="service-tabs">
        <button className={tab === 'bank' ? 'active' : ''} onClick={() => setTab('bank')}>🏦 银行</button>
        <button className={tab === 'post' ? 'active' : ''} onClick={() => setTab('post')}>📮 邮局</button>
        <button className={tab === 'hospital' ? 'active' : ''} onClick={() => setTab('hospital')}>🏥 医院</button>
        <button className={tab === 'house' ? 'active' : ''} onClick={() => setTab('house')}>🏠 中介</button>
        <button className={tab === 'netcafe' ? 'active' : ''} onClick={() => setTab('netcafe')}>💻 网吧</button>
        <button className={tab === 'settings' ? 'active' : ''} onClick={() => setTab('settings')}>⚙️ 设置</button>
        <button className={tab === 'score' ? 'active' : ''} onClick={() => setTab('score')}>🏆 排行</button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      <div className="service-content">
        {tab === 'bank' && (
          <div>
            <p>现金: {state.cash.toLocaleString()} | 存款: {state.bank.toLocaleString()}</p>
            <input type="number" min={1} max={state.cash} value={amount} onChange={e => setAmount(Math.max(1, parseInt(e.target.value) || 1))} />
            <button onClick={() => handleAction(() => onBankDeposit(amount))}>存款</button>
            <input type="number" min={1} max={state.bank} value={amount} onChange={e => setAmount(Math.max(1, parseInt(e.target.value) || 1))} />
            <button onClick={() => handleAction(() => onBankWithdraw(amount))}>取款</button>
          </div>
        )}

        {tab === 'post' && (
          <div>
            <p>债务: {state.debt.toLocaleString()} | 现金: {state.cash.toLocaleString()}</p>
            <input type="number" min={1} max={state.cash} value={amount} onChange={e => setAmount(Math.max(1, parseInt(e.target.value) || 1))} />
            <button onClick={() => handleAction(() => onRepayDebt(amount))}>还款</button>
          </div>
        )}

        {tab === 'hospital' && (
          <div>
            <p>健康: {state.health}/{state.healthMax} | 每点 3500 元</p>
            <input type="number" min={1} max={100 - state.health} value={healthPoints} onChange={e => setHealthPoints(Math.max(1, parseInt(e.target.value) || 1))} />
            <button onClick={() => handleAction(() => onBuyHealth(healthPoints))}>
              治疗 ({healthPoints * 3500} 元)
            </button>
          </div>
        )}

        {tab === 'house' && (
          <div>
            <p>当前容量: {state.coat}/{state.coatMax}</p>
            <button onClick={() => handleAction(onRentHouse)}>租房子 (+10 容量)</button>
          </div>
        )}

        {tab === 'netcafe' && (
          <div>
            <p>已访问: {state.visitWangba}/3 次</p>
            <button onClick={() => handleAction(onNetcafe)} disabled={state.visitWangba >= 3}>
              去网吧
            </button>
          </div>
        )}

        {tab === 'settings' && (
          <div>
            <label>
              <input type="checkbox" checked={state.settings.hackActs} onChange={e => handleAction(() => onSetup(e.target.checked, state.settings.closeSound))} />
              黑客事件
            </label>
            <label>
              <input type="checkbox" checked={state.settings.closeSound} onChange={e => handleAction(() => onSetup(state.settings.hackActs, e.target.checked))} />
              关闭声音
            </label>
            <p className="hint">老板遮挡快捷键: <kbd>Ctrl+B</kbd></p>
          </div>
        )}

        {tab === 'score' && (
          <div>
            <button onClick={loadLeaderboard}>
              {showLeaderboard ? '收起' : '查看排行'}
            </button>
            {state.gameOver && (
              <div className="submit-score">
                <p>得分: {state.score.toLocaleString()}</p>
                <input type="text" placeholder="输入姓名" value={submitName} onChange={e => setSubmitName(e.target.value)} />
                <button onClick={() => handleAction(() => onSubmitScore(submitName || '无名氏'))}>提交高分</button>
              </div>
            )}
            {showLeaderboard && leaderboard && (
              <table className="leaderboard">
                <thead>
                  <tr><th>#</th><th>姓名</th><th>得分</th><th>健康</th><th>称号</th></tr>
                </thead>
                <tbody>
                  {leaderboard.map(e => (
                    <tr key={e.rank}>
                      <td>{e.rank}</td>
                      <td>{e.name}</td>
                      <td>{e.score.toLocaleString()}</td>
                      <td>{e.health}</td>
                      <td>{e.title}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}