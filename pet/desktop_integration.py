"""桌面环境感知 - 监听系统状态，让宠物感知到周围环境"""
import time
from typing import Optional


class DesktopSensor:
    """感知桌面环境，为宠物提供上下文信息。

    当前功能:
    - 检测用户键盘鼠标活动（是否 idle）
    - 后续可以扩展: CPU/内存使用率、活动窗口标题、VS Code 状态等
    """

    def __init__(self):
        self.last_input_time = time.time()
        self._monitoring = False

    def get_user_activity(self) -> str:
        """返回用户当前活动状态的描述。"""
        idle_seconds = time.time() - self.last_input_time

        if idle_seconds < 30:
            return "正在使用电脑"
        elif idle_seconds < 120:
            return "好像在发呆"
        elif idle_seconds < 600:
            return "暂时离开了"
        else:
            return "很久没出现了"

    def poke(self):
        """检测到用户活动时调用。"""
        self.last_input_time = time.time()
