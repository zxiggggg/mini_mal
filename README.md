# mini_mal — 面试复盘工具

上传或录制面试录音，自动转写、提取问答对、生成改进建议。BYOK（自备 OpenAI Key）+ Docker Compose 一键部署，数据全在本机。

## 功能

1. **录音输入** — 上传音频文件，或浏览器直接录制
2. **语音转写** — OpenAI gpt-4o-transcribe 转写，支持说话人分离
3. **角色标注** — 手动标注说话人为面试官 / 面试者
4. **问答提取** — 自动提取面试官问题与面试者回答
5. **改进建议** — 每个问答对生成 1-3 条复盘建议
6. **数据导出** — 支持 JSON / CSV / TXT 三种格式导出
7. **数据删除** — 删除录音时联动清理所有关联数据

## 快速开始

### 前提

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- OpenAI API Key（[获取](https://platform.openai.com/api-keys)）

### 启动

```bash
git clone https://github.com/zxiggggg/mini_mal.git
cd mini_mal
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY=sk-xxx
docker compose up
```

浏览器打开 http://localhost:5173

### 使用流程

上传/录制 → 转写 → 标注角色 → 提取问答对 → 生成建议 → 导出

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12 + FastAPI + SQLAlchemy + SQLite |
| 前端 | React 19 + TypeScript 5.6 + Vite + Tailwind CSS |
| ASR | OpenAI gpt-4o-transcribe |
| LLM | OpenAI GPT-4o |
| 部署 | Docker Compose |

## 截图

> TODO: 启动应用后截图四步流程：录音/上传 → 转写 → 问答对 → 建议
