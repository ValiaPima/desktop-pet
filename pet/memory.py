"""宠物记忆系统 - SQLite + 简单的语义检索"""
import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from config import MEMORY_DB_PATH


class PetMemory:
    """宠物记忆模块。

    存储三类信息:
    1. facts - 关于用户的事实性知识（喜欢的食物、习惯等）
    2. interactions - 对话/互动历史
    3. emotional_memory - 情绪记忆（什么让宠物开心/不开心）
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or MEMORY_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                created_at REAL DEFAULT (strftime('%s','now')),
                updated_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,  -- 'user' | 'pet'
                content TEXT NOT NULL,
                emotion TEXT DEFAULT 'neutral',
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS emotional_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_event TEXT NOT NULL,
                emotion TEXT NOT NULL,
                intensity REAL DEFAULT 0.5,
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        conn.commit()
        conn.close()

    # ---- facts ----

    def remember_fact(self, key: str, value: str, confidence: float = 1.0):
        """记住一个关于用户的事实。"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            """INSERT INTO facts (key, value, confidence, updated_at)
               VALUES (?, ?, ?, strftime('%s','now'))
               ON CONFLICT(key) DO UPDATE SET
                   value = excluded.value,
                   confidence = excluded.confidence,
                   updated_at = strftime('%s','now')""",
            (key, value, confidence),
        )
        conn.commit()
        conn.close()

    def recall_fact(self, key: str) -> Optional[str]:
        """回忆一个事实。"""
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute(
            "SELECT value FROM facts WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def all_facts(self) -> list[dict]:
        """获取所有事实。"""
        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute(
            "SELECT key, value, confidence FROM facts ORDER BY updated_at DESC"
        ).fetchall()
        conn.close()
        return [{"key": k, "value": v, "confidence": c} for k, v, c in rows]

    # ---- interactions ----

    def add_interaction(self, role: str, content: str, emotion: str = "neutral"):
        """记录一次互动。"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO interactions (role, content, emotion) VALUES (?, ?, ?)",
            (role, content, emotion),
        )
        conn.commit()
        conn.close()

    def recent_interactions(self, limit: int = 20) -> list[dict]:
        """获取最近的互动历史。"""
        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute(
            "SELECT role, content, emotion, created_at FROM interactions "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [
            {"role": r, "content": c, "emotion": e, "time": t}
            for r, c, e, t in reversed(rows)
        ]

    # ---- emotional memory ----

    def remember_emotion(self, trigger: str, emotion: str, intensity: float = 0.5):
        """记住一件引发情绪的事件。"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO emotional_memory (trigger_event, emotion, intensity) "
            "VALUES (?, ?, ?)",
            (trigger, emotion, intensity),
        )
        conn.commit()
        conn.close()

    def recent_emotions(self, limit: int = 10) -> list[dict]:
        """最近的情绪记录。"""
        conn = sqlite3.connect(str(self.db_path))
        rows = conn.execute(
            "SELECT trigger_event, emotion, intensity, created_at "
            "FROM emotional_memory ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [
            {"trigger": t, "emotion": e, "intensity": i, "time": c}
            for t, e, i, c in rows
        ]

    # ---- LLM prompt builder ----

    def build_context_prompt(self) -> str:
        """构建给 LLM 的上下文提示。"""
        facts = self.all_facts()
        recent = self.recent_interactions()

        parts = []
        if facts:
            parts.append("【我记住的关于你的事】")
            for f in facts:
                parts.append(f"- {f['key']}: {f['value']}")

        if recent:
            parts.append("\n【最近的互动】")
            for r in recent[-6:]:  # 最近6条
                label = "你" if r["role"] == "user" else "我"
                parts.append(f"  {label}: {r['content']}")

        return "\n".join(parts) if parts else "（还没有记住什么）"
