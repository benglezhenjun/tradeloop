"""
LLM 客户端封装 (V4)

设计原则：
- 供应商无关：所有兼容 OpenAI /v1/chat/completions 接口的服务都能用
- 切换供应商只改 config/local.toml，代码零修改
- 调用失败时抛出明确异常，由上层 Agent 决定如何降级处理
"""

from openai import OpenAI

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER


def is_configured() -> bool:
    """检查 LLM 是否已配置（api_key 不为空）。"""
    return bool(LLM_API_KEY and LLM_API_KEY.strip())


def get_status() -> dict:
    """返回当前 LLM 配置状态（供前端展示）。"""
    return {
        "configured": is_configured(),
        "provider": LLM_PROVIDER,
        "model": LLM_MODEL,
        "base_url": LLM_BASE_URL,
    }


def _get_client() -> OpenAI:
    """返回配置好的 OpenAI 兼容客户端。"""
    if not is_configured():
        raise ValueError(
            "LLM 未配置。请在 config/local.toml 中填写 [llm] api_key。"
        )
    return OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        timeout=120.0,
    )


def chat(messages: list[dict], max_tokens: int = 1000) -> str:
    """
    发送对话请求，返回模型回复文本。

    messages 格式：
        [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

    失败时抛出异常，由调用方捕获处理。
    """
    client = _get_client()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,  # type: ignore[arg-type]
        max_tokens=max_tokens,
        temperature=0.3,    # 分析类任务偏低温度，减少幻觉
    )
    content = response.choices[0].message.content
    return content or ""
