"""
Agent loop — drives the LLM through one complete game session.
"""
from __future__ import annotations

import json
import os
from openai import OpenAI

from .game_client import (
    GameClient,
    TOOL_DEFINITIONS,
    resolve_tool,
    format_state,
    format_messages,
    GOODS_NAMES,
    CITY_NAMES,
)

SYSTEM_PROMPT = """你是一个从农村来北京打工的年轻人。你有40天时间在北京闯荡，目标是挣尽可能多的钱。

【游戏目标】
最终得分 = 现金 + 存款 - 债务。最大化这个得分。游戏结束时得分>0才算赢。

【核心规则】
• 只有 travel(移动到新地点) 会消耗天数。其他所有操作（买卖、存取款、还债、治疗等）都是即时的，不消耗天数。
• 初始状态：现金2000元，债务5000元，存款0元，健康100/100，名声100/100，仓库容量100。
• 每次 travel 到新地点 = 消耗1天，触发完整日循环。
• 健康<0 → 死亡，游戏结束。
• 得分≤0 → 破产，游戏结束。
• 40天用完后强制结算，所有剩余货物按当前价格强制卖出。

【每日流程】（每次 travel 触发）
1. 生成新价格（8种商品随机定价，其中3种当天停售）
2. 利息结算（债务+10%，存款+1%）
3. 商业事件（最多18条，可多重触发，价格暴涨/暴跌/赠送货物）
4. 健康事件（最多1条，可能受伤）
5. 强制住院判定（健康<85且剩余>3天 → 强制住院损失1-2天+高额医疗费）
6. 偷钱事件（最多1条，偷现金或存款）
7. 黑客事件（如果开启）
8. 讨债（债务>10万 → 健康-30）
9. 天数-1，检查是否最后一天

【商品列表】
• 进口香烟 
• 走私汽车 
• 盗版VCD游戏
• 假白酒剧毒 — 卖这个会减名声
• 上海小宝贝禁书 — 卖这个会减名声
• 进口玩具 
• 水货手机
• 伪劣化妆品

正常情况下每天5种商品在售（3种停售），最后2天全部在售。

【地点】
两个地图各10个地点，用 toggle_map 切换：
地铁图：建国门、北京站、西直门、崇文门、东直门、复兴门、积水潭、长椿街、公主坟、苹果园
地面图：永安里、方庄、海淀大街、永定门、三元东桥、文津街、北辰西路、菜户营、翠微路、八角地铁

【重要策略提示】
1. 低买高卖：不同地点、不同天数的价格独立波动。
2. 关注商业事件消息：价格乘数事件(2x-8x)意味着巨大套利机会。
3. 尽早还债：债务每日10%复利增长！如果超过10万每天被打。
4. 保持健康>85：否则强制住院损失天数和金钱。
5. 善用银行：存款每日1%利息，且比现金安全（街头偷钱只偷现金）。
6. 仓库扩容：现金充裕时租房扩大容量，可以囤更多货。
7. 最后两天所有商品在售，但最后一天系统会强制清仓。
8. 卖禁书(-7名声/件)和假酒(-10名声/件)会损害名声。

【可用工具】
你有以下工具可用。每次行动前先思考，再调用工具。你可以多次调用工具。""".strip()


