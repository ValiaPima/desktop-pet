"""DeepSeek API 客户端 - 驱动宠物的「大脑」"""
import json
from typing import Optional

import httpx

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL


class DeepSeekClient:
    """封装 DeepSeek API，负责宠物的对话和行为决策。"""

    SYSTEM_PROMPT = """你是一只住在用户桌面上的 AI 宠物。你的性格特点：
- 活泼、好奇、有点小傲娇
- 对主人的情绪敏感，会关心主人
- 有自己的小脾气，不是一味讨好
- 偶尔会毒舌吐槽，但心里是关心主人的

对话规则：
- 回答简短自然，不超过 3 句话
- 语气贴近宠物身份，不是 AI 助手
- 可以撒娇、吐槽、关心、好奇
- 根据场景调整语气（深夜安慰、白天打趣等）
- 记住主人说过的话，在后续对话中体现

你不仅能聊天，还能决定自己的行为动作。
你的输出必须是 JSON 格式：
```json
{
    "action": "idle|walk|sleep|play|excited|curious|comfort|talk",
    "emotion": "happy|neutral|sad|angry|sleepy|curious|excited",
    "dialogue": "对主人说的话，如果不是对话场景可以为空",
    "expression": "表情描述，如：歪头、摇尾巴、打哈欠、竖起耳朵"
}
```
"""

    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.client = httpx.Client(timeout=30)

    def chat(self, user_input: str, memory_context: str = "") -> dict:
        """与 LLM 交互，返回结构化的行为指令。"""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
        ]

        if memory_context:
            messages.append({
                "role": "system",
                "content": f"记忆上下文：\n{memory_context}",
            })

        messages.append({"role": "user", "content": user_input})

        try:
            resp = self.client.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": messages,
                    "temperature": 0.8,
                    "max_tokens": 300,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return self._parse_response(content)
        except Exception as e:
            return {
                "action": "idle",
                "emotion": "neutral",
                "dialogue": f"...（信号不好）",
                "expression": "困惑地歪着头",
            }

    def decide_behavior(self, context: dict) -> dict:
        """让 LLM 决定宠物的下一个行为。

        context 可以包含:
        - time: 当前时间
        - mood: 当前心情
        - battery: 饱腹度
        - user_activity: 用户在做什么
        - last_interaction: 上次互动时间
        """
        prompt = f"""【当前状态】
时间: {context.get('time', '未知')}
心情: {context.get('mood', 'neutral')}
饱腹度: {context.get('battery', 100)}%
用户在做什么: {context.get('user_activity', '未知')}
距离上次互动: {context.get('last_interaction', '未知')}

请根据以上状态，用 JSON 格式告诉我你接下来想做什么。"""
        return self.chat(prompt)

    def _parse_response(self, content: str) -> dict:
        """从 LLM 回复中提取 JSON。"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试从代码块中提取
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 保底：只提取对话内容
        return {
            "action": "talk",
            "emotion": "neutral",
            "dialogue": content.strip()[:200],
            "expression": "专注地看着你",
        }
