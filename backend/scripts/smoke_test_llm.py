"""AI_CLOUD_API_KEY(학교 AI Cloud 게이트웨이) 연결 스모크 테스트.

에이전트(Rubric/Grading/Chatting) 구조에 엮기 전에, LLM 게이트웨이 호출 자체가
정상 동작하는지만 먼저 확인한다 (0단계의 bareun 스모크 테스트와 같은 목적).
실제 채점/루브릭 프롬프트 설계는 2단계 이후 별도로 진행한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.services.llm_client import chat_completion  # noqa: E402


def main() -> None:
    if not settings.ai_cloud_api_key:
        raise SystemExit("AI_CLOUD_API_KEY가 설정되지 않았습니다. 프로젝트 루트 .env를 확인하세요.")

    reply = chat_completion(
        [
            {
                "role": "user",
                "content": (
                    "너는 대입 논술 채점 보조 AI다. 연결 테스트다. "
                    "정확히 한 문장으로, 네가 논술 채점/첨삭을 도울 준비가 되었다고 한국어로 답해라."
                ),
            }
        ]
    )

    print("=== base_url ===")
    print(settings.ai_cloud_base_url)
    print("=== 모델 ===")
    print(settings.ai_cloud_model)
    print("=== 응답 ===")
    print(reply)


if __name__ == "__main__":
    main()
