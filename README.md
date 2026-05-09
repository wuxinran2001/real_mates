 # 🎭 小美AI聊天机器人 - Ren'Py版

[![Ren'Py](https://img.shields.io/badge/Ren'Py-8.0+-blue.svg)](https://www.renpy.org/)
[![Python](https://img.shields.io/badge/Python-3.9+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![API](https://img.shields.io/badge/API-讯飞星火-orange.svg)](https://www.xfyun.cn/)

一个基于Ren'Py游戏引擎开发的智能聊天机器人，集成了讯飞星火大模型API和Edge-TTS语音合成功能，提供富有情感交互的对话体验。

## ✨ 特性

- 🎨 **视觉小说风格界面** - 使用Ren'Py引擎打造精美的对话界面
- 🧠 **AI智能对话** - 接入讯飞星火大模型，支持自然语言理解和生成
- 🎭 **情感表达系统** - 机器人会根据对话内容展现6种不同情绪（normal、smile、think、sad、angry、shy）
- 🔊 **TTS语音合成** - 使用Edge-TTS将机器人回复转换为语音，支持语音缓存
- 📝 **JSON格式响应** - LLM严格按照JSON格式返回，确保情绪和内容的准确解析
- 🔄 **流式/非流式输出** - 支持两种输出模式
- 💾 **聊天历史记录** - 保存完整对话历史
- 📖 **文本分页显示** - 长文本自动分页，提升阅读体验
- 🌐 **在线/离线模式** - API不可用时自动切换到本地关键词回复

## 🎮 游戏截图
<img width="1335" height="777" alt="image" src="https://github.com/user-attachments/assets/5ac786c0-a9b4-4fe6-85d4-1dd5db15043d" />

## 📋 系统要求

- Ren'Py 8.0 或更高版本
- Python 3.9+
- 讯飞星火大模型API密钥
- 网络连接（用于API调用和TTS）

开发本项目，需要先下载安装Ren'Py，并导入本项目。请申请自己的API，填入script.rpy指定位置。

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/wuxinran2001/real_mates.git

# 安装Python依赖
pip install requests edge-tts
```

#### 配置大模型文件

编辑 game/script.rpy 文件，修改API配置：

```python
XUNFEI_CONFIG = {
    "api_url": "http://maas-api.cn-huabei-1.xf-yun.com/v1/chat/completions",
    "api_key": "your_api_key:your_api_secret",  # 格式：APIKey:APISecret
    "model_id": "your_model_id_here",           # 如：generalv3.5
    "system_prompt": "你是一个开心的AI助手...",
    "max_tokens": 4096,
    "temperature": 0.7,
    "timeout": 120
}
```

### 2. 定制化设计


#### 准备资源文件

创建 game/images/ 文件夹并添加以下图片：

```
game/images/
├── bg_room.jpg          # 背景图片（建议1920x1080）
├── bot_normal.png       # 正常表情（建议800x800，透明背景）
├── bot_smile.png        # 微笑表情
├── bot_think.png        # 思考表情
├── bot_sad.png          # 悲伤表情
├── bot_angry.png        # 生气表情
└── bot_shy.png          # 害羞表情
```

图片制作建议：

使用PNG格式支持透明背景

保持角色风格统一

表情差异明显可辨

文件大小控制在2MB以内

#### 修改机器人性格

编辑 script.rpy 中的 system_prompt：

```python
XUNFEI_CONFIG["system_prompt"] = """
你是一个{性格描述}的AI助手。
名字：{名字}
特点：{特点列表}

{你想要的任何额外指令}

请严格按照以下JSON格式回复：
{
    "emotion": "情绪类型",
    "text": "回复内容"
}
"""
```

示例 - 治愈系：

```python
"system_prompt": """
你是一个温柔治愈的AI助手，名字叫暖暖。
特点：
- 说话温柔体贴
- 善于安慰他人
- 充满正能量

回复格式：JSON...
"""
```

示例 - 幽默系：

```python
"system_prompt": """
你是一个幽默风趣的AI助手，名字叫笑笑。
特点：
- 说话幽默搞笑
- 喜欢讲笑话
- 活跃气氛

回复格式：JSON...
"""
```

#### 调整语音参数

```python
TTS_CONFIG = {
    "rate": "+20%",      # 语速：-100% 到 +100%
    "volume": "-10%",    # 音量：-100% 到 +100%
    "voice_mapping": {
        "normal": "zh-CN-XiaoxiaoNeural",
        # 可以替换为其他支持的语音
    }
}
```

支持语音如下：

```
zh-CN-XiaoxiaoNeural 女，普通话，温暖、亲切、通用
zh-CN-XiaoyiNeural 女，普通话，活泼、可爱、元气
zh-CN-YunxiNeural 男，普通话，阳光、年轻、有活力
zh-CN-shaanxi-XiaoniNeural 女，陕西话，接地气
zh-CN-liaoning-XiaobeiNeural 女，东北话，接地气
zh-HK-HiuGaaiNeural 女，粤语，香港话
zh-TW-HsiaoYuNeural 女，普通话，台湾腔
zh-TW-YunJheNeural 男，普通话，台湾腔
```

### 3. 运行项目


使用Ren'Py Launcher：
打开Ren'Py启动器

点击"Preferences" → "Projects Directory" 选择项目目录

点击"Launch Project"启动游戏


### 4. 发行版下载


release目录下real_mates-1.0-win,解压缩后运行real_mates.exe即可游玩。
