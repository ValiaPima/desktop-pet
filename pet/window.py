"""透明穿透窗口 - 宠物在桌面上活动的容器"""
import time
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QFont, QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QMenu,
    QSystemTrayIcon, QInputDialog, QLineEdit,
)

from config import WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_ALPHA
from pet.animation import SimpleSprite
from pet.state_machine import PetBrain
from pet.desktop_integration import DesktopSensor
from pet.speech import VoiceOutput


class PetWidget(QWidget):
    """宠物绘制区域。"""

    def __init__(self, brain: PetBrain, parent=None):
        super().__init__(parent)
        self.brain = brain
        self.bubble_text: Optional[str] = None
        self.bubble_timer = 0

    def show_bubble(self, text: str, duration_frames: int = 60):
        """显示对话气泡。"""
        max_width = 20
        if len(text) > max_width:
            text = text[:max_width] + "…"
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

        # 表情描述文字（底部小字）
        if self.brain.pending_expression:
            painter.setPen(QColor(100, 100, 100, 180))
            font = QFont("Microsoft YaHei", 8)
            painter.setFont(font)
            painter.drawText(
                int(sprite.x - 40), int(sprite.y + 40), 80, 20,
                Qt.AlignmentFlag.AlignCenter,
                self.brain.pending_expression,
            )

    def _draw_bubble(self, painter, sprite):
        """绘制对话框气泡。"""
        painter.setPen(QColor(255, 255, 255, 220))
        painter.setBrush(QColor(255, 255, 255, 220))

        bubble_x = int(sprite.x - 35)
        bubble_y = int(sprite.y - 60)
        bubble_w = 70
        bubble_h = 25

        painter.drawRoundedRect(bubble_x, bubble_y, bubble_w, bubble_h, 8, 8)

        # 小三角
        painter.drawPolygon(
            QPoint(int(sprite.x - 2), bubble_y + bubble_h),
            QPoint(int(sprite.x + 2), bubble_y + bubble_h),
            QPoint(int(sprite.x), bubble_y + bubble_h + 5),
        )

        painter.setPen(QColor(50, 50, 50))
        font = QFont("Microsoft YaHei", 9)
        painter.setFont(font)
        painter.drawText(
            bubble_x, bubble_y, bubble_w, bubble_h,
            Qt.AlignmentFlag.AlignCenter,
            self.bubble_text or "",
        )


class PetWindow(QMainWindow):
    """主窗口 - 透明、置顶、可穿透鼠标。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("桌面宠物")

        # 窗口基础设置
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )

        # 点击穿透切换
        self._click_through = False

        # 初始化组件
        self.sprite = SimpleSprite()
        self.brain = PetBrain(self.sprite)
        self.sensor = DesktopSensor()
        self.voice = VoiceOutput()

        # 宠物绘制
        self.pet_widget = PetWidget(self.brain, self)
        self.setCentralWidget(self.pet_widget)

        # 系统托盘
        self._setup_tray()

        # 定时器 - 游戏主循环
        self.timer = QTimer()
        self.timer.timeout.connect(self._game_loop)
        self.timer.start(100)  # 100ms ≈ 10fps

        # 行为循环
        self.behavior_timer = QTimer()
        self.behavior_timer.timeout.connect(self._behavior_loop)
        self.behavior_timer.start(500)  # 500ms 检查一次行为决策

    def _setup_tray(self):
        """设置系统托盘图标和菜单。"""
        self.tray_menu = QMenu()

        talk_action = self.tray_menu.addAction("聊天")
        talk_action.triggered.connect(self._show_chat_dialog)

        self.tray_menu.addSeparator()

        self._click_through_action = self.tray_menu.addAction("点击穿透: 关")
        self._click_through_action.triggered.connect(self._toggle_click_through)

        self.tray_menu.addSeparator()

        quit_action = self.tray_menu.addAction("退出")
        quit_action.triggered.connect(QApplication.quit)

        # 没有真图标就用一个占位
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.setToolTip("桌面宠物")
        self.tray_icon.activated.connect(self._on_tray_activate)
        self.tray_icon.show()

    def _toggle_click_through(self):
        """切换鼠标点击穿透。"""
        self._click_through = not self._click_through

        if self._click_through:
            self.setWindowFlags(
                Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.Tool
                | Qt.WindowType.WindowTransparentForInput
            )
            self._click_through_action.setText("点击穿透: 开")
        else:
            self.setWindowFlags(
                Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.Tool
            )
            self._click_through_action.setText("点击穿透: 关")

        self.show()

    def _show_chat_dialog(self):
        """弹出聊天输入框。"""
        text, ok = QInputDialog.getText(
            self, "和宠物聊天", "说点什么:",
            QLineEdit.EchoMode.Normal, "",
        )
        if ok and text.strip():
            reply = self.brain.handle_user_input(text)
            self.pet_widget.show_bubble(reply)
            self.voice.say(reply)

    def _on_tray_activate(self, reason):
        """点击托盘图标 - 可以随机互动。"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_chat_dialog()

    def _game_loop(self):
        """主循环 - 更新动画和绘制。"""
        current_time = time.time()
        self.brain.update(current_time, self.sensor.get_user_activity())
        self.pet_widget.update()

        # 显示对话气泡（如有待发言）
        if self.brain.pending_dialogue:
            self.pet_widget.show_bubble(self.brain.pending_dialogue)
            # 语音
            self.voice.say(self.brain.pending_dialogue)
            self.brain.pending_dialogue = ""

    def _behavior_loop(self):
        """行为决策循环 - 调用 LLM。"""
        # LLM 行为决策在 PetBrain.update() 中按间隔触发
        pass

    def mousePressEvent(self, event):
        """点击宠物触发交互。"""
        if not self._click_through:
            self.brain.handle_click()
            self.pet_widget.show_bubble("摸～")
            self.sensor.poke()
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """拖拽移动窗口。"""
        if not self._click_through:
            self.move(self.pos() + event.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        pass