def run_agent(
    model: str,
    seed: int | None,
    game_url: str,
    api_key: str,
    api_base_url: str | None = None,
    max_turns: int = 200,
    verbose: bool = False,
    transcript: bool = False,
    transcript_path: str | None = None,
    reasoning_effort: str | None = None,
) -> dict:
    """Run one complete game session. Returns result metrics dict."""

    # ── 1. Setup ──────────────────────────────────────────
    client = GameClient(game_url)
    llm = OpenAI(api_key=api_key, base_url=api_base_url)

    # ── 2. Auto-create + start game ──────────────────────
    game_id, state = client.create_game(seed=seed)
    resp = client.post_action(game_id, "startGame", {})
    state = resp["state"]
    messages = resp.get("messages", [])

    if verbose:
        print(f"\n{'='*60}")
        print(f"🎮 Starting game | model={model} | seed={seed} | game_id={game_id[:8]}...")
        print(format_state(state))
        print(format_messages(messages))
        print(f"{'='*60}\n")

    # ── 2b. Transcript setup ─────────────────────────────
    if transcript:
        t: list[str] = []
        t.append("# 北京浮生记 Agent Transcript")
        t.append("")
        t.append(f"- **Model**: {model}")
        t.append(f"- **Seed**: {seed}")
        t.append(f"- **Game ID**: {game_id}")
        t.append("")
        t.append("## System Prompt")
        t.append("```")
        t.append(SYSTEM_PROMPT)
        t.append("```")
        t.append("")

    # ── 3. Initialize conversation ───────────────────────
    conversation: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "我是刚从乡下来的打工仔，有40天时间在北京闯荡。让我先看看黑市行情在哪里买货赚钱。"},
    ]

    turned_count = 0
    game_over = state.get("_gameOver", False)
    last_messages: list[dict] = messages or []

    # ── 4. Agent loop ────────────────────────────────────
    while not game_over and turned_count < max_turns:
        turned_count += 1

        # Show current state to LLM
        state_text = format_state(state)
        if last_messages:
            state_text += "\n" + format_messages(last_messages)

        conversation.append({"role": "user", "content": state_text})

        if transcript:
            t.append(f"## Turn {turned_count}")
            t.append("")
            t.append("### State")
            t.append("```")
            t.append(state_text)
            t.append("```")
            t.append("")

        # Call LLM
        completion_kwargs = {
            "model": model,
            "messages": conversation,
            "tools": TOOL_DEFINITIONS,
            "tool_choice": "auto",
        }
        if reasoning_effort:
            completion_kwargs["reasoning_effort"] = reasoning_effort
        try:
            response = llm.chat.completions.create(**completion_kwargs)
        except Exception as e:
            if verbose:
                print(f"⚠️  LLM API error: {e}")
            break

        choice = response.choices[0]
        msg = choice.message

        if verbose:
            if msg.content:
                print(f"🤔 [{turned_count}] {msg.content[:200]}")

        # Add assistant response to conversation
        content = msg.content if msg.content else None
        assistant_entry: dict = {"role": "assistant"}
        if content is not None:
            assistant_entry["content"] = content
        if msg.tool_calls:
            assistant_entry["tool_calls"] = [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
        conversation.append(assistant_entry)

        # If no tool calls, LLM is just thinking — continue
        if not msg.tool_calls:
            if transcript:
                t.append("### Assistant (thinking)")
                if content:
                    t.append(content)
                t.append("")
            continue

        # Transcript: log assistant message once before its tool calls
        if transcript:
            calls_str = ", ".join(f"`{c.function.name}(...)`" for c in msg.tool_calls)
            t.append(f"### Assistant → {calls_str}")
            if content:
                t.append(content)
            t.append("")

        # Execute each tool call
        last_messages = []
        for tc in msg.tool_calls:
            tool_name = tc.function.name
            try:
                tool_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                tool_args = {}

            if verbose:
                print(f"  🛠  {tool_name}({json.dumps(tool_args, ensure_ascii=False)})")

            # Dispatch
            result_text, new_msgs = resolve_tool(tool_name, tool_args, client, game_id)
            last_messages = new_msgs or []

            if verbose:
                first_line = result_text.split("\n")[0]
                print(f"  → {first_line}")

            if transcript:
                t.append(f"### Assistant")
                if content:
                    t.append(content)
                t.append("")
                t.append(f"**Tool call: `{tool_name}({json.dumps(tool_args, ensure_ascii=False)})`**")
                t.append("")
                t.append("**Result:**")
                t.append("```")
                t.append(result_text)
                t.append("```")
                t.append("")

            # Feed tool result back
            conversation.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_text,
            })

            # Check if any message indicates game over
            for m in (new_msgs or []):
                if "游戏结束" in m.get("text", "") or "死亡" in m.get("text", ""):
                    game_over = True

        # Fetch fresh state
        try:
            state = client.get_state(game_id)
            game_over = state.get("_gameOver", False)
        except Exception as e:
            if verbose:
                print(f"⚠️  State fetch error: {e}")
            break

    # ── 5. Auto-submit score ─────────────────────────────
    final_score = state.get("score", 0)
    submitted = False
    if final_score > 0:
        try:
            client.submit_score(game_id, f"agent-{model}")
            submitted = True
        except Exception:
            pass

    # ── 6. Determine game-over cause ─────────────────────
    if state.get("health", 100) <= 0:
        cause = "death"
    elif final_score <= 0:
        cause = "bankrupt"
    elif state.get("timeLeft", 0) <= 0:
        cause = "time_up"
    elif turned_count >= max_turns:
        cause = "max_turns"
    else:
        cause = "unknown"

    # ── 7. Return metrics ────────────────────────────────
    result = {
        "model": model,
        "seed": seed,
        "final_score": final_score,
        "cash": state.get("cash", 0),
        "bank": state.get("bank", 0),
        "debt": state.get("debt", 0),
        "health": state.get("health", 0),
        "fame": state.get("fame", 0),
        "days_used": 40 - state.get("timeLeft", 0),
        "warehouse_capacity": state.get("coat", 0),
        "cause": cause,
        "turns": turned_count,
        "score_submitted": submitted,
    }

    if verbose:
        print(f"\n{'='*60}")
        print(f"🏁 Game Over | cause={cause} | score={final_score:,}")
        print(f"  cash={state.get('cash',0):,}  bank={state.get('bank',0):,}  debt={state.get('debt',0):,}")
        print(f"  health={state.get('health',0)}  fame={state.get('fame',0)}  days_used={result['days_used']}")
        print(f"{'='*60}\n")

    # ── 8. Save transcript if requested ──────────────────
    if transcript and transcript_path:
        t.append("")
        t.append("## Summary")
        t.append("")
        t.append(f"- **Final score**: {final_score:,}")
        t.append(f"- **Cause**: {cause}")
        t.append(f"- **Turns**: {turned_count}")
        t.append(f"- **Days used**: {result['days_used']}")
        t.append(f"- **Cash**: {state.get('cash',0):,}")
        t.append(f"- **Bank**: {state.get('bank',0):,}")
        t.append(f"- **Debt**: {state.get('debt',0):,}")
        t.append(f"- **Health**: {state.get('health',0)} / Fame: {state.get('fame',0)}")
        t.append("")
        os.makedirs(os.path.dirname(transcript_path), exist_ok=True)
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write("\n".join(t))

    client.close()
    return result