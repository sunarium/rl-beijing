"""
FastAPI 应用 — 北京浮生记 v1.2.2 API 服务
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import (
    CreateGameRequest, ActionRequest, ActionResponse,
    LeaderboardResponse, LeaderboardEntry, ErrorResponse, ErrorDetail,
    fame_title,
)
from game_engine import GameSessionManager, GameError

app = FastAPI(
    title="北京浮生记 API",
    version="1.0.0",
    description="北京浮生记 v1.2.2 — 面向前端与自动化 Agent 的游戏后端服务",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局会话管理器（内存存储）
manager = GameSessionManager()


# ── 错误处理 ──────────────────────────────────────────

@app.exception_handler(GameError)
async def game_error_handler(request, exc: GameError):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code={
            "INVALID_PARAM": 400,
            "INVALID_COUNT": 400,
            "GAME_NOT_FOUND": 404,
            "GAME_OVER": 409,
            "GAME_NOT_STARTED": 409,
            "SCORE_ALREADY_SUBMITTED": 422,
        }.get(exc.code, 422),
        content=ErrorResponse(
            error=ErrorDetail(code=exc.code, message=exc.message, params=exc.params)
        ).model_dump(),
    )


# ── 端点 ──────────────────────────────────────────────

@app.post("/api/v1/games")
async def create_game(req: CreateGameRequest):
    game_id, engine = manager.create_game(seed=req.seed)
    state, msgs = engine.handle_action("startGame", {})
    return {
        "gameId": game_id,
        "createdAt": None,  # 简化：不返回时间
        "state": state.model_dump(),
        "messages": [m.model_dump() for m in msgs],
        "gameOver": False,
    }


@app.get("/api/v1/games/leaderboard")
async def get_leaderboard(limit: int = 10):
    entries = manager.get_leaderboard()
    return LeaderboardResponse(
        entries=[LeaderboardEntry(**e) for e in entries],
        total=len(entries),
    )


@app.get("/api/v1/games/{game_id}")
async def get_game(game_id: str):
    engine = manager.get_game(game_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=ErrorResponse(
            error=ErrorDetail(code="GAME_NOT_FOUND", message="游戏不存在。")
        ).model_dump())
    return {
        "gameId": game_id,
        "createdAt": None,
        "state": engine.get_state().model_dump(),
        "gameOver": engine.game_over,
    }


@app.post("/api/v1/games/{game_id}/actions")
async def post_action(game_id: str, req: ActionRequest):
    engine = manager.get_game(game_id)
    if engine is None:
        raise GameError("GAME_NOT_FOUND", "游戏不存在。")

    state, msgs = engine.handle_action(req.action, req.params)

    return ActionResponse(
        gameId=game_id,
        state=state,
        messages=msgs,
        gameOver=engine.game_over,
        action=req.action,
        params=req.params,
    )


@app.post("/api/v1/games/{game_id}/submit")
async def submit_score(game_id: str, req: ActionRequest):
    """
    提交高分的快捷端点（与 POST /actions 等效但更显式）。
    """
    engine = manager.get_game(game_id)
    if engine is None:
        raise GameError("GAME_NOT_FOUND", "游戏不存在。")

    name = req.params.get("name", "无名氏")
    state, msgs = engine._handle_submit_score(name, [])

    return ActionResponse(
        gameId=game_id,
        state=state,
        messages=msgs,
        gameOver=engine.game_over,
        action="submitScore",
        params={"name": name},
    )


# ── 健康检查 ──────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}