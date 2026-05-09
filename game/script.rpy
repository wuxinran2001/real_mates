# ========================================
# LLM聊天机器人项目 - 讯飞API版本（带TTS语音功能）
# 使用纯requests实现，无需openai库
# ========================================

# 1. 角色定义
define c = Character("你", color="#e8a639")
define bot = Character("小美", color="#e8a639", image="bot", what_xpos=0.5, what_xanchor=0.5, what_text_xalign=0.0, what_xsize=850,what_ypos=0.3,what_style="say_dialogue",what_text_align=0.0)

# 聊天角色形象（为不同表情创建不同立绘）
image bot normal = "images/bot_normal.png"
image bot smile = "images/bot_smile.png"
image bot think = "images/bot_think.png"
image bot sad = "images/bot_sad.png"
image bot angry = "images/bot_angry.png"
image bot shy = "images/bot_shy.png"

# 立绘位置定义 - 必须在start之前定义
transform bot_center:
    xpos 0.5
    xanchor 0.5
    ypos 0.75
    yanchor 0.5

transform bot_left:
    xpos 0.1
    xanchor 0.5
    ypos 0.85
    yanchor 0.5

transform bot_right:
    xpos 0.85
    xanchor 0.5
    ypos 0.85
    yanchor 0.5

# 添加背景图
image bg room = Frame("images/bg_room.jpg", 0, 0)
image bg default = Solid("#1a1a2e")

define keywords = '''【重要】请严格按照以下JSON格式回复，不要包含任何其他内容：
{
    "emotion": "情绪类型",
    "text": "你的回复内容"
}

情绪类型只能是以下之一：normal, smile, think, sad, angry, shy

示例1：
{
    "emotion": "smile",
    "text": "你好呀！今天天气真好~"
}

示例2：
{
    "emotion": "think",
    "text": "嗯...让我想想这个问题。"
}

请确保回复是有效的JSON格式！'''

