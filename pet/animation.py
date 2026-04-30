"""帧动画引擎 - 管理宠物的各种动画状态"""
import math
import random
from enum import Enum
from typing import Optional

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainterPath, QColor, QPen, QBrush


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
    """Chibi 风格的动漫少女精灵。

    角色设定:
    - 浅粉色短发 + 厚重刘海
    - 紫罗兰色大眼睛
    - 额头两侧浅色小角饰品
    - 蓝黑色战斗服 + 黑色肩甲
    """

    def __init__(self, state: AnimationState = AnimationState.IDLE):
        self.state = state
        self.frame = 0
        self.total_frames = self._frames_for_state(state)
        self.x = 100  # 初始 x 位置
        self.y = 100  # 初始 y 位置
        self.target_x: Optional[float] = None
        self.target_y: Optional[float] = None
        self.eye_blink_timer = 0

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

    # ---- 颜色常量 ----
    HAIR_COLOR = QColor(255, 180, 200)      # 浅粉色头发
    HAIR_DARK = QColor(235, 155, 175)       # 头发阴影
    SKIN_COLOR = QColor(255, 230, 220)      # 肤色
    EYE_COLOR = QColor(140, 80, 200)        # 紫罗兰色
    EYE_DARK = QColor(100, 50, 160)         # 深色瞳孔
    EYE_HIGHLIGHT = QColor(255, 255, 255)   # 高光
    UNIFORM_BLUE = QColor(40, 60, 140)      # 战斗服蓝色
    UNIFORM_DARK = QColor(20, 25, 40)       # 战斗服深色/黑色
    SHOULDER_PAD = QColor(30, 30, 35)       # 黑色肩甲
    HORN_COLOR = QColor(220, 210, 200)      # 浅色小角
    MOUTH_COLOR = QColor(180, 100, 100)     # 嘴巴色

    def draw(self, painter, width: int, height: int, emotion: str = "neutral"):
        """用 QPainter 绘制 chibi 动漫少女。"""
        cx = int(self.x)
        cy = int(self.y)
        bob = math.sin(self.frame * 0.5) * 2

        painter.setRenderHint(painter.RenderHint.Antialiasing)

        # ========== 身体（战斗服）==========
        body_top = cy + 10 + bob
        self._draw_body(painter, cx, body_top, emotion)

        # ========== 头部 ==========
        head_cy = cy - 2 + bob

        # 皮肤底色
        self._draw_face(painter, cx, head_cy)

        # 眼睛（紫罗兰色大眼睛）
        is_blinking = (self.eye_blink_timer % 150) < 5
        self._draw_eyes(painter, cx, head_cy, emotion, is_blinking)

        # 嘴巴
        self._draw_mouth(painter, cx, head_cy, emotion)

        # 头发（浅粉色，覆盖头部上方 + 两侧）
        self._draw_hair(painter, cx, head_cy)

        # 刘海（厚重的刘海遮住额头部分）
        self._draw_bangs(painter, cx, head_cy)

        # 小角饰品（额头两侧）
        self._draw_horns(painter, cx, head_cy)

        # ========== 动画状态附加效果 ==========
        self._draw_state_effects(painter, cx, cy, bob, emotion)

    # ---- 绘制分解 ----

    def _draw_face(self, p, cx, cy):
        """脸部椭圆。"""
        cx, cy = int(cx), int(cy)
        p.setBrush(self.SKIN_COLOR)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), 20, 22)

    def _draw_eyes(self, p, cx, cy, emotion, blinking):
        """紫罗兰色大眼睛。"""
        cx, cy = int(cx), int(cy)
        if blinking:
            p.setPen(QPen(self.HAIR_DARK, 2))
            p.drawLine(cx - 11, cy - 4, cx - 4, cy - 4)
            p.drawLine(cx + 4, cy - 4, cx + 11, cy - 4)
            return

        # 眼睛方向
        look = 0
        if self.target_x is not None:
            look = 1 if self.target_x > self.x else -1

        eye_y = cy - 3
        left_x = cx - 10 + look
        right_x = cx + 10 + look

        # 眼白
        p.setBrush(QColor(255, 255, 255))
        p.setPen(QPen(QColor(50, 50, 60), 1))
        p.drawEllipse(QPointF(left_x, eye_y), 6, 8)
        p.drawEllipse(QPointF(right_x, eye_y), 6, 8)

        # 虹膜（紫罗兰色）
        p.setBrush(self.EYE_COLOR)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(left_x, eye_y), 4.5, 6.5)
        p.drawEllipse(QPointF(right_x, eye_y), 4.5, 6.5)

        # 瞳孔
        p.setBrush(self.EYE_DARK)
        p.drawEllipse(QPointF(left_x, eye_y + 1), 2.5, 3.5)
        p.drawEllipse(QPointF(right_x, eye_y + 1), 2.5, 3.5)

        # 高光
        p.setBrush(self.EYE_HIGHLIGHT)
        p.drawEllipse(QPointF(left_x + 2, eye_y - 2), 1.5, 1.5)
        p.drawEllipse(QPointF(right_x + 2, eye_y - 2), 1.5, 1.5)

    def _draw_mouth(self, p, cx, cy, emotion):
        """根据表情画嘴巴。"""
        cx, cy = int(cx), int(cy)
        p.setPen(QPen(self.MOUTH_COLOR, 1.5))
        mouth_y = cy + 8
        if emotion in ("happy", "excited"):
            # 微笑
            path = QPainterPath()
            path.moveTo(cx - 5, mouth_y)
            path.quadTo(cx, mouth_y + 4, cx + 5, mouth_y)
            p.setBrush(Qt.PenStyle.NoPen)
            p.drawPath(path)
        elif emotion == "sad":
            # 撇嘴
            path = QPainterPath()
            path.moveTo(cx - 5, mouth_y + 2)
            path.quadTo(cx, mouth_y, cx + 5, mouth_y + 2)
            p.setBrush(Qt.PenStyle.NoPen)
            p.drawPath(path)
        elif emotion == "sleepy":
            p.drawEllipse(QPointF(cx, mouth_y), 2, 1.5)
        else:
            # 小直线嘴
            p.drawLine(cx - 3, mouth_y, cx + 3, mouth_y)

    def _draw_hair(self, p, cx, cy):
        """浅粉色头发 - 覆盖头顶和两侧。"""
        p.setBrush(self.HAIR_COLOR)
        p.setPen(QPen(self.HAIR_DARK, 1))

        # 头顶主发块
        hair_path = QPainterPath()
        hair_path.moveTo(cx - 24, cy - 8)
        hair_path.quadTo(cx - 22, cy - 30, cx, cy - 32)
        hair_path.quadTo(cx + 22, cy - 30, cx + 24, cy - 8)
        hair_path.lineTo(cx + 20, cy + 2)
        hair_path.quadTo(cx + 14, cy - 5, cx, cy - 6)
        hair_path.quadTo(cx - 14, cy - 5, cx - 20, cy + 2)
        hair_path.closeSubpath()
        p.drawPath(hair_path)

        # 侧发 - 左
        p.setPen(Qt.PenStyle.NoPen)
        side_path = QPainterPath()
        side_path.moveTo(cx - 22, cy - 5)
        side_path.quadTo(cx - 28, cy + 4, cx - 26, cy + 14)
        side_path.quadTo(cx - 24, cy + 8, cx - 18, cy + 4)
        side_path.closeSubpath()
        p.drawPath(side_path)

        # 侧发 - 右
        side_path = QPainterPath()
        side_path.moveTo(cx + 22, cy - 5)
        side_path.quadTo(cx + 28, cy + 4, cx + 26, cy + 14)
        side_path.quadTo(cx + 24, cy + 8, cx + 18, cy + 4)
        side_path.closeSubpath()
        p.drawPath(side_path)

    def _draw_bangs(self, p, cx, cy):
        """厚重刘海。"""
        p.setBrush(self.HAIR_COLOR)
        p.setPen(QPen(self.HAIR_DARK, 0.5))

        # 主刘海 - 覆盖前额
        bang_path = QPainterPath()
        bang_path.moveTo(cx - 20, cy - 14)
        bang_path.quadTo(cx - 18, cy - 24, cx - 8, cy - 26)
        bang_path.quadTo(cx - 4, cy - 22, cx, cy - 22)
        bang_path.quadTo(cx + 4, cy - 22, cx + 8, cy - 26)
        bang_path.quadTo(cx + 18, cy - 24, cx + 20, cy - 14)
        bang_path.quadTo(cx + 15, cy - 8, cx, cy - 10)
        bang_path.quadTo(cx - 15, cy - 8, cx - 20, cy - 14)
        bang_path.closeSubpath()
        p.drawPath(bang_path)

        # 左侧一缕
        p.setPen(Qt.PenStyle.NoPen)
        left_bang = QPainterPath()
        left_bang.moveTo(cx - 18, cy - 14)
        left_bang.quadTo(cx - 22, cy - 6, cx - 16, cy + 2)
        left_bang.quadTo(cx - 14, cy - 4, cx - 15, cy - 10)
        left_bang.closeSubpath()
        p.drawPath(left_bang)

        # 右侧一缕
        right_bang = QPainterPath()
        right_bang.moveTo(cx + 18, cy - 14)
        right_bang.quadTo(cx + 22, cy - 6, cx + 16, cy + 2)
        right_bang.quadTo(cx + 14, cy - 4, cx + 15, cy - 10)
        right_bang.closeSubpath()
        p.drawPath(right_bang)

    def _draw_horns(self, p, cx, cy):
        """额头两侧的小角饰品。"""
        p.setBrush(self.HORN_COLOR)
        p.setPen(QPen(QColor(180, 170, 160), 1))

        # 左角
        horn_path = QPainterPath()
        horn_path.moveTo(cx - 15, cy - 20)
        horn_path.quadTo(cx - 20, cy - 32, cx - 18, cy - 30)
        horn_path.quadTo(cx - 14, cy - 28, cx - 12, cy - 20)
        horn_path.closeSubpath()
        p.drawPath(horn_path)

        # 右角
        horn_path = QPainterPath()
        horn_path.moveTo(cx + 15, cy - 20)
        horn_path.quadTo(cx + 20, cy - 32, cx + 18, cy - 30)
        horn_path.quadTo(cx + 14, cy - 28, cx + 12, cy - 20)
        horn_path.closeSubpath()
        p.drawPath(horn_path)

    def _draw_body(self, p, cx, cy, emotion):
        """蓝黑色战斗服 + 黑色肩甲，带呼吸浮动。"""
        cx, cy = int(cx), int(cy)
        # 躯干 - 蓝黑色战斗服
        body_path = QPainterPath()
        body_path.moveTo(cx - 15, cy)
        body_path.quadTo(cx - 18, cy + 16, cx - 14, cy + 28)
        body_path.quadTo(cx - 8, cy + 32, cx, cy + 32)
        body_path.quadTo(cx + 8, cy + 32, cx + 14, cy + 28)
        body_path.quadTo(cx + 18, cy + 16, cx + 15, cy)
        body_path.closeSubpath()

        # 填充渐变效果（用两个色块模拟）
        p.setBrush(self.UNIFORM_DARK)
        p.setPen(QPen(self.UNIFORM_BLUE, 1))
        p.drawPath(body_path)

        # 胸前蓝色装饰条
        p.setPen(QPen(self.UNIFORM_BLUE, 2))
        p.drawLine(cx - 6, cy + 4, cx + 6, cy + 4)
        p.drawLine(cx - 4, cy + 10, cx + 4, cy + 10)

        # 黑色肩甲 - 左
        p.setBrush(self.SHOULDER_PAD)
        p.setPen(QPen(QColor(50, 50, 55), 1))
        shoulder_path = QPainterPath()
        shoulder_path.moveTo(cx - 15, cy + 2)
        shoulder_path.quadTo(cx - 22, cy - 2, cx - 18, cy + 6)
        shoulder_path.quadTo(cx - 16, cy + 8, cx - 14, cy + 6)
        shoulder_path.closeSubpath()
        p.drawPath(shoulder_path)

        # 黑色肩甲 - 右
        shoulder_path = QPainterPath()
        shoulder_path.moveTo(cx + 15, cy + 2)
        shoulder_path.quadTo(cx + 22, cy - 2, cx + 18, cy + 6)
        shoulder_path.quadTo(cx + 16, cy + 8, cx + 14, cy + 6)
        shoulder_path.closeSubpath()
        p.drawPath(shoulder_path)

    def _draw_state_effects(self, p, cx, cy, bob, emotion):
        """根据状态和情绪绘制附加效果。"""
        # 兴奋心跳效果
        if emotion == "excited":
            p.setPen(QPen(QColor(255, 100, 150, 120), 1.5))
            heart_scale = 1 + math.sin(self.frame * 0.8) * 0.3
            hx = cx + 18
            hy = cy - 5
            # 简单小心形
            p.drawEllipse(QPointF(hx - 3 * heart_scale, hy), 3 * heart_scale, 3 * heart_scale)
            p.drawEllipse(QPointF(hx + 3 * heart_scale, hy), 3 * heart_scale, 3 * heart_scale)
            p.drawEllipse(QPointF(hx, hy + 3 * heart_scale), 2 * heart_scale, 2 * heart_scale)

        # 好奇问号
        if emotion == "curious":
            p.setPen(QPen(QColor(150, 200, 255, 150), 2))
            p.drawEllipse(QPointF(cx + 18, cy - 10), 4, 4)

        # 睡觉 Zzz
        if self.state == AnimationState.SLEEP:
            p.setPen(QPen(QColor(150, 180, 255, 150), 1.5))
            for i, (dx, dy) in enumerate([(16, -16), (20, -22), (24, -28)]):
                size = 4 - i
                p.drawText(
                    int(cx + dx), int(cy + dy + bob),
                    f"{'Z' * (i + 1)}"
                )
