"""语音模块 - 文字转语音输出"""
import asyncio
import threading
from typing import Optional


class VoiceOutput:
    """语音输出模块，使用 Edge-TTS（免费、低延迟、效果好）。

    需要联网首次下载语音模型。
    """

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural"):
        self.voice = voice
        self._enabled = True
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _ensure_loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop

    def say(self, text: str):
        """异步播放语音。"""
        if not self._enabled or not text:
            return

        def _run():
            try:
                import edge_tts
                loop = self._ensure_loop()
                async def _speak():
                    communicate = edge_tts.Communicate(text, self.voice)
                    await communicate.save("temp_speech.mp3")
                    # 播放（需要系统播放器）
                    import subprocess
                    subprocess.run(
                        ["start", "temp_speech.mp3"],
                        shell=True, capture_output=True,
                    )
                loop.run_until_complete(_speak())
            except Exception:
                pass  # 静默失败，不影响主功能

        threading.Thread(target=_run, daemon=True).start()

    def toggle(self, enabled: bool):
        self._enabled = enabled