# 2. 游戏核心系统
init python:
    import json
    import requests
    import time
    import random
    import re
    from datetime import datetime
    import asyncio
    import edge_tts
    import os
    import threading
    
    # ========== TTS语音配置 ==========
    TTS_CONFIG = {
        # 不同情绪对应的不同语音角色
        "voice_mapping": {
            "normal": "zh-CN-XiaoxiaoNeural",  # 正常-晓晓
            "smile": "zh-CN-XiaoxiaoNeural",     # 开心-晓伊
            "think": "zh-CN-XiaoxiaoNeural",      # 思考-云希
            "sad": "zh-CN-XiaoxiaoNeural",      # 悲伤-晓涵
            "angry": "zh-CN-XiaoxiaoNeural",    # 生气-云健
            "shy": "zh-CN-XiaoxiaoNeural"       # 害羞-晓柔
        },
        "rate": "+0%",       # 语速 (-100% 到 +100%)
        "volume": "+0%",     # 音量 (-100% 到 +100%)
        "cache_dir": "tts_cache",  # 缓存目录（相对于游戏目录）
        "auto_play": True    # 自动播放
    }
    
    # ========== TTS管理类 ==========
    class TTSManager:
        def __init__(self):
            self.current_voice = None
            self.is_playing = False
            self.current_audio_file = None
            self.audio_queue = []
            # 获取游戏目录的绝对路径和相对路径
            self.game_dir = renpy.config.gamedir
            self.cache_dir = os.path.join(self.game_dir, TTS_CONFIG["cache_dir"])
            
            # 创建缓存目录
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir)
                print(f"创建TTS缓存目录: {self.cache_dir}")
            
            # 注册语音通道
            renpy.music.register_channel("voice", mixer="voice", loop=False)
            print(f"TTS管理器初始化完成，缓存目录: {self.cache_dir}")
        
        def get_voice_for_emotion(self, emotion):
            """根据情绪获取对应的语音角色"""
            return TTS_CONFIG["voice_mapping"].get(emotion, TTS_CONFIG["voice_mapping"]["normal"])
        
        def get_cache_filename(self, text, voice):
            """生成缓存文件名（基于文本和语音角色的哈希）"""
            import hashlib
            content_hash = hashlib.md5(f"{text}_{voice}".encode()).hexdigest()
            return os.path.join(self.cache_dir, f"{content_hash}.mp3")
        
        def get_renpy_path(self, absolute_path):
            """将绝对路径转换为 Ren'Py 可识别的相对路径"""
            try:
                # 获取相对于游戏目录的路径
                rel_path = os.path.relpath(absolute_path, self.game_dir)
                # 统一使用正斜杠（Ren'Py 的要求）
                rel_path = rel_path.replace("\\", "/")
                print(f"路径转换: {absolute_path} -> {rel_path}")
                return rel_path
            except Exception as e:
                print(f"路径转换失败: {e}")
                return absolute_path
        
       
        def play_audio_sync(self, audio_file):
            try:
                # 1. 确保文件在 game/tts_cache/ 目录
                game_dir = renpy.config.gamedir
                if not audio_file.startswith(game_dir):
                    # 复制文件到 game 目录
                    import shutil
                    dest_dir = os.path.join(game_dir, "tts_cache")
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)
                    dest_file = os.path.join(dest_dir, os.path.basename(audio_file))
                    if not os.path.exists(dest_file):
                        shutil.copy2(audio_file, dest_file)
                    audio_file = dest_file
                # 2. 使用相对路径（相对于 game/）
                rel_path = os.path.relpath(audio_file, game_dir).replace("\\", "/")
                # 3. 使用 voice 语句播放
                renpy.music.play(f"tts_cache/{os.path.basename(audio_file)}", channel="music",loop=False,fadein=0.0,tight=False)     
                # 设置通道属性
                renpy.music.set_volume(1.0, channel="music")
                renpy.music.set_pan(0.0, channel="music")
                print(f"播放成功\n")
            except Exception as e:
                print(f"播放失败: {e}")
        
        def generate_tts_async(self, text, voice, audio_file):
            """异步生成TTS音频"""
            try:
                print(f"开始生成TTS: {text[:50]}...")
                
                # 创建新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def generate():
                    communicate = edge_tts.Communicate(text, voice, 
                                                       rate=TTS_CONFIG["rate"],
                                                       volume=TTS_CONFIG["volume"])
                    await communicate.save(audio_file)
                
                loop.run_until_complete(generate())
                loop.close()
                
                # 验证文件是否生成成功
                if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
                    file_size = os.path.getsize(audio_file)
                    print(f"✅ TTS生成成功: {audio_file} (大小: {file_size} bytes)")
                    return True
                else:
                    print(f"❌ TTS生成失败: 文件为空或不存在")
                    return False
                
            except Exception as e:
                print(f"❌ TTS生成失败: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        def generate_and_play(self, text, emotion):
            """生成并播放TTS语音"""
            if not text or text.strip() == "":
                print("文本为空，跳过TTS")
                return
            
            print(f"\n=== TTS处理 ===")
            print(f"文本: {text[:50]}...")
            print(f"情绪: {emotion}")
            
            voice = self.get_voice_for_emotion(emotion)
            audio_file = self.get_cache_filename(text, voice)
            
            # 如果缓存文件不存在，先生成
            if not os.path.exists(audio_file):
                print(f"生成新的TTS音频...")
                success = self.generate_tts_async(text, voice, audio_file)
                if not success:
                    print("TTS生成失败，跳过播放")
                    return
            else:
                file_size = os.path.getsize(audio_file)
                print(f"使用缓存的TTS音频: {os.path.basename(audio_file)} (大小: {file_size} bytes)")
            
            # 播放音频
            self.play_audio_sync(audio_file)
            print(f"=== TTS处理完成 ===\n")
        
        def stop_audio(self):
            """停止当前播放的音频"""
            renpy.music.stop(channel="voice")
            self.is_playing = False
            print("停止语音播放")
    
    # 全局TTS管理器实例
    tts_manager = TTSManager()
    
    # ========== 讯飞API配置 ==========
    XUNFEI_CONFIG = {
        "api_url": "https://maas-api.cn-huabei-1.xf-yun.com/v2/chat/completions",  # 讯飞API完整地址
        "api_key": "XXX",  # API Key
        "model_id": "XXX",  # 模型ID（从服务管控页面获取）
        "system_prompt": """你是一个开心的AI助手，名字叫小美，是一个嘴甜、心里阳光、会陪伴的人。\n"""+keywords,
        "max_tokens": 4096,
        "temperature": 0.7,
        "timeout": 120
    }
    
    # ========== 讯飞API调用函数（纯requests实现） ==========
    def call_xunfei_api(messages, use_stream=False, extra_body={}):
        """调用讯飞API - 使用requests库"""
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {XUNFEI_CONFIG['api_key']}"
        }
        
        payload = {
            "model": XUNFEI_CONFIG["model_id"],
            "messages": messages,
            "stream": use_stream,
            "temperature": XUNFEI_CONFIG["temperature"],
            "max_tokens": XUNFEI_CONFIG["max_tokens"],
        }
        
        # 合并额外参数
        payload.update(extra_body)
        
        try:
            print(f"发送请求到讯飞API: {XUNFEI_CONFIG['api_url']}")
            
            response = requests.post(
                XUNFEI_CONFIG["api_url"],
                headers=headers,
                json=payload,
                timeout=XUNFEI_CONFIG["timeout"]
            )
            
            if response.status_code == 200:
                if use_stream:
                    # 处理流式响应
                    full_response = ""
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith('data: '):
                                data = line[6:]
                                if data != '[DONE]':
                                    try:
                                        chunk = json.loads(data)
                                        if 'choices' in chunk and len(chunk['choices']) > 0:
                                            delta = chunk['choices'][0].get('delta', {})
                                            content = delta.get('content', '')
                                            if content:
                                                full_response += content
                                    except json.JSONDecodeError:
                                        continue
                    return full_response
                else:
                    # 非流式响应
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    else:
                        print(f"API返回格式错误: {result}")
                        return None
            else:
                print(f"讯飞API请求失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("讯飞API请求超时")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"讯飞API连接错误: {e}")
            return None
        except Exception as e:
            print(f"讯飞API未知错误: {e}")
            return None
    
    # ========== 文本格式化类 ==========
    class FormattedText:
        def __init__(self, text, max_chars_per_line=35, max_lines_per_page=4):
            self.full_text = text
            self.pages = []
            self.current_page = 0
            self.max_chars_per_line = max_chars_per_line
            self.max_lines_per_page = max_lines_per_page
            self._format_text()
        
        def _remove_empty_lines(self, text):
            lines = text.split('\n')
            non_empty_lines = [line for line in lines if line.strip()]
            return '\n'.join(non_empty_lines)
        
        def _wrap_line(self, line):
            if len(line) <= self.max_chars_per_line:
                return [line]
            
            wrapped_lines = []
            for i in range(0, len(line), self.max_chars_per_line):
                wrapped_lines.append(line[i:i+self.max_chars_per_line])
            return wrapped_lines
        
        def _format_text(self):
            if not self.full_text:
                self.pages = [""]
                return
            
            text_no_empty = self._remove_empty_lines(self.full_text)
            original_lines = text_no_empty.split('\n')
            
            all_formatted_lines = []
            for line in original_lines:
                wrapped = self._wrap_line(line)
                all_formatted_lines.extend(wrapped)
            
            current_page_lines = []
            for line in all_formatted_lines:
                current_page_lines.append(line)
                if len(current_page_lines) >= self.max_lines_per_page:
                    page_text = "\n".join(current_page_lines)
                    self.pages.append(page_text)
                    current_page_lines = []
            
            if current_page_lines:
                page_text = "\n".join(current_page_lines)
                self.pages.append(page_text)
            
            if not self.pages:
                self.pages = [""]
        
        def has_next(self):
            return self.current_page < len(self.pages) - 1
        
        def get_current_page(self):
            if self.pages and self.current_page < len(self.pages):
                return self.pages[self.current_page]
            return ""
        
        def next_page(self):
            if self.has_next():
                self.current_page += 1
                return True
            return False
        
        def reset(self):
            self.current_page = 0
        
        def total_pages(self):
            return len(self.pages)
    
    # ========== 聊天管理类 ==========
    class ChatManager:
        def __init__(self):
            self.conversation_history = []
            self.is_loading = False
            self.loading_text = "..."
            self.api_available = True
            self.retry_count = 0
            self.max_retries = 2
            self.current_emotion = "normal"
            self.pending_reply = None
            self.formatted_reply = None
            self.is_formatted_display = False
            
        def add_message(self, role, content):
            self.conversation_history.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().strftime("%H:%M")
            })
            
        def analyze_emotion(self, text):
            text_lower = text.lower()
            
            angry_keywords = ["生气", "愤怒", "可恶", "讨厌", "烦", "烦死了", "滚", "闭嘴", 
                              "气死", "气人", "恼火", "火大", "不满", "抗议", "不行", "绝不",
                              "😠", "😡", "🤬", "打死", "揍", "骂", "恨", "讨厌你"]
            if any(word in text_lower for word in angry_keywords):
                return "angry"
            
            happy_keywords = ["哈哈", "开心", "高兴", "嘻嘻", "😊", "😄", "😂", "🤣", 
                              "耶", "太棒了", "真好", "幸福", "快乐", "兴奋"]
            if any(word in text_lower for word in happy_keywords):
                return "smile"
            
            sad_keywords = ["难过", "伤心", "哭", "😢", "😭", "郁闷", "沮丧", "失落", 
                            "痛苦", "悲伤", "悲哀", "心碎", "绝望"]
            if any(word in text_lower for word in sad_keywords):
                return "sad"
            
            think_keywords = ["想", "觉得", "认为", "思考", "也许", "可能", "大概", 
                              "疑惑", "奇怪", "不懂", "不明白", "为什么", "怎么样",
                              "怎么办", "如何", "? ", "？"]
            if any(word in text_lower for word in think_keywords):
                return "think"
            
            return "normal"
        
        def validate_emotion(self, emotion):
            """验证情绪是否有效"""
            valid_emotions = ["normal", "smile", "think", "sad", "angry", "shy"]
            return emotion in valid_emotions
        
        def parse_json_response(self, response_text):
            """解析JSON响应，返回(文本, 情绪)元组，如果解析失败返回(None, None)"""
            try:
                # 尝试提取JSON部分（处理可能的额外文本）
                json_match = re.search(r'\{[^{}]*"emotion"[^{}]*"text"[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group()                   
                data = json.loads(response_text)
                emotion = data.get("emotion", "normal")
                text = data.get("text", "")
                
                # 验证情绪是否有效
                if self.validate_emotion(emotion) and text:
                    return text, emotion
                else:
                    print(f"无效的情绪值: {emotion}")
                    return text, self.analyze_emotion(text)
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                return response_text, self.analyze_emotion(response_text)
        
        def clean_markdown(self, text):
            """清理Markdown格式符号，保留纯文本内容"""
            if not text:
                return text
            # 移除代码块
            text = re.sub(r'```[\s\S]*?```', '', text)
            text = re.sub(r'`([^`]+)`', r'\1', text)
            # 移除标题标记
            text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
            # 移除粗体
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            text = re.sub(r'__(.+?)__', r'\1', text)
            # 移除斜体
            text = re.sub(r'\*([^*\n]+?)\*', r'\1', text)
            text = re.sub(r'_([^_\n]+?)_', r'\1', text)
            # 移除删除线
            text = re.sub(r'~~(.+?)~~', r'\1', text)
            # 移除链接
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
            # 移除图片
            text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
            # 移除列表标记
            text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
            text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)
            # 移除引用标记
            text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
            # 移除水平线
            text = re.sub(r'^[\-\*\_]{3,}\s*$', '', text, flags=re.MULTILINE)
            # 清理多余的空格和换行
            text = re.sub(r' +', ' ', text)
            text = re.sub(r'\n\s*\n', '\n\n', text)
            return text.strip()
        
        def is_goodbye(self, text):
            text_lower = text.lower().strip()
            goodbye_keywords = ["再见", "拜拜", "88", "bye", "bye bye", "回头见", 
                              "下次聊", "结束", "退出", "关闭", "不聊了", "我走了", 
                              "告辞", "后会有期", "goodbye", "see you"]
            return any(word in text_lower for word in goodbye_keywords)
        
        def get_history_for_api(self):
            """构建API请求的消息历史"""
            messages = [{"role": "system", "content": XUNFEI_CONFIG["system_prompt"]}]
            for msg in self.conversation_history:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            return messages
        
        def send_to_llm_with_json(self, user_message):
            """发送消息到讯飞LLM，要求返回JSON格式，支持重试"""
            self.add_message("user", user_message)
            self.is_loading = True
                       
            loading_texts = ["思考中", "正在输入", "认真回复", "组织语言", "等待响应"]
            
            # 尝试最多3次
            for attempt in range(3):
                self.loading_text = f"{random.choice(loading_texts)}... (尝试 {attempt + 1}/3)"
                
                try:
                    print(f"\n=== 讯飞API请求 (JSON模式, 尝试 {attempt + 1}/3) ===")
                    
                    # 使用讯飞API，启用JSON模式
                    messages = self.get_history_for_api()
                    
                    # 添加JSON格式要求到用户消息
                    messages[-1]["content"] = user_message + "\n" + keywords
                    
                    extra_body = {
                        "response_format": {"type": "json_object"},  # 启用JSON模式
                        "search_disable": True  # JSON模式下关闭搜索
                    }
                    
                    raw_reply = call_xunfei_api(messages, use_stream=False, extra_body=extra_body)
                    
                    if raw_reply:
                        print(f"原始回复: {raw_reply[:200]}...")
                        
                        # 解析JSON
                        text, emotion = self.parse_json_response(raw_reply)
                        
                        if text and emotion:
                            # JSON解析成功
                            text = self.clean_markdown(text)
                            self.current_emotion = emotion
                            self.add_message("assistant", text)
                            self.is_loading = False
                            self.api_available = True
                            
                            self.formatted_reply = FormattedText(text, max_chars_per_line=35, max_lines_per_page=4)
                            self.is_formatted_display = True
                            
                            print(f"✅ JSON解析成功 - 情绪: {emotion}, 文本: {text[:50]}...")
                            return text
                        else:
                            print(f"❌ JSON解析失败 (尝试 {attempt + 1}/3)")
                            if attempt == 2:  # 最后一次尝试失败
                                print("使用离线方案")
                                return self.local_response(user_message)
                            continue
                    else:
                        print("API返回为空")
                        if attempt == 2:
                            return self.local_response(user_message)
                        continue
                        
                except Exception as e:
                    print(f"未知错误: {e}")
                    if attempt == 2:
                        return self.local_response(user_message)
                    continue
            
            self.is_loading = False
            return self.local_response(user_message)
        
        def local_response(self, user_message):
            """离线方案：基于关键词匹配的回复"""
            self.is_loading = False
            
            user_lower = user_message.lower()
            
            if "你好" in user_lower or "hi" in user_lower:
                reply = "你好呀！很高兴见到你！今天过得怎么样？"
                self.current_emotion = "smile"
            elif "名字" in user_lower:
                reply = "我叫小美，是你的AI聊天助手~很高兴认识你！"
                self.current_emotion = "smile"
            elif "谢谢" in user_lower:
                reply = "不客气！能帮到你就好~"
                self.current_emotion = "smile"
            elif "开心" in user_lower:
                reply = "真为你开心！保持好心情很重要哦~"
                self.current_emotion = "smile"
            elif "难过" in user_lower or "伤心" in user_lower:
                reply = "抱抱，有什么不开心的事可以跟我说说..."
                self.current_emotion = "sad"
            elif "喜欢" in user_lower:
                reply = "我也很喜欢和你聊天呢~"
                self.current_emotion = "smile"
            elif "故事" in user_lower:
                reply = "曾经有一个小村庄，住着一位善良的老人..."
                self.current_emotion = "think"
            elif "生气" in user_lower or "愤怒" in user_lower:
                reply = "哼！你为什么要生气？有什么可以好好说嘛..."
                self.current_emotion = "angry"
            elif "讨厌" in user_lower or "烦" in user_lower:
                reply = "看样子你心情很不好，我安静地陪着你吧。"
                self.current_emotion = "angry"
            elif "害羞" in user_lower or "不好意思" in user_lower:
                reply = "诶嘿...被你发现我有点害羞了呢~"
                self.current_emotion = "shy"
            else:
                replies = [
                    "嗯，我明白。能多说一些吗？",
                    "原来是这样啊，然后呢？",
                    "我在认真听你说呢~",
                    "这很有意思，能聊聊更多吗？",
                    "我理解你的感受。"
                ]
                reply = random.choice(replies)
                self.current_emotion = "think"
            
            reply = self.clean_markdown(reply)
            self.add_message("assistant", reply)
            
            self.formatted_reply = FormattedText(reply, max_chars_per_line=35, max_lines_per_page=4)
            self.is_formatted_display = True
            
            return reply
        
        def clear_history(self):
            self.conversation_history = []
            welcome = "✨ 对话已清空！让我们重新开始聊天吧~ ✨"
            self.add_message("assistant", welcome)
            self.api_available = True
            self.current_emotion = "normal"
            self.formatted_reply = None
            self.is_formatted_display = False
    
    chat_manager = ChatManager()
    
    def test_api_connection():
        """测试讯飞API连接"""
        try:
            test_messages = [
                {"role": "system", "content": "你是测试助手"},
                {"role": "user", "content": "你好"}
            ]
            
            reply = call_xunfei_api(test_messages, use_stream=False)
            
            if reply:
                renpy.notify(f"✅ 讯飞API连接成功！响应: {reply[:30]}...")
                chat_manager.api_available = True
                chat_manager.current_emotion = "smile"
            else:
                renpy.notify(f"❌ API连接失败")
                chat_manager.api_available = False
        except Exception as e:
            renpy.notify(f"❌ 连接失败: {str(e)[:50]}")
            chat_manager.api_available = False
    
    def test_tts():
        """测试TTS功能"""
        try:
            test_text = "你好，我是小美，很高兴认识你！"
            tts_manager.generate_and_play(test_text, "smile")
            renpy.notify("✅ TTS测试已启动，请听语音播放")
        except Exception as e:
            renpy.notify(f"❌ TTS测试失败: {str(e)[:50]}")
            import traceback
            traceback.print_exc()

