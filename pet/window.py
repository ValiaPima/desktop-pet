"""透明穿透窗口 - 宠物在桌面上活动的容器"""
import math
import time
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QAction, QIcon, QPixmap, QPainterPath
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QMenu,
    QSystemTrayIcon, QInputDialog, QLineEdit,
)

from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_ALPHA,
    DOCK_THRESHOLD, DOCK_HIDE_PERCENT,
    HOTKEY_CHAT, HOTKEY_QUIT,
    AUTO_SLEEP_AFTER,
)
from pet.animation import SimpleSprite
from pet.state_machine import PetBrain
from pet.desktop_integration import DesktopSensor
from pet.speech import VoiceOutput


def _make_tray_pixmap() -> QPixmap:
    """生成一个简单的托盘图标（粉紫色爱心）。"""
    pm = QPixmap(32, 32)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(255, 120, 160))
    p.setPen(Qt.PenStyle.NoPen)

    # 心形
    path = QPainterPath()
    path.moveTo(16, 28)
    path.cubicTo(2, 18, 4, 6, 16, 12)
    path.cubicTo(28, 6, 30, 18, 16, 28)
    p.drawPath(path)
    p.end()
    return pm


class PetWidget(QWidget):
    """宠物绘制区域。"""

    def __init__(self, brain: PetBrain, parent=None):
        super().__init__(parent)
        self.brain = brain
        self.bubble_text: Optional[str] = None
        self.bubble_timer = 0

    def show_bubble(self, text: str, duration_frames: int = 90):
        self.bubble_text = text
        self.bubble_timer = duration_frames

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 清空背景（透明）
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        sprite = self.brain.sprite
        sprite.draw(painter, self.width(), self.height(), self.brain.emotion)

        # 对话气泡
        if self.bubble_text and self.bubble_timer > 0:
            self._draw_bubble(painter, sprite)
            self.bubble_timer -= 1

        # 表情描述文字（图片下方）
        if self.brain.pending_expression and self.brain.state.name != "SLEEPING":
            painter.setPen(QColor(100, 100, 100, 180))
            font = QFont("Microsoft YaHei", 8)
            painter.setFont(font)
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(self.brain.pending_expression) + 12
            painter.drawText(
                int(sprite.x - text_w // 2), int(sprite.y + 80), text_w, 18,
                Qt.AlignmentFlag.AlignCenter,
                self.brain.pending_expression,
            )

        # 睡眠状态提示
        if self.brain.state.name == "SLEEPING":
            painter.setPen(QColor(150, 180, 255, 120))
            font = QFont("Microsoft YaHei", 9)
            painter.setFont(font)
            painter.drawText(
                int(sprite.x - 30), int(sprite.y + 75), 60, 18,
                Qt.AlignmentFlag.AlignCenter,
                "💤 睡着了",
            )

    def _draw_bubble(self, painter, sprite):
        text = self.bubble_text or ""
        if not text:
            return

        font = QFont("Microsoft YaHei", 9)
        painter.setFont(font)
        fm = painter.fontMetrics()

        # 折行
        max_chars_per_line = 12
        max_px_width = fm.horizontalAdvance("中") * max_chars_per_line + 16
        lines = []
        current_line = ""
        for ch in text:
            test_line = current_line + ch
            if fm.horizontalAdvance(test_line) > max_px_width and current_line:
                lines.append(current_line)
                current_line = ch
            else:
                current_line = test_line
        if current_line:
            lines.append(current_line)
        if len(lines) > 3:
            lines = lines[:3]
            if not lines[-1].endswith("…"):
                lines[-1] = lines[-1][:-1] + "…"

        max_line_width = max(fm.horizontalAdvance(l) for l in lines)
        bubble_w = max(max_line_width + 24, 40)
        line_height = fm.height() + 4
        bubble_h = line_height * len(lines) + 12

        # 气泡在 sprite 上方（图片顶部约在 sprite.y-70）
        bubble_x = int(sprite.x - bubble_w // 2)
        bubble_y = int(sprite.y - 85 - bubble_h)

        # 背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 230))
        painter.drawRoundedRect(bubble_x, bubble_y, bubble_w, bubble_h, 8, 8)

        # 小三角
        triangle_y = bubble_y + bubble_h
        painter.drawPolygon(
            QPoint(int(sprite.x - 5), triangle_y),
            QPoint(int(sprite.x + 5), triangle_y),
            QPoint(int(sprite.x), triangle_y + 6),
        )

        # 文字
        painter.setPen(QColor(40, 40, 40))
        for i, line in enumerate(lines):
            painter.drawText(
                bubble_x + 12,
                bubble_y + 6 + i * line_height,
                bubble_w - 24,
                line_height,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                line,
            )


class PetWindow(QMainWindow):
    """主窗口 - 透明、置顶、可穿透鼠标 + 吸附 + 快捷键。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("桌面宠物")

        # 窗口基础
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self._click_through = False

        # 组件
        self.sprite = SimpleSprite()
        self.brain = PetBrain(self.sprite)
        self.sensor = DesktopSensor()
        self.voice = VoiceOutput(parent=self)
        self._drag_pos = None
        self._docked = False      # 是否处于吸附状态
        self._dock_side = ""      # "left" | "right" | "top" | "bottom"
        self._docked_out = False  # 是否已露出（移出状态）

        # 绘制
        self.pet_widget = PetWidget(self.brain, self)
        self.setCentralWidget(self.pet_widget)

        # 系统托盘
        self._setup_tray()
        self._setup_hotkeys()

        # 定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self._game_loop)
        self.timer.start(100)

        self.behavior_timer = QTimer()
        self.behavior_timer.timeout.connect(self._behavior_loop)
        self.behavior_timer.start(500)

        self.dock_timer = QTimer()
        self.dock_timer.timeout.connect(self._check_dock)
        self.dock_timer.start(200)

    # ==================== 系统托盘 ====================

    def _setup_tray(self):
        self.tray_menu = QMenu()

        talk_action = self.tray_menu.addAction("聊天")
        talk_action.triggered.connect(self._show_chat_dialog)

        self.tray_menu.addSeparator()

        self._click_through_action = self.tray_menu.addAction("点击穿透: 关")
        self._click_through_action.triggered.connect(self._toggle_click_through)

        sleep_action = self.tray_menu.addAction("哄睡觉")
        sleep_action.triggered.connect(self._force_sleep)

        wake_action = self.tray_menu.addAction("叫醒")
        wake_action.triggered.connect(self._force_wake)

        self.tray_menu.addSeparator()

        quit_action = self.tray_menu.addAction("退出")
        quit_action.triggered.connect(QApplication.quit)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(_make_tray_pixmap()))
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.setToolTip("桌面宠物")
        self.tray_icon.activated.connect(self._on_tray_activate)
        self.tray_icon.show()

    # ==================== 全局快捷键 ====================

    def _setup_hotkeys(self):
        from PyQt6.QtGui import QShortcut, QKeySequence
        self._hotkey_chat = QShortcut(QKeySequence(HOTKEY_CHAT), self)
        self._hotkey_chat.activated.connect(self._show_chat_dialog)

        self._hotkey_sleep = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self._hotkey_sleep.activated.connect(self._force_sleep)

        self._hotkey_wake = QShortcut(QKeySequence("Ctrl+Shift+W"), self)
        self._hotkey_wake.activated.connect(self._force_wake)

    # ==================== 窗口吸附 ====================

    def _check_dock(self):
        """检测窗口是否靠近屏幕边缘。"""
        if self._click_through:
            return  # 穿透模式下不吸附

        screen = self.screen()
        if not screen:
            return
        sg = screen.geometry()
        wx, wy = self.x(), self.y()
        half_w = WINDOW_WIDTH // 2
        half_h = WINDOW_HEIGHT // 2
        cx = wx + half_w
        cy = wy + half_h

        # 计算到各边缘的距离
        dist_left = cx
        dist_right = sg.width() - cx
        dist_top = cy
        dist_bottom = sg.height() - cy

        min_dist = min(dist_left, dist_right, dist_top, dist_bottom)

        if min_dist > DOCK_THRESHOLD:
            if self._docked:
                # 恢复正常
                self._docked = False
                self._docked_out = False
                self._docked_out = False
                self._docked_out = False
            return

        # 在吸附阈值内
        if not self._docked and min_dist <= DOCK_THRESHOLD:
            self._docked = True
            self._docked_out = False

        if self._docked:
            # 根据最近边缘决定吸附方向
            sides = {
                "left": dist_left,
                "right": dist_right,
                "top": dist_top,
                "bottom": dist_bottom,
            }
            side = min(sides, key=sides.get)
            self._dock_side = side

            # 计算隐藏后应该露出多少
            show_w = int(WINDOW_WIDTH * DOCK_HIDE_PERCENT)
            show_h = int(WINDOW_HEIGHT * DOCK_HIDE_PERCENT)

            if side == "left":
                self.move(-WINDOW_WIDTH + show_w, wy)
            elif side == "right":
                self.move(sg.width() - show_w, wy)
            elif side == "top":
                self.move(wx, -WINDOW_HEIGHT + show_h)
            elif side == "bottom":
                self.move(wx, sg.height() - show_h)

    def _undock(self):
        """退出吸附状态。"""
        if self._docked:
            self._docked = False
            screen = self.screen()
            if screen:
                sg = screen.geometry()
                # 从吸附方向弹出一段
                step = 60
                x, y = self.x(), self.y()
                if self._dock_side == "left":
                    x += step
                elif self._dock_side == "right":
                    x -= step
                elif self._dock_side == "top":
                    y += step
                elif self._dock_side == "bottom":
                    y -= step
                self.move(x, y)

    # ==================== 交互 ====================

    def _toggle_click_through(self):
        self._click_through = not self._click_through
        if self._click_through:
            flags = (
                Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.Tool
                | Qt.WindowType.WindowTransparentForInput
            )
            self._click_through_action.setText("点击穿透: 开")
        else:
            flags = (
                Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.Tool
            )
            self._click_through_action.setText("点击穿透: 关")
        self.setWindowFlags(flags)
        self.show()

    def _show_chat_dialog(self):
        text, ok = QInputDialog.getText(
            self, "和宠物聊天", "说点什么:",
            QLineEdit.EchoMode.Normal, "",
        )
        if ok and text.strip():
            reply = self.brain.handle_user_input(text)
            self.pet_widget.show_bubble(reply)
            self.voice.say(reply)

    def _on_tray_activate(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_chat_dialog()

    def _force_sleep(self):
        """强制宠物睡觉。"""
        self.brain.state = type(self.brain.state).SLEEPING
        self.brain.sprite.set_state(AnimationState.SLEEP)
        self.brain.emotion = "sleepy"
        self.brain.pending_dialogue = "zzz… 那我先睡啦~"

    def _force_wake(self):
        """叫醒宠物。"""
        self.brain.state = type(self.brain.state).FREE
        self.brain.sprite.set_state(AnimationState.IDLE)
        self.brain.emotion = "neutral"
        self.brain.pending_dialogue = "嗯…？主人叫我？"
        self.sensor.poke()

    # ==================== 主循环 ====================

    def _game_loop(self):
        current_time = time.time()
        user_activity = self.sensor.get_user_activity()
        self.brain.update(current_time, user_activity)
        self.pet_widget.update()

        # 自动睡眠检测
        if (self.brain.state.name != "SLEEPING"
                and current_time - self.sensor.last_input_time > AUTO_SLEEP_AFTER):
            self._force_sleep()
            self.brain.pending_dialogue = ""  # 静默睡眠，不说话

        if self.brain.pending_dialogue:
            self.pet_widget.show_bubble(self.brain.pending_dialogue)
            self.voice.say(self.brain.pending_dialogue)
            self.brain.pending_dialogue = ""

    def _behavior_loop(self):
        pass

    # ==================== 鼠标事件 ====================

    def mousePressEvent(self, event):
        if not self._click_through:
            self._drag_pos = event.globalPosition().toPoint()
            self._undock()
            # 如果正在睡觉，点一下叫醒
            if self.brain.state.name == "SLEEPING":
                self._force_wake()
            else:
                self.brain.handle_click()
            self.sensor.poke()
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._click_through and self._drag_pos:
            self.move(self.pos() + event.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
