"""설정된 OpenAI API만 사용한다. API 키·응답 오류 본문은 화면이나 로그에 노출하지 않는다."""

import json
import os
import socket
import urllib.error
import urllib.request

from apps.core.models import AppSetting
from .services import prompt

KEY_SETTING = "writing_openai_key"
MODEL_SETTING = "writing_openai_model"


def configuration():
    key = AppSetting.get(KEY_SETTING) or os.environ.get("OPENAI_API_KEY", "")
    model = AppSetting.get(MODEL_SETTING) or os.environ.get(
        "WRITING_AI_MODEL", "gpt-4.1-mini"
    )
    return key, model


class AIError(Exception):
    pass


def generate(draft):
    key, model = configuration()
    if not key:
        raise AIError(
            "AI 연결 설정이 없습니다. 작성 설정에서 연결하거나 AI 요청문을 복사해 사용하세요."
        )
    data = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": '한국어 글쓰기 편집자입니다. 주어진 자료에 근거한 초안을 JSON으로 출력합니다. 형식: {"title": "제목", "body_markdown": "Markdown 본문", "description": "소개 한 문장", "tags": ["태그"]}. 제공되지 않은 사실은 [[확인할 내용]]으로 표시합니다.',
            },
            {"role": "user", "content": prompt(draft)},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 6000,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(data).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.loads(response.read(2_000_000))
        message = result["choices"][0]["message"]["content"]
        parsed = json.loads(message)
    except urllib.error.HTTPError as exc:
        reasons = {
            401: "API 키를 확인하세요.",
            403: "API 접근 권한을 확인하세요.",
            429: "API 사용 한도·결제 상태를 확인하거나 잠시 후 다시 시도하세요.",
        }
        raise AIError(
            reasons.get(
                exc.code,
                "AI 서비스가 요청을 처리하지 못했습니다. 원고는 변경하지 않았습니다.",
            )
        ) from None
    except (urllib.error.URLError, TimeoutError, socket.timeout):
        raise AIError(
            "AI 서비스 연결이 지연되거나 차단됐습니다. 원고는 유지됩니다. AI 요청문 복사로도 진행할 수 있습니다."
        ) from None
    except (ValueError, KeyError, IndexError, TypeError):
        raise AIError(
            "AI 응답 형식을 읽지 못했습니다. 원고는 변경하지 않았습니다."
        ) from None
    if (
        not isinstance(parsed, dict)
        or not isinstance(parsed.get("body_markdown"), str)
        or not parsed["body_markdown"].strip()
        or len(parsed["body_markdown"]) > 120000
    ):
        raise AIError("AI가 유효한 본문을 반환하지 않았습니다. 다시 시도하세요.")
    for field in ["title", "description"]:
        if field in parsed and not isinstance(parsed[field], str):
            raise AIError("AI가 유효한 제목·소개를 반환하지 않았습니다.")
    tags = parsed.get("tags", [])
    if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
        tags = []
    return {
        "title": (parsed.get("title") or draft.content.title)[:160],
        "body": parsed["body_markdown"].strip(),
        "description": parsed.get("description", "")[:300],
        "tags": ", ".join(t.strip().lstrip("#")[:30] for t in tags[:10] if t.strip()),
    }