# 显示立绘的函数
init python:
    def show_bot_with_emotion():
        emotion = chat_manager.current_emotion
        if emotion == "smile":
            renpy.show("bot smile", at_list=[bot_center])
        elif emotion == "sad":
            renpy.show("bot sad", at_list=[bot_center])
        elif emotion == "think":
            renpy.show("bot think", at_list=[bot_center])
        elif emotion == "angry":
            renpy.show("bot angry", at_list=[bot_center])
        elif emotion == "shy":
            renpy.show("bot shy", at_list=[bot_center])
        else:
            renpy.show("bot normal", at_list=[bot_center])

screen persistent_menu():
    frame:
        xalign 1.0
        yalign 0.0
        xoffset -20
        yoffset 20
        background "#2c5f4aee"
        xpadding 12
        ypadding 8
        
        vbox:
            spacing 8
            
            textbutton "📔 菜单":
                text_size 20
                text_color "#e8d5a3"
                action Show("game_menu_simple")
            
            if chat_manager.api_available:
                text "🌐 在线" size 12 color "#9dd4f0"
            else:
                text "💻 离线" size 12 color "#e8a639"

screen game_menu_simple():
    modal True
    
    frame:
        xalign 0.5
        yalign 0.5
        xsize 350
        ysize 320
        background "#1a3a2e"
        
        vbox:
            xalign 0.5
            yalign 0.5
            spacing 15
            
            text "菜单选项" size 20 color "#e8d5a3" xalign 0.5
            
            textbutton "继续聊天":
                text_size 16
                action Hide("game_menu_simple")
                xalign 0.5
            
            textbutton "清空对话历史":
                text_size 16
                action [Function(chat_manager.clear_history), Hide("game_menu_simple")]
                xalign 0.5
            
            textbutton "测试API连接":
                text_size 16
                action [Function(test_api_connection), Hide("game_menu_simple")]
                xalign 0.5
            
            textbutton "🔊 测试语音":
                text_size 16
                action [Function(test_tts), Hide("game_menu_simple")]
                xalign 0.5
            
            textbutton "停止语音":
                text_size 16
                action Function(tts_manager.stop_audio)
                xalign 0.5
            
            textbutton "退出游戏":
                text_size 16
                action Quit(confirm=True)
                xalign 0.5

