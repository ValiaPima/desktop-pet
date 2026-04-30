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
WINDOW_WIDTH = 200
WINDOW_HEIGHT = 200
WINDOW_ALPHA = 0.95  # 窗口透明度

# 动画设置
ANIMATION_FPS = 12
FRAME_INTERVAL_MS = 1000 // ANIMATION_FPS

# 行为决策间隔（秒）
BEHAVIOR_INTERVAL = 15

# 记忆设置
MEMORY_DB_PATH = ROOT_DIR / "data" / "memory.db"

# 感知识别
IDLE_THRESHOLD_SECONDS = 120  # 用户无操作多久算 idle
