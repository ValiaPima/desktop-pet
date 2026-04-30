#!/usr/bin/env python3
"""桌面宠物 - 入口文件

一只由 AI 驱动的桌面宠物，会说话、有记忆、有情绪。

使用方式:
    export DEEPSEEK_API_KEY="your-api-key"
    python main.py
"""
import sys
import os

from PyQt6.QtWidgets import QApplication

from pet.window import PetWindow


def main():
    # 检查 API key
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("[!] 请先设置环境变量: export DEEPSEEK_API_KEY='your-key'")
        print("    也可以临时传入: DEEPSEEK_API_KEY=xxx python main.py")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 允许后台运行

    window = PetWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
