"""透明穿透窗口 - 宠物在桌面上活动的容器"""
import time
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QPoint, QRect
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

    def show_bubble(self, text: str, duration_frames: int = 90):
        """显示对话气泡。"""
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

        # 表情描述文字（底部）- 在图片下方
        if self.brain.pending_expression:
            painter.setPen(QColor(100, 100, 100, 180))
            font = QFont("Microsoft YaHei", 8)
            painter.setFont(font)
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(self.brain.pending_expression) + 12
            painter.drawText(
                int(sprite.x - text_w // 2), int(sprite.y + 95), text_w, 18,
                Qt.AlignmentFlag.AlignCenter,
                self.brain.pending_expression,
            )

    def _draw_bubble(self, painter, sprite):
        """绘制对话框气泡 — 自适应宽度 + 自动换行。"""
        text = self.bubble_text or ""
        if not text:
            return

        font = QFont("Microsoft YaHei", 9)
        painter.setFont(font)

        # 测量文字，决定换行
        fm = painter.fontMetrics()
        char_width = fm.horizontalAdvance("中")  # 一个中文字符的宽度
        max_chars_per_line = 12
        max_px_width = char_width * max_chars_per_line + 16  # 留 padding

        # 按宽度折行
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

        # 限制最多显示 3 行，超出加 "..."
        if len(lines) > 3:
            lines = lines[:3]
            if not lines[-1].endswith("…"):
                lines[-1] = lines[-1][:-1] + "…"

        # 计算气泡尺寸
        max_line_width = max(fm.horizontalAdvance(l) for l in lines)
        bubble_w = max(max_line_width + 24, 40)
        line_height = fm.height() + 4
        bubble_h = line_height * len(lines) + 12

        # 居中于 sprite 上方（图片高度约 180px，气泡放在图片上面）
        bubble_x = int(sprite.x - bubble_w // 2)
        bubble_y = int(sprite.y - 100 - bubble_h)

        # 背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 230))
        painter.drawRoundedRect(bubble_x, bubble_y, bubble_w, bubble_h, 8, 8)

        # 小三角（指向下方）
        triangle_y = bubble_y + bubble_h
        painter.drawPolygon(
            QPoint(int(sprite.x - 5), triangle_y),
            QPoint(int(sprite.x + 5), triangle_y),
            QPoint(int(sprite.x), triangle_y + 6),
        )

        # 文字
        painter.setPen(QColor(40, 40, 40))
        text_rect_x = bubble_x + 12
        text_rect_y = bubble_y + 6
        label_width = bubble_w - 24
        for i, line in enumerate(lines):
            painter.drawText(
                text_rect_x,
                text_rect_y + i * line_height,
                label_width,
                line_height,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                line,
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
        self.voice = VoiceOutput(parent=self)
        self._drag_pos = None

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
        """点击宠物触发交互 / 拖拽记录起点。"""
        if not self._click_through:
            self._drag_pos = event.globalPosition().toPoint()
            self.brain.handle_click()
            self.sensor.poke()
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """拖拽移动窗口。"""
        if not self._click_through:
            self.move(self.pos() + event.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        pass
