// API client for the game backend
import type { ActionResponse, LeaderboardResponse, ErrorResponse } from './types';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

class ApiError extends Error {
  code: string;
  params: Record<string, unknown>;

  constructor(code: string, message: string, params: Record<string, unknown> = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.params = params;
  }
}

async function handleResponse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let body: ErrorResponse;
    try {
      body = await resp.json();
    } catch {
      throw new ApiError('UNKNOWN', `HTTP ${resp.status}: ${resp.statusText}`);
    }
    const err = body.error || { code: 'UNKNOWN', message: 'Unknown error' };
    throw new ApiError(err.code, err.message, err.params);
  }
  return resp.json();
}

export async function createGame(agentName?: string, seed?: number): Promise<{
  gameId: string;
  state: import('./types').GameState;
  messages: import('./types').Message[];
  gameOver: boolean;
}> {
  const resp = await fetch(`${API_BASE}/games`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agentName, seed }),
  });
  return handleResponse(resp);
}

export async function getGame(gameId: string): Promise<{
  gameId: string;
  state: import('./types').GameState;
  gameOver: boolean;
}> {
  const resp = await fetch(`${API_BASE}/games/${gameId}`);
  return handleResponse(resp);
}

export async function postAction(
  gameId: string,
  action: string,
  params: Record<string, unknown> = {}
): Promise<ActionResponse> {
  const resp = await fetch(`${API_BASE}/games/${gameId}/actions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, params }),
  });
  return handleResponse(resp);
}

export async function getLeaderboard(limit = 10): Promise<LeaderboardResponse> {
  const resp = await fetch(`${API_BASE}/games/leaderboard?limit=${limit}`);
  return handleResponse(resp);
}

export { ApiError };