# 添加TTS设置屏幕
screen tts_settings():
    modal True
    
    frame:
        xalign 0.5
        yalign 0.5
        xsize 400
        ysize 300
        background "#1a3a2e"
        
        vbox:
            xalign 0.5
            yalign 0.5
            spacing 15
            
            text "🔊 语音设置" size 20 color "#e8d5a3" xalign 0.5
            
            text "语速: " + TTS_CONFIG["rate"] size 14
            bar value VariableValue("tts_rate_value", 0, 200) xsize 300:
                style "slider"
                changed tts_update_rate
            
            text "音量: " + TTS_CONFIG["volume"] size 14
            bar value VariableValue("tts_volume_value", 0, 200) xsize 300:
                style "slider"
                changed tts_update_volume
            
            textbutton "关闭":
                text_size 16
                action Hide("tts_settings")
                xalign 0.5

init python:
    def tts_update_rate(value):
        rate_val = int((value - 100) / 100 * 100)  # 转换 -100 到 100
        TTS_CONFIG["rate"] = f"{rate_val:+d}%"
    
    def tts_update_volume(value):
        volume_val = int((value - 100) / 100 * 100)
        TTS_CONFIG["volume"] = f"{volume_val:+d}%"

# ========================================
# 3. 主游戏流程 - 连续对话模式
# ========================================

