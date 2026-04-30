"""语音模块 - 文字转语音输出"""
import asyncio
import os
import threading
import tempfile
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QUrl, QObject
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput


class VoiceOutput(QObject):
    """语音输出模块，使用 Edge-TTS + PyQt6 QMediaPlayer。

    Edge-TTS 负责生成音频（免费、低延迟、效果好），
    QMediaPlayer 负责静默播放（不弹任何外部播放器窗口）。
    """

    def __init__(self, voice: str = "zh-CN-XiaoyiNeural", parent=None):
        super().__init__(parent)
        self.voice = voice
        self._enabled = True
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # PyQt6 内嵌播放器 — 不弹窗口
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)

        # 临时文件管理
        self._temp_dir = Path(tempfile.gettempdir()) / "desktop_pet_tts"
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        self._file_counter = 0

    def _ensure_loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop

    def say(self, text: str):
        """将文本转为语音并播放，全程无窗口弹出。"""
        if not self._enabled or not text:
            return

        def _run():
            try:
                import edge_tts

                # 生成唯一的临时文件
                self._file_counter += 1
                mp3_path = self._temp_dir / f"tts_{self._file_counter}.mp3"

                # 异步生成音频文件
                loop = self._ensure_loop()
                async def _generate():
                    communicate = edge_tts.Communicate(text, self.voice)
                    await communicate.save(str(mp3_path))
                loop.run_until_complete(_generate())

                # 用 QMediaPlayer 静默播放（在主线程消息队列中执行）
                self._player.stop()
                self._player.setSource(QUrl.fromLocalFile(str(mp3_path)))
                self._player.play()

            except Exception:
                pass  # 静默失败，不影响主功能

        threading.Thread(target=_run, daemon=True).start()

    def toggle(self, enabled: bool):
        self._enabled = enabled
        if not enabled:
            self._player.stop()
