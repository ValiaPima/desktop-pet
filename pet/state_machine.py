"""AI 驱动的行为状态机 - 宠物的「大脑」决策层"""
import random
import time
from enum import Enum

from config import BEHAVIOR_INTERVAL_BASE, BEHAVIOR_INTERVAL_JITTER, WINDOW_WIDTH, WINDOW_HEIGHT
from pet.animation import AnimationState, SimpleSprite
from pet.deepseek_client import DeepSeekClient
from pet.memory import PetMemory


class PetState(Enum):
    FREE = "free"
    INTERACTING = "interacting"
    SLEEPING = "sleeping"


class PetBrain:
    """宠物 AI 大脑。"""

    def __init__(self, sprite: SimpleSprite):
        self.sprite = sprite
        self.llm = DeepSeekClient()
        self.memory = PetMemory()
        self.state = PetState.FREE
        self.emotion = "neutral"
        self.last_behavior_time = 0
        self._next_behavior_delay = 0
        self.last_interaction_time = time.time()
        self.conversation_active = False
        self.pending_dialogue: str = ""
        self.pending_expression: str = ""
        self.user_idle = False

        self._click_responses = [
            "嘿嘿~", "干嘛呀~", "别戳了！", "嗯？",
            "摸摸头~", "痒！", "再摸要收费了！", "呼噜呼噜~",
            "再摸就生气了！", "嘿嘿嘿~",
        ]

    def update(self, current_time: float, user_activity: str = "未知"):
        """主循环更新。"""
        self.sprite.update()

        # 睡眠状态 —— 不决策，只显示 Zzz
        if self.state == PetState.SLEEPING:
            if self.sprite.state != AnimationState.SLEEP:
                self.sprite.set_state(AnimationState.SLEEP)
            self.emotion = "sleepy"
            return

        if self.state == PetState.INTERACTING:
            return

        self.user_idle = (current_time - self.last_interaction_time) > 120

        if self._next_behavior_delay == 0:
            self._next_behavior_delay = current_time + random.uniform(60, 120)
        elif current_time > self._next_behavior_delay:
            jitter = random.uniform(-BEHAVIOR_INTERVAL_JITTER, BEHAVIOR_INTERVAL_JITTER)
            self._next_behavior_delay = current_time + BEHAVIOR_INTERVAL_BASE + jitter
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
        action = decision.get("action", "idle")
        emotion = decision.get("emotion", "neutral")
        dialogue = decision.get("dialogue", "")
        expression = decision.get("expression", "")

        self.emotion = emotion
        self.pending_expression = expression

        action_map = {
            "idle": AnimationState.IDLE, "walk": AnimationState.WALK,
            "sleep": AnimationState.SLEEP, "play": AnimationState.PLAY,
            "excited": AnimationState.EXCITED, "curious": AnimationState.CURIOUS,
            "comfort": AnimationState.COMFORT, "talk": AnimationState.TALK,
        }
        self.sprite.set_state(action_map.get(action, AnimationState.IDLE))

        if dialogue:
            self.pending_dialogue = dialogue
        if action == "walk":
            self.sprite.wander(WINDOW_WIDTH, WINDOW_HEIGHT)

    def handle_user_input(self, text: str) -> str:
        self.last_interaction_time = time.time()
        # 睡觉时说话会叫醒
        if self.state == PetState.SLEEPING:
            self.state = PetState.INTERACTING
            self.sprite.set_state(AnimationState.IDLE)
            self.emotion = "curious"
            self.pending_expression = "揉眼睛"
            self.pending_dialogue = "唔…怎么了？"
            return "唔…怎么了？"

        self.state = PetState.INTERACTING
        memory_context = self.memory.build_context_prompt()
        decision = self.llm.chat(text, memory_context)
        self._apply_decision(decision)
        dialogue = decision.get("dialogue", "嗯？")
        self._extract_facts(text, dialogue)
        self.memory.add_interaction("user", text)
        self.memory.add_interaction("pet", dialogue, self.emotion)

        def end_interaction():
            self.state = PetState.FREE
        import threading
        threading.Timer(5.0, end_interaction).start()
        return dialogue

    def handle_click(self):
        self.last_interaction_time = time.time()
        # 睡觉时点击 = 被摸醒
        if self.state == PetState.SLEEPING:
            self.state = PetState.FREE
            self.sprite.set_state(AnimationState.CURIOUS)
            self.emotion = "curious"
            self.pending_dialogue = "嗯…谁摸我…"
            import threading
            threading.Timer(3.0, lambda: self.sprite.set_state(AnimationState.IDLE)).start()
            return

        self.memory.remember_emotion("被主人抚摸", "happy", 0.6)
        self.sprite.set_state(AnimationState.EXCITED)
        self.emotion = "happy"
        self.pending_dialogue = random.choice(self._click_responses)
        self.state = PetState.INTERACTING

        def end_interaction():
            self.state = PetState.FREE
            self.sprite.set_state(AnimationState.IDLE)
        import threading
        threading.Timer(3.0, end_interaction).start()

    def _extract_facts(self, user_text: str, pet_response: str):
        patterns = [
            ("喜欢", "喜欢"), ("最爱", "最爱"),
            ("不喜欢", "不喜欢"), ("我叫", "名字"),
            ("我是", "身份"),
        ]
        for keyword, fact_key in patterns:
            if keyword in user_text:
                idx = user_text.find(keyword)
                value = user_text[idx:idx + 30]
                self.memory.remember_fact(fact_key, value, confidence=0.5)
