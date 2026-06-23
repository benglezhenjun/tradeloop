"""Agents 共享基础设施。"""

from __future__ import annotations

import json

from app.services import llm

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
    for idx, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            _, end = decoder.raw_decode(text[idx:])
            return text[idx : idx + end]
        except json.JSONDecodeError:
            continue
    return text.strip()
