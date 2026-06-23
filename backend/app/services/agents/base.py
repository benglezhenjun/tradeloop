"""Agents 共享基础设施。"""

from __future__ import annotations

import json
import logging

from app.services import llm

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "你是一个 A 股市场分析助手。分析要专业、简洁、直接，"
    "不预测股价涨跌，不给出明确买卖建议，只描述现象和可能成因。"
    "用中文回复，使用 Markdown 格式。"
)

_PLAN_SYSTEM_PROMPT = (
    "你是一个 A 股交易计划助手。根据提供的数据生成三套交易方案。"
    "严格按要求的 JSON 格式输出，不要输出任何 JSON 之外的文字。"
    "不预测股价，方案仅供参考。"
)

_ERROR_PREFIX = "> ⚠️ 该部分分析生成失败："


def _safe_llm_call(prompt: str, *, max_tokens: int = 600, system_prompt: str = _SYSTEM_PROMPT) -> str:
    try:
        return llm.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
    except Exception as exc:
        return f"{_ERROR_PREFIX} {exc}"


def _extract_first_json_payload(text: str) -> str:
    decoder = json.JSONDecoder()
    first_start: str | None = None
    for idx, char in enumerate(text):
        if char not in "[{":
            continue
        if first_start is None:
            first_start = char
        try:
            _, end = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        payload = text[idx : idx + end]
        # 截断检测：最外层以 '[' 开头却只解出一个内部对象 '{' → 多半是 max_tokens 截断的数组，
        # 不能把数组里第一个对象当成正常结果返回，否则会掩盖真实截断
        if first_start == "[" and payload.lstrip().startswith("{"):
            logger.warning("LLM JSON 疑似被截断：期望数组却只解析出单个对象，按解析失败处理")
            break
        return payload
    return text.strip()
