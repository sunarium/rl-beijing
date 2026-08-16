import type { GameState } from '../types';

interface Props {
  state: GameState;
}

const fameColor = (fame: number) => (fame < 60 ? '#ff4444' : '#ffffff');
const healthColor = (health: number) =>
  health <= 0 ? '#ff0000' : health < 20 ? '#ff6600' : health < 60 ? '#ffaa00' : '#00ff00';

export function StatusBar({ state }: Props) {
  return (
    <div className="status-bar">
      <div className="stat">
        <span className="label">💰 现金</span>
        <span className="value">{state.cash.toLocaleString()}</span>
      </div>
      <div className="stat">
        <span className="label">🏦 存款</span>
        <span className="value">{state.bank.toLocaleString()}</span>
      </div>
      <div className="stat debt">
        <span className="label">⚠️ 债务</span>
        <span className="value">{state.debt.toLocaleString()}</span>
      </div>
      <div className="stat">
        <span className="label">❤️ 健康</span>
        <span className="value" style={{ color: healthColor(state.health) }}>
          {state.health}/{state.healthMax}
        </span>
      </div>
      <div className="stat">
        <span className="label">🏅 名声</span>
        <span className="value" style={{ color: fameColor(state.fame) }}>
          {state.fame}
        </span>
      </div>
      <div className="stat">
        <span className="label">📦 容量</span>
        <span className="value">{state.total}/{state.coat}</span>
      </div>
      <div className="stat">
        <span className="label">📅 剩余</span>
        <span className="value">{state.timeLeft}/40 天</span>
      </div>
      <div className="stat score">
        <span className="label">🏆 得分</span>
        <span className="value">{state.score.toLocaleString()}</span>
      </div>
    </div>
  );
}