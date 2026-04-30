# 🐾 AI 桌面宠物

一只由 DeepSeek 驱动的 AI 桌面宠物，会说话、有记忆、有情绪。

## 功能特性

### Lv3 智能

- **🧠 AI 大脑** — 基于 DeepSeek API 的行为决策，告别 if-else
- **💬 自然对话** — 用文字和宠物聊天，它会记住你
- **📝 长期记忆** — 记住你的喜好、习惯、说过的话
- **🎭 情绪系统** — 开心、难过、好奇、犯困…情绪影响行为和外观
- **🗣️ 语音输出** — 用 Edge-TTS 读出宠物说的话
- **👀 桌面感知** — 检测你的活动状态（写代码/发呆/离开）

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/<your-username>/desktop-pet.git
cd desktop-pet

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置 DeepSeek API Key
export DEEPSEEK_API_KEY="your-api-key-here"

# 4. 开玩！
python main.py
```

## 操作方式

| 操作 | 效果 |
|------|------|
| 🖱️ 点击宠物 | 抚摸它，它会开心 |
| 🖱️ 拖拽 | 移动窗口位置 |
| 📋 托盘菜单 → 聊天 | 和宠物说话 |
| 📋 托盘菜单 → 穿透 | 开启后鼠标穿过宠物（不影响正常工作） |

## 项目结构

```
desktop-pet/
├── main.py                  # 入口
├── config.py                # 配置
├── pet/
│   ├── window.py            # PyQt6 透明窗口
│   ├── animation.py         # 帧动画 + 绘制
│   ├── state_machine.py     # AI 行为决策
│   ├── deepseek_client.py   # DeepSeek API 客户端
│   ├── memory.py            # SQLite 记忆系统
│   ├── speech.py            # 语音输出
│   └── desktop_integration.py  # 桌面感知
├── assets/
│   └── sprites/             # 素材资源（施工中）
└── requirements.txt
```

## 路线图

- [x] 基础透明窗口 + 点击穿透
- [x] AI 行为决策（DeepSeek）
- [x] 对话 + 记忆
- [x] 语音输出
- [ ] 语音输入
- [ ] 真实 Sprite Sheet 素材
- [ ] VS Code / IDE 集成感知
- [ ] 番茄钟、Git 事件联动
- [ ] 多宠物互动
- [ ] 宠物成长/进化系统
