"""精灵渲染引擎 - 加载 PNG 素材替代几何绘制"""
import math
import random
from enum import Enum
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QFont


class AnimationState(Enum):
    IDLE = "idle"
    WALK = "walk"
    SLEEP = "sleep"
    PLAY = "play"
    EXCITED = "excited"
    CURIOUS = "curious"
    COMFORT = "comfort"
    TALK = "talk"


class SimpleSprite:
    """PNG 精灵 — 加载角色立绘并渲染到桌面。"""

    def __init__(self, state: AnimationState = AnimationState.IDLE):
        self.state = state
        self.frame = 0
        self.total_frames = self._frames_for_state(state)
        self.x = 100
        self.y = 100
        self.target_x: Optional[float] = None
        self.target_y: Optional[float] = None
        self.eye_blink_timer = 0

        # 加载 PNG 精灵
        sprite_path = Path(__file__).parent.parent / "assets" / "sprites" / "pet_sprite.png"
        self._pixmap = QPixmap(str(sprite_path))
        if self._pixmap.isNull():
            print(f"[PET] 未找到精灵图: {sprite_path}，使用 fallback 颜色块")
        else:
            # 缩放至窗口适合大小（保持比例）
            self._pixmap = self._pixmap.scaled(
                130, 180,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

    def _frames_for_state(self, state: AnimationState) -> int:
        mapping = {
            AnimationState.IDLE: 4,
            AnimationState.WALK: 6,
            AnimationState.SLEEP: 2,
            AnimationState.PLAY: 4,
            AnimationState.EXCITED: 3,
            AnimationState.CURIOUS: 2,
            AnimationState.COMFORT: 3,
            AnimationState.TALK: 4,
        }
        return mapping.get(state, 4)

    def set_state(self, state: AnimationState):
        if self.state != state:
            self.state = state
            self.frame = 0
            self.total_frames = self._frames_for_state(state)

    def update(self):
        """更新动画帧。"""
        self.frame = (self.frame + 1) % self.total_frames
        self.eye_blink_timer += 1

        # 移动逻辑
        if self.target_x is not None and self.target_y is not None:
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 5:
                speed = 3 if self.state == AnimationState.WALK else 1.5
                self.x += (dx / dist) * speed
                self.y += (dy / dist) * speed
            else:
                self.target_x = None
                self.target_y = None
                if self.state == AnimationState.WALK:
                    self.set_state(AnimationState.IDLE)

    def wander(self, bounds_width: int, bounds_height: int):
        """随机移动目标。"""
        margin = 40
        self.target_x = random.uniform(margin, bounds_width - margin)
        self.target_y = random.uniform(margin, bounds_height - margin)
        self.set_state(AnimationState.WALK)

    def draw(self, painter, width: int, height: int, emotion: str = "neutral"):
        """绘制精灵 + 状态叠加效果。"""
        cx = int(self.x)
        cy = int(self.y)
        bob = math.sin(self.frame * 0.5) * 2

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # ---- 精灵图 ----
        if not self._pixmap.isNull():
            pw, ph = self._pixmap.width(), self._pixmap.height()
            px = cx - pw // 2
            py = cy - ph + 20 + int(bob)
            painter.drawPixmap(px, py, self._pixmap)
        else:
            # fallback：简单的颜色块
            painter.setBrush(QColor(200, 180, 220))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(cx - 30, cy - 40 + int(bob), 60, 70, 10, 10)
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(QPointF(cx - 8, cy - 18), 5, 6)
            painter.drawEllipse(QPointF(cx + 8, cy - 18), 5, 6)
            painter.setBrush(QColor(60, 40, 120))
            painter.drawEllipse(QPointF(cx - 7, cy - 17), 2, 3)
            painter.drawEllipse(QPointF(cx + 9, cy - 17), 2, 3)

        # ---- 情绪特效叠加 ----
        self._draw_effects(painter, cx, cy, bob, emotion)

    def _draw_effects(self, p, cx, cy, bob, emotion):
        """情绪特效（爱心、问号、Zzz 等）。"""
        if emotion == "excited":
            # 小心心跳动
            p.setPen(QPen(QColor(255, 100, 150, 160), 2))
            heart_scale = 1 + math.sin(self.frame * 0.8) * 0.3
            hx = cx + 22
            hy = cy - 10
            r = 4 * heart_scale
            p.drawEllipse(QPointF(hx - r * 0.5, hy), r, r)
            p.drawEllipse(QPointF(hx + r * 0.5, hy), r, r)
            # 小心尖
            tip = QPainterPath()
            tip.moveTo(hx - r * 0.8, hy + r * 0.2)
            tip.lineTo(hx, hy + r * 1.2)
            tip.lineTo(hx + r * 0.8, hy + r * 0.2)
            p.setBrush(QColor(255, 100, 150, 120))
            p.drawPath(tip)

        elif emotion == "curious":
            # 问号
            p.setPen(QPen(QColor(150, 200, 255, 180), 2.5))
            font = QFont("Arial", 14, QFont.Weight.Bold)
            p.setFont(font)
            p.drawText(int(cx + 20), int(cy - 22), "?")

        elif self.state == AnimationState.SLEEP:
            # Zzz
            p.setPen(QPen(QColor(150, 180, 255, 150), 2))
            font = QFont("Arial", 10, QFont.Weight.Bold)
            p.setFont(font)
            for i, (dx, dy) in enumerate([(18, -20), (24, -28), (30, -36)]):
                p.drawText(int(cx + dx), int(cy + dy), "Z" * (i + 1))
