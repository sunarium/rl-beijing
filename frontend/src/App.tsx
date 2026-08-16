import { useState, useCallback, useEffect } from 'react';
import { createGame, postAction, getGame, ApiError } from './api';
import { StatusBar } from './components/StatusBar';
import { MapView } from './components/MapView';
import { MarketView } from './components/MarketView';
import { EventFeed } from './components/EventFeed';
import { ServicePanel } from './components/ServicePanel';
import type { GameState, Message } from './types';
import './App.css';

// Boss shield state
const BOSS_KEY = 'b';

function App() {
  const [gameId, setGameId] = useState<string | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [gameOver, setGameOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [bossMode, setBossMode] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Boss shield keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === BOSS_KEY) {
        e.preventDefault();
        setBossMode(prev => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const startNewGame = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await createGame();
      setGameId(data.gameId);
      setState(data.state);
      setMessages(data.messages);
      setGameOver(data.gameOver);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : '创建游戏失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAction = useCallback(async (action: string, params: Record<string, unknown> = {}) => {
    if (!gameId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await postAction(gameId, action, params);
      setState(data.state);
      setMessages(prev => [...prev, ...data.messages]);
      setGameOver(data.gameOver);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : '操作失败';
      // Add error as diary entry for visibility
      setMessages(prev => [...prev, {
        id: `err-${Date.now()}`,
        type: 'diary',
        category: 'error',
        text: msg,
        data: {},
      }]);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [gameId]);

  return (
    <div className={`app ${bossMode ? 'boss-mode' : ''}`}>
      {bossMode && (
        <div className="boss-overlay">
          <div className="boss-content">
            <h1>📋 北京经济技术开发区 — 2024年度工作总结报告</h1>
            <p>尊敬的领导：</p>
            <p>在过去的一年中，北京经济技术开发区坚决贯彻落实党中央、国务院决策部署……</p>
            <p style={{ marginTop: '2rem', color: '#666', fontSize: '0.8rem' }}>
              按 Ctrl+B 返回游戏
            </p>
          </div>
        </div>
      )}

      {!bossMode && (
        <>
          <header className="app-header">
            <h1>北京浮生记</h1>
            {!gameId && (
              <button className="start-btn" onClick={startNewGame} disabled={loading}>
                {loading ? '加载中...' : '🎮 新游戏'}
              </button>
            )}
          </header>

          {error && <div className="global-error">{error}</div>}

          {state && (
            <>
              <StatusBar state={state} />

              <div className="game-layout">
                <div className="left-panel">
                  <MapView
                    state={state}
                    onMoveTo={loc => handleAction('moveTo', { loc })}
                    onToggleMap={() => handleAction('toggleMap')}
                  />
                  <MarketView
                    state={state}
                    onBuy={(goodsId, count) => handleAction('buy', { goodsId, count })}
                    onSell={(goodsId, count) => handleAction('sell', { goodsId, count })}
                  />
                </div>

                <div className="right-panel">
                  <ServicePanel
                    state={state}
                    gameId={gameId!}
                    onBankDeposit={amount => handleAction('bankDeposit', { amount })}
                    onBankWithdraw={amount => handleAction('bankWithdraw', { amount })}
                    onRepayDebt={amount => handleAction('repayDebt', { amount })}
                    onBuyHealth={points => handleAction('buyHealth', { points })}
                    onRentHouse={() => handleAction('rentHouse')}
                    onNetcafe={() => handleAction('visitNetcafe')}
                    onSetup={(hack, sound) => handleAction('setup', { hackActs: hack, closeSound: sound })}
                    onSubmitScore={name => handleAction('submitScore', { name })}
                  />
                  <EventFeed
                    messages={messages}
                    onClear={() => setMessages([])}
                  />
                </div>
              </div>

              {gameOver && (
                <div className="game-over-banner">
                  <span>🎬 游戏结束！得分: {state.score.toLocaleString()}</span>
                  <button onClick={startNewGame}>再来一局</button>
                </div>
              )}
            </>
          )}

          {!state && !loading && (
            <div className="welcome">
              <p>欢迎来到北京浮生记！</p>
              <p>在 40 天内通过黑市买卖赚取财富，还清债务，成为富豪！</p>
              <p className="hint">支持鼠标操作 · Ctrl+B 老板键 · 可在 Service Panel 查看排行</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default App;