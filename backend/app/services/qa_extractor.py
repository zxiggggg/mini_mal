import json
import os
from typing import Dict, List

from openai import AsyncOpenAI, AuthenticationError


class QAExtractionError(Exception):
    pass


QA_SYSTEM_PROMPT = """你是一个面试复盘助手。给定一段面试转写文本和说话人角色标注（面试官/面试者），提取所有的问答对。

转写文本格式：[说话人 标签] 内容
角色标注格式：{"标签1": "interviewer", "标签2": "interviewee", ...}

规则：
1. 面试官的连续发言 = 一个问题
2. 面试者紧随其后的发言 = 对应回答
3. 一个问可能对应多段回答（面试官追问后面试者补充），合并为一条
4. 跳过"好的""嗯""接下来"这类过渡语

返回严格的 JSON 数组，每个元素包含 question 和 answer 两个字段。不要包含任何其他内容。"""


async def extract_qa_pairs(text: str, speaker_labels: Dict[str, str]) -> List[dict]:
    """Extract Q&A pairs from labeled transcript using OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise QAExtractionError("请检查 OpenAI API Key 配置")

    client = AsyncOpenAI(api_key=api_key)

    user_content = f"角色标注：{json.dumps(speaker_labels, ensure_ascii=False)}\n\n转写文本：\n{text}"

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
        )
        content = response.choices[0].message.content or "[]"
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            if content.startswith("json\n"):
                content = content[5:]

        pairs = json.loads(content)
        return pairs

    except AuthenticationError:
        raise QAExtractionError("请检查 OpenAI API Key 配置")
    except json.JSONDecodeError:
        raise QAExtractionError("问答对提取失败：AI 返回格式异常，请重试")
    except Exception as e:
        raise QAExtractionError(f"问答对提取失败: {str(e)}")
