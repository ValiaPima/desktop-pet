"""桌面宠物配置"""
import os
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 窗口设置
WINDOW_WIDTH = 220
WINDOW_HEIGHT = 320
WINDOW_ALPHA = 0.95

# 窗口吸附
DOCK_THRESHOLD = 20       # 距离边缘多少像素触发吸附
DOCK_HIDE_PERCENT = 0.15  # 吸附后露出比例

# 全局快捷键
HOTKEY_CHAT = "Ctrl+Shift+P"
HOTKEY_QUIT = "Ctrl+Shift+Q"

# 自动睡眠
AUTO_SLEEP_AFTER = 300    # 用户无操作多少秒后自动睡眠（5分钟）

# 动画设置
ANIMATION_FPS = 12
FRAME_INTERVAL_MS = 1000 // ANIMATION_FPS

# 行为决策间隔（秒）- 基础值，实际会加上随机偏移
BEHAVIOR_INTERVAL_BASE = 90
BEHAVIOR_INTERVAL_JITTER = 30  # 上下随机浮动秒数

# 记忆设置
MEMORY_DB_PATH = ROOT_DIR / "data" / "memory.db"

# 感知识别
IDLE_THRESHOLD_SECONDS = 120  # 用户无操作多久算 idle
