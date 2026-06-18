import json
import os

from openai import AsyncOpenAI, AuthenticationError


class SuggestionError(Exception):
    pass


SYSTEM_PROMPT = """你是一个面试教练。给定一个面试问答对（面试官的问题 + 面试者的回答），给出 1-3 条简短、具体、可执行的改进建议。

每条建议不超过两句话。聚焦于：
- 回答结构是否清晰
- 是否用具体例子支撑
- 表述是否简洁有力

返回严格的 JSON 字符串数组，例如：["建议1", "建议2"]。不要包含任何其他内容。"""


async def generate_suggestions(question: str, answer: str) -> list[str]:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise SuggestionError("请检查 OpenAI API Key 配置")

    client = AsyncOpenAI(api_key=api_key)

    user_content = f"面试官问题：{question}\n\n面试者回答：{answer}"

    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.5,
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

        suggestions = json.loads(content)
        if not isinstance(suggestions, list):
            raise SuggestionError("AI 返回格式异常")
        return suggestions[:3]

    except AuthenticationError:
        raise SuggestionError("请检查 OpenAI API Key 配置")
    except json.JSONDecodeError:
        raise SuggestionError("建议生成失败：AI 返回格式异常，请重试")
    except SuggestionError:
        raise
    except Exception as e:
        raise SuggestionError(f"建议生成失败: {str(e)}")
