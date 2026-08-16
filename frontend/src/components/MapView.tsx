import type { GameState } from '../types';

// Button names (bug-faithful: differ from loc[] array)
const MAP_BUTTONS: Record<number, string[]> = {
  1: ["西直门", "复兴门", "积水潭", "东直门", "建国门",
     "北京站", "崇文门", "长椿街", "公主坟", "苹果园"],
  2: ["海淀大街", "府右街", "亚运村", "三元西桥", "永安里",
     "方 庄", "永定门", "玉泉营", "翠微路", "八角西路"],
};

interface Props {
  state: GameState;
  onMoveTo: (loc: number) => void;
  onToggleMap: () => void;
}

export function MapView({ state, onMoveTo, onToggleMap }: Props) {
  const buttons = MAP_BUTTONS[state.city] || MAP_BUTTONS[1];
  const title = state.cityName;

  return (
    <div className="map-view">
      <div className="map-header">
        <h3>{title}</h3>
        <button className="toggle-btn" onClick={onToggleMap}>
          {state.city === 1 ? "我要逛京城" : "我要进地铁"}
        </button>
      </div>
      <div className="map-grid">
        {buttons.map((name, idx) => {
          const locNum = idx + 1;
          const isCurrent = state.currentLoc === locNum;
          return (
            <button
              key={locNum}
              className={`loc-btn ${isCurrent ? 'current' : ''}`}
              onClick={() => onMoveTo(locNum)}
              disabled={state.timeLeft <= 0}
            >
              {name}
              {isCurrent && <span className="loc-indicator">●</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}