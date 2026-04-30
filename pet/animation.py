"""帧动画引擎 - 管理宠物的各种动画状态"""
import math
import random
from enum import Enum
from typing import Optional


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
    """简易精灵 - 用几何图形绘制宠物。

    后续可以替换为真正的 PNG Sprite Sheet。
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

    def draw(self, painter, width: int, height: int, emotion: str = "neutral"):
        """用 QPainter 绘制当前帧。

        这是一个简化的绘制方法，用几何图形表示宠物。
        之后可以替换为 Sprite Sheet 渲染。
        """
        # 身体（椭圆）
        body_color = self._color_for_emotion(emotion)
        painter.setBrush(body_color)
        painter.setPen(body_color.darker(120))

        # 身体位置 - 根据动画状态有轻微的浮动
        float_offset = math.sin(self.frame * 0.5) * 3
        body_x = self.x - 25
        body_y = self.y - 30 + float_offset
        painter.drawEllipse(int(body_x), int(body_y), 50, 40)

        # 眼睛
        eye_white = painter.brush().color().lighter(200)
        painter.setBrush(eye_white)
        painter.setPen(eye_white)

        is_blinking = (self.eye_blink_timer % 150) < 5
        eye_y = self.y - 25 + float_offset

        if is_blinking:
            # 闭眼 - 画横线
            painter.setPen(painter.brush().color().darker(180))
            painter.drawLine(int(self.x - 10), int(eye_y),
                            int(self.x - 2), int(eye_y))
            painter.drawLine(int(self.x + 2), int(eye_y),
                            int(self.x + 10), int(eye_y))
        else:
            # 眼睛方向跟随目标
            look_offset = 0
            if self.target_x is not None:
                diff = self.target_x - self.x
                look_offset = 1 if diff > 0 else -1

            painter.setBrush(painter.brush().color().darker(180))
            painter.drawEllipse(int(self.x - 9 + look_offset), int(eye_y - 4), 7, 8)
            painter.drawEllipse(int(self.x + 2 + look_offset), int(eye_y - 4), 7, 8)

            # 瞳孔高光
            painter.setBrush(painter.brush().color().lighter(300))
            painter.drawEllipse(int(self.x - 6 + look_offset), int(eye_y - 2), 2, 2)
            painter.drawEllipse(int(self.x + 5 + look_offset), int(eye_y - 2), 2, 2)

        # 嘴巴（根据表情）
        painter.setPen(painter.brush().color().darker(150))
        mouth_y = self.y + 2 + float_offset
        if emotion in ("happy", "excited"):
            painter.drawArc(int(self.x - 8), int(mouth_y), 16, 10, 0, -180 * 16)
        elif emotion == "sad":
            painter.drawArc(int(self.x - 8), int(mouth_y + 5), 16, 10, 0, 180 * 16)
        elif emotion == "curious":
            painter.drawEllipse(int(self.x - 2), int(mouth_y), 4, 4)
        else:
            painter.drawLine(int(self.x - 5), int(mouth_y),
                            int(self.x + 5), int(mouth_y))

        # 耳朵
        ear_color = body_color.darker(110)
        painter.setBrush(ear_color)
        painter.setPen(ear_color)
        # 左耳
        painter.drawEllipse(int(self.x - 20), int(self.y - 35 + float_offset), 12, 10)
        # 右耳
        painter.drawEllipse(int(self.x + 8), int(self.y - 35 + float_offset), 12, 10)

        # 尾巴（状态相关）
        if self.state == AnimationState.EXCITED:
            # 兴奋时尾巴快速摇摆 - 画多条线模拟动画
            painter.setPen(painter.brush().color().darker(130))
            tail_wag = math.sin(self.frame * 1.5)
            tail_end_x = self.x - 30 + tail_wag * 10
            tail_end_y = self.y - 15 + float_offset
            painter.drawLine(int(self.x - 25), int(self.y - 10 + float_offset),
                            int(tail_end_x), int(tail_end_y))

    def _color_for_emotion(self, emotion: str):
        """根据情绪返回身体颜色。"""
        from PyQt6.QtGui import QColor
        palette = {
            "happy": QColor(255, 200, 100),    # 暖黄
            "excited": QColor(255, 180, 80),   # 橙黄
            "sad": QColor(180, 200, 220),      # 灰蓝
            "angry": QColor(255, 120, 100),    # 红
            "sleepy": QColor(200, 200, 220),   # 淡紫
            "curious": QColor(255, 220, 150),  # 浅橙
            "neutral": QColor(230, 210, 180),  # 米白
        }
        return palette.get(emotion, QColor(230, 210, 180))
