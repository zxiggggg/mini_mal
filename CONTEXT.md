# 面试复盘工具（mini_mal）

个人开源工具，帮助用户录制/上传面试录音，自动转写、提取问答对并生成改进建议。

## Language

### 核心概念

**面试录音（Interview Recording）**：
用户输入的原始音频，来源分两类。

**录音来源（Recording Source）**：
- **视频会议录制**：来自 Zoom/腾讯会议/飞书等，自带说话人分离能力
- **直接录音**：手机录音机或电脑麦克风录制的单声道混合音频
_Avoid_：双轨音频、麦克风录制

**转写（Transcription）**：
通过 OpenAI Whisper / GPT-4o Transcribe 将语音转为文本。用户可以手动编辑转写结果修正术语错误。
_Avoid_：ASR结果、语音识别

**说话人分离（Speaker Separation / Diarization）**：
识别"谁在说话"的过程。视频会议来源用会议软件自带分离；直接录音用 GPT-4o Transcribe with Diarization。分离后的角色标签由用户手动调整。
_Avoid_：角色识别、声纹识别

**角色标注（Speaker Label）**：
用户手动将说话人标记为"面试官"或"面试者"。
_Avoid_：角色分离

**问答对（Q&A Pair）**：
从转写文本中提取的一组"面试官问题 → 面试者回答"。一个录音可包含多个问答对。
_Avoid_：对话片段、访谈记录

**复盘建议（Review Suggestion）**：
每个问答对给出 1-3 条简短改进建议，一次性生成，不支持追问。
_Avoid_：评分、打分、反馈

### 部署

**BYOK（Bring Your Own Key）**：
用户自备 OpenAI API Key，填入 .env 后应用启动。Key 未配置时后端正常启动，首次上传录音时前端报错提示。
_Avoid_：托管 Key、统一计费

**自部署（Self-Hosted）**：
通过 Docker Compose 一键启动（前端+后端+SQLite），全在本机运行。开发者不提供在线 Demo 或云端服务。
_Avoid_：SaaS、云端部署
