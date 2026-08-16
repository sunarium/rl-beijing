// TypeScript types matching the API contract

export interface Holding {
  goodsId: number;
  name: string;
  count: number;
  avgPrice: number;
}

export interface GameSettings {
  hackActs: boolean;
  closeSound: boolean;
}

export interface GameState {
  cash: number;
  debt: number;
  bank: number;
  health: number;
  healthMax: number;
  fame: number;
  fameMin: number;
  fameMax: number;
  coat: number;
  coatMax: number;
  total: number;
  holdings: Holding[];
  prices: number[];
  timeLeft: number;
  currentLoc: number | null;
  city: number;
  cityName: string;
  visitWangba: number;
  settings: GameSettings;
  score: number;
}

export interface Message {
  id: string;
  type: "diary" | "news";
  category: string;
  text: string;
  data: Record<string, unknown>;
}

export interface ActionResponse {
  gameId: string;
  state: GameState;
  messages: Message[];
  gameOver: boolean;
  action: string;
  params: Record<string, unknown>;
}

export interface LeaderboardEntry {
  rank: number;
  name: string;
  score: number;
  health: number;
  title: string;
}

export interface LeaderboardResponse {
  entries: LeaderboardEntry[];
  total: number;
}

export interface ErrorDetail {
  code: string;
  message: string;
  params: Record<string, unknown>;
}

export interface ErrorResponse {
  error: ErrorDetail;
}