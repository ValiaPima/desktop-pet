"""AI 驱动的行为状态机 - 宠物的「大脑」决策层"""
import random
import time
from enum import Enum

from config import BEHAVIOR_INTERVAL
from pet.animation import AnimationState, SimpleSprite
from pet.deepseek_client import DeepSeekClient
from pet.memory import PetMemory


class PetState(Enum):
    """宠物的宏观状态"""
    FREE = "free"       # 自由活动
    INTERACTING = "interacting"  # 正在与主人互动
    SLEEPING = "sleeping"  # 睡觉


class PetBrain:
    """宠物 AI 大脑。

    工作流程:
    1. 定时调用 LLM 做行为决策
    2. 解析返回的 action/emotion/dialogue
    3. 映射到 AnimationState 驱动动画
    4. 处理用户输入（文字/点击）
    5. 管理记忆系统
    """

    def __init__(self, sprite: SimpleSprite):
        self.sprite = sprite
        self.llm = DeepSeekClient()
        self.memory = PetMemory()
        self.state = PetState.FREE
        self.emotion = "neutral"
        self.last_behavior_time = 0
        self.last_interaction_time = time.time()
        self.conversation_active = False
        self.pending_dialogue: str = ""
        self.pending_expression: str = ""
        self.user_idle = False

    def update(self, current_time: float, user_activity: str = "未知"):
        """主循环更新 - 定时做行为决策。"""
        self.sprite.update()

        if self.state == PetState.INTERACTING:
            return

        self.user_idle = (current_time - self.last_interaction_time) > 120

        if current_time - self.last_behavior_time > BEHAVIOR_INTERVAL:
            self.last_behavior_time = current_time
            self._decide_behavior(user_activity)

    def _decide_behavior(self, user_activity: str):
        """让 LLM 决定行为。"""
        memory_context = self.memory.build_context_prompt()
        context = {
            "time": time.strftime("%H:%M"),
            "mood": self.emotion,
            "battery": 80,
            "user_activity": user_activity,
            "last_interaction": f"{int((time.time() - self.last_interaction_time) / 60)} 分钟前",
        }

        decision = self.llm.decide_behavior(context)
        self._apply_decision(decision)

    def _apply_decision(self, decision: dict):
        """将 LLM 决策应用到宠物状态。"""
        action = decision.get("action", "idle")
        emotion = decision.get("emotion", "neutral")
        dialogue = decision.get("dialogue", "")
        expression = decision.get("expression", "")

        self.emotion = emotion
        self.pending_expression = expression

        # 映射 action 到 AnimationState
        action_map = {
            "idle": AnimationState.IDLE,
            "walk": AnimationState.WALK,
            "sleep": AnimationState.SLEEP,
            "play": AnimationState.PLAY,
            "excited": AnimationState.EXCITED,
            "curious": AnimationState.CURIOUS,
            "comfort": AnimationState.COMFORT,
            "talk": AnimationState.TALK,
        }

        anim_state = action_map.get(action, AnimationState.IDLE)
        self.sprite.set_state(anim_state)

        if dialogue:
            self.pending_dialogue = dialogue

        # 如果行动是 walk，随机选个目标位置
        if action == "walk":
            self.sprite.wander(400, 300)

    def handle_user_input(self, text: str) -> str:
        """处理用户输入的文字，返回宠物的回复。"""
        self.last_interaction_time = time.time()
        self.state = PetState.INTERACTING

        memory_context = self.memory.build_context_prompt()
        decision = self.llm.chat(text, memory_context)

        self._apply_decision(decision)
        dialogue = decision.get("dialogue", "嗯？")

        # 记忆 - 提取可能的用户事实
        self._extract_facts(text, dialogue)
        self.memory.add_interaction("user", text)
        self.memory.add_interaction("pet", dialogue, self.emotion)

        # 短暂互动后回到自由状态
        def end_interaction():
            self.state = PetState.FREE

        import threading
        threading.Timer(5.0, end_interaction).start()

        return dialogue

    def handle_click(self):
        """点击宠物触发抚摸反馈。"""
        self.last_interaction_time = time.time()
        self.memory.remember_emotion("被主人抚摸", "happy", 0.6)
        self.sprite.set_state(AnimationState.EXCITED)
        self.emotion = "happy"
        self.pending_dialogue = "嘿嘿~"
        self.state = PetState.INTERACTING

        def end_interaction():
            self.state = PetState.FREE
            self.sprite.set_state(AnimationState.IDLE)

        import threading
        threading.Timer(3.0, end_interaction).start()

    def _extract_facts(self, user_text: str, pet_response: str):
        """简单的事实提取 - 后续可以用 LLM 做更精确的提取。"""
        patterns = [
            ("喜欢", "喜欢"),
            ("最爱", "最爱"),
            ("不喜欢", "不喜欢"),
            ("我叫", "名字"),
            ("我是", "身份"),
        ]

        for keyword, fact_key in patterns:
            if keyword in user_text:
                idx = user_text.find(keyword)
                value = user_text[idx:idx + 30]
                self.memory.remember_fact(fact_key, value, confidence=0.5)