label start:
    scene bg room
    show bot normal at bot_center
    
    show screen persistent_menu
    
    # 播放欢迎语音（可选）
    $ tts_manager.generate_and_play("你好呀！我是小美，很高兴认识你~", "smile")
    bot "你好呀！我是小美，很高兴认识你~"
    
    $ tts_manager.generate_and_play("有什么想聊的吗？我会一直在这里陪着你。", "normal")
    bot "有什么想聊的吗？我会一直在这里陪着你。"
    
    call continuous_chat

label continuous_chat:
    $ chat_manager.current_emotion = "normal"
    $ show_bot_with_emotion()
    
    $ user_input = renpy.input("说点什么吧... (输入'再见'结束聊天)", length=200)
    
    if user_input is False or user_input is None:
        jump continuous_chat
    
    $ user_input = str(user_input).strip()
    
    if user_input == "":
        "请输入内容..."
        jump continuous_chat
    
    if chat_manager.is_goodbye(user_input):
        c "[user_input]"
        $ tts_manager.generate_and_play("再见啦~期待下次和你聊天！", "normal")
        bot "再见啦~期待下次和你聊天！"
        $ renpy.full_restart()
        return
    
    c "[user_input]"
    
    $ chat_manager.is_loading = True
    show expression Solid("#00000033", xysize=(400, 600)) as thinking at bot_center
    
    python:
        # 使用JSON模式发送消息到讯飞API
        reply = chat_manager.send_to_llm_with_json(user_input)
    
    hide thinking
    
    $ show_bot_with_emotion()
    
    call display_formatted_message
    
    jump continuous_chat

label display_formatted_message:
    python:
        formatted = chat_manager.formatted_reply
        total_pages = formatted.total_pages()
        # 获取完整的回复文本用于TTS（不分页）
        full_reply_text = formatted.full_text
        emotion = chat_manager.current_emotion
    
    # 在显示文本之前同时播放TTS语音
    $ tts_manager.generate_and_play(full_reply_text, emotion)
    $ renpy.pause(0.5)

    $ current_text = formatted.get_current_page()
    $ current_page_num = formatted.current_page + 1
    
    if total_pages > 1:
        bot "[current_text]"
    else:
        bot "[current_text]"
    
    while formatted.has_next():
        $ formatted.next_page()
        $ current_text = formatted.get_current_page()
        $ current_page_num = formatted.current_page + 1
        
        if total_pages > 1:
            bot "[current_text]"
        else:
            bot "[current_text]"
    
    $ formatted.reset()
    $ chat_manager.is_formatted_display = False
    $ chat_manager.formatted_reply = None
    return

label main_menu_return:
    $ renpy.full_restart()
    return