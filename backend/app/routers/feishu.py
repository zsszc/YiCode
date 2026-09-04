"""
飞书 Bot API Router — Phase 2
支持接收飞书消息，返回刷题看板和题目信息。
"""

import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services import DashboardService, ProblemService, LearningProfileService
from app.services.ai_tutor_service import AITutorService

router = APIRouter(prefix="/feishu", tags=["feishu"])

# 命令映射
COMMANDS = {
    "今日看板": "dashboard",
    "看板": "dashboard",
    "dashboard": "dashboard",
    "复习": "review",
    "review": "review",
    "统计": "stats",
    "stats": "stats",
    "帮助": "help",
    "help": "help",
}


def _build_dashboard_card(data: dict) -> dict:
    """构建飞书卡片消息 — 今日看板。"""
    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**📅 {data['date']} {'· 周末' if data['is_weekend'] else '· 工作日'}**\n"
                           f"配额 **{data['quota']}** 道 · 已做 **{len(data['done_today'])}** 道 · 剩余 **{data['todo_left']}** 道",
            },
        },
        {"tag": "hr"},
    ]

    # 到期复习
    if data.get("due_review"):
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**🔄 今日到期复习**"},
        })
        for item in data["due_review"][:5]:
            diff_emoji = {"简单": "🟢", "中等": "🟡", "困难": "🔴"}.get(item["difficulty"], "⚪")
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{diff_emoji} **#{item['id']}** {item['title']} ({item['difficulty']})",
                },
            })
        if len(data["due_review"]) > 5:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"_还有 {len(data['due_review']) - 5} 道题..._"},
            })

    # 今日新题
    if data.get("today_new"):
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "**✨ 今日新题**"},
        })
        for item in data["today_new"][:5]:
            diff_emoji = {"简单": "🟢", "中等": "🟡", "困难": "🔴"}.get(item["difficulty"], "⚪")
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{diff_emoji} **#{item['id']}** {item['title']}",
                },
            })

    # 统计
    elements.append({"tag": "hr"})
    counts = data.get("counts", {})
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": (
                f"📊 进度：未刷 {counts.get('todo', 0)} | 遗忘 {counts.get('forgot', 0)} | "
                f"磕绊 {counts.get('shaky', 0)} | 稳固 {counts.get('solid', 0)} | 归档 {counts.get('archived', 0)}"
            ),
        },
    })

    if data.get("finish"):
        finish = data["finish"]
        if finish.get("reachable"):
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"🎯 预计 **{finish['days_left']}** 天后完成（{finish['finish_date']}）",
                },
            })

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "忆码 YiCode · 今日看板"},
                "template": "blue",
            },
            "elements": elements,
        },
    }


def _build_stats_card(profile: dict, recommendation: dict) -> dict:
    """构建统计卡片。"""
    p = recommendation.get("profile", {})
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "忆码 YiCode · 学习统计"},
                "template": "green",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**🔥 连续打卡：{p.get('streak_days', 0)} 天** (最高 {profile.get('max_streak', 0)} 天)\n"
                            f"**🧩 总解题数：{profile.get('total_solved', 0)}**\n"
                            f"**📝 总复习数：{profile.get('total_reviewed', 0)}**\n"
                            f"**💡 提示依赖率：{p.get('hint_dependency_rate', 0):.0%}**\n"
                            f"**⭐ 首次成功率：{p.get('first_try_success_rate', 0):.0%}**\n"
                            f"**⏰ 活跃时段：{profile.get('peak_hour_start', 9)}:00 - {profile.get('peak_hour_end', 22)}:00**"
                        ),
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📋 AI 自适应建议**\n{recommendation.get('reasoning', '')}",
                    },
                },
            ],
        },
    }


def _build_help_card() -> dict:
    """构建帮助卡片。"""
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "忆码 YiCode · 命令帮助"},
                "template": "grey",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            "**可用命令：**\n"
                            "• `今日看板` / `dashboard` — 查看今日复习和新题\n"
                            "• `复习` / `review` — 列出到期复习题\n"
                            "• `统计` / `stats` — 学习数据统计\n"
                            "• `帮助` / `help` — 显示此帮助"
                        ),
                    },
                },
            ],
        },
    }


@router.post("/webhook")
async def feishu_webhook(request: Request, db: Session = Depends(get_db)):
    """接收飞书 Bot 消息。"""
    try:
        body = await request.json()
    except Exception:
        return {"msg_type": "text", "content": {"text": "无法解析消息"}}

    # 飞书 challenge 验证
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}

    # 提取消息内容
    event = body.get("event", {})
    msg = event.get("text", "").strip()
    user_id = event.get("open_id", "unknown")

    # 解析命令
    cmd = COMMANDS.get(msg.lower(), "unknown")

    if cmd == "dashboard":
        service = DashboardService(db)
        data = service.build()
        return _build_dashboard_card(data)

    elif cmd == "review":
        service = DashboardService(db)
        data = service.build()
        due = data.get("due_review", [])
        if not due:
            return {"msg_type": "text", "content": {"text": "🎉 今天没有到期复习题，去刷新题吧！"}}
        text = "🔄 今日到期复习：\n"
        for item in due[:10]:
            text += f"• #{item['id']} {item['title']} ({item['difficulty']})\n"
        return {"msg_type": "text", "content": {"text": text}}

    elif cmd == "stats":
        lp = LearningProfileService(db)
        profile = lp.get_or_create()
        recommendation = lp.adaptive_recommendation()
        return _build_stats_card(
            {
                "max_streak": profile.max_streak,
                "total_solved": profile.total_solved,
                "total_reviewed": profile.total_reviewed,
                "peak_hour_start": profile.peak_hour_start,
                "peak_hour_end": profile.peak_hour_end,
            },
            recommendation,
        )

    elif cmd == "help":
        return _build_help_card()

    # 默认：尝试题目查询
    if msg.startswith("题目 ") or msg.startswith("题 "):
        try:
            problem_id = int(msg.split()[-1])
            ps = ProblemService(db)
            p = ps.get_by_id(problem_id)
            if p:
                text = (
                    f"**#{p.id} {p.title}**\n"
                    f"难度：{p.difficulty}\n"
                    f"分类：{p.category}\n"
                    f"[去刷题 →](https://leetcode.cn/problems/{p.slug})"
                )
                return {"msg_type": "interactive", "card": {
                    "header": {"title": {"tag": "plain_text", "content": f"#{p.id} {p.title}"}, "template": "blue"},
                    "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": text}}],
                }}
        except (ValueError, IndexError):
            pass

    return {
        "msg_type": "text",
        "content": {"text": f"未识别的命令：{msg}\n输入 `帮助` 查看可用命令。"},
    }
