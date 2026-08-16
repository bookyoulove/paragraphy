# Agent package

Paragraphy의 LangGraph 에이전트 패키지입니다. 백엔드 애플리케이션과 분리해 그래프,
상태/입출력 계약, 외부 연동 경계를 독립적으로 관리합니다.

```text
src/agent/
├── graphs/         그래프 조립과 노드 연결
├── schemas/        에이전트별 Pydantic 입출력 모델과 LangGraph 상태
├── nodes/          여러 그래프가 공유하는 정책 노드(가드레일 등)
├── integrations/   RAG·맞춤법 등 외부 시스템 어댑터
├── model.py        init_chat_model 및 structured output 경계
└── config.py       .env 기반 모델 설정
```

## 계약과 환경 설정

백엔드와 에이전트 사이의 공개 입출력 계약은 `shared.schema`와
`shared.protocol`을 직접 사용합니다. 내부 LangGraph 상태도 `TypedDict`가 아니라
Pydantic `BaseModel`로 두며, 각 state의 `request` 필드에 shared 또는 agent 입력
계약을 보유합니다. RAG 컨텍스트와 노드별 결과는 state의 나머지 필드로 누적합니다.
structured output용 세부 모델은 이 패키지의 `schemas/`에 둡니다. 그래프를 직접 호출할
때도 개별 필드를 평평하게 넘기지 않고 다음처럼 `request`에 입력 계약을 넣습니다.

```python
await grading_app.ainvoke({"request": analysis_request})
await rubric_app.ainvoke({"request": rubric_generation_request})
await feedback_app.ainvoke({"request": FeedbackInput(essay_text=text)})
```

모델 게이트웨이는 OpenAI-compatible API로 연결합니다. `.env`에 다음을 설정합니다.

- `AI_CLOUD_API_KEY` (또는 `OPENAI_API_KEY`)
- `AI_CLOUD_BASE_URL` (또는 `OPENAI_BASE_URL`)
- `AI_CLOUD_MODEL` (선택)
- `BAREUN_API_KEY` (맞춤법 검사를 사용할 때 필수)
- `BAREUN_HOST`, `BAREUN_PORT` (선택, 기본값 `api.bareun.ai:443`)

`bareunpy`와 `chromadb`는 agent 패키지 의존성으로 선언되어 있습니다. agent 전용
환경을 새로 만들 때는 agent 디렉터리에서 `uv sync`를 실행하면 됩니다. 백엔드에서
사용할 때는 백엔드의 `uv.lock`도 agent 패키지를 editable dependency로 포함해야 합니다.

JSON 결과를 프롬프트로 강제하거나 직접 파싱하지 않고, 각 LLM 그래프의 Pydantic 출력
모델을 `with_structured_output()`에 전달합니다.

## bareunpy와 `shared.schema.grammar`의 호환성 기록

현재 feedback graph는 bareunpy 응답을 `shared.schema.grammar.GrammarResult`로
변환하고, grading output도 같은 타입을 계약으로 사용합니다. 다만 grading graph와
feedback graph를 하나의 실행 경로로 합치는 작업은 아직 별도 과제입니다.

bareunpy protobuf 응답의 `CorrectErrorResponse` 필드는 `GrammarResult`와 거의
같습니다.

| 항목                  | bareunpy Python SDK                                                                                                          | `shared.schema.grammar` | 현재 처리                                             |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ----------------------------------------------------- |
| 응답 전체             | `origin`, `revised`, `revised_blocks`, `whitespace_cleanup_ranges`, `revised_sentences`, `helps`, `language`, `tokens_count` | 동일한 필드             | Pydantic 모델로 변환                                  |
| `RevisedBlock.origin` | `str` (현재 `Corrector` Python 응답에서 관찰됨; 저수준 protobuf는 `TextSpan`일 수 있음)                                      | `str`                   | 문자열을 우선 사용하고 `TextSpan.content`도 호환 처리 |
| `Revision`            | `revised`, `score`, `category`, `help_id`                                                                                    | 동일한 필드             | enum 값을 변환                                        |
| `ReviseHelp`          | `id`, `category`, `comment`, `examples`, `rule_article`                                                                      | 동일한 필드             | map value를 변환                                      |
| `CleanUpRange`        | `offset`, `length`, 중첩 enum `position`                                                                                     | 동일한 필드/값          | enum 값을 변환                                        |

현재 `Corrector` Python SDK에서 관찰한 응답은 `origin: str`이므로 `shared`의
`origin: str`와 직접 호환됩니다. 다만 저수준 protobuf 정의가 `TextSpan`인 버전이나
API를 직접 다루는 경로에서는 `begin_offset`과 `length`가 존재할 수 있습니다. 이후
UI나 문장 단위 diff에서 offset이 필요해질 때만 `shared.schema.grammar`를 span 모델로
확장하면 됩니다.

`RevisionCategory.GRAMMER`처럼 SDK와 shared에 함께 존재하는 명칭의 오탈자는 지금
그대로 매핑됩니다. 공용 스키마에서 이름을 고칠 때는 저장된 JSON과 API 호환성
마이그레이션을 함께 검토해야 합니다.

-> TextSpan을 구현함

### 에이전트 내부 structured output과 shared 계약의 차이

- `agent.schemas.rubric.RubricSuggestion.max_score`는 생성 프롬프트의 내부 정책
  필드입니다. `shared.schema.rubric.Rubric`에는 이 필드가 없으므로 공개 어댑터에서
  제거합니다.
- `agent.schemas.grading.CriterionScore.max_score`와 `total_score`도 내부 채점
  상태용입니다. `shared.schema.analysis.CriteriaScore`에는 `max_score`가 없으므로
  변환 시 제외하고, 총점은 현재 그래프 상태에만 둡니다.
- `shared.schema.analysis.AnalysisResult.grammar_result`는 필수이므로, 문법 그래프가
  채점 그래프에 아직 결합되지 않은 현재 단계에서는 `GrammarResult`의 빈 호환값을
  사용합니다. feedback graph가 생성한 실제 결과를 최종 AnalysisResult에 연결하는
  것은 별도의 후속 작업입니다.

## 확인이 필요한 항목

- 실제 `BAREUN_API_KEY`로 `check_spelling()`을 한 번 호출해 protobuf → Pydantic
  변환을 통합 테스트해야 합니다. 현재 코드에는 API 키를 하드코딩하지 않습니다.
- 실제 OpenAI-compatible 게이트웨이에 연결해 `RubricGenerationOutput`,
  `GradingOutput`, `PolishOutput` 각각의 `with_structured_output()` 호출이 해당
  게이트웨이에서 지원되는지 확인해야 합니다. 게이트웨이가 JSON Schema 방식을
  지원하지 않으면 `agent/model.py`에서 `method="function_calling"`으로 바꾸는
  선택을 검토합니다.
- 현재 확인한 bareun Python SDK의 `origin: str` 응답이 사용하는 SDK 버전에서
  계속 유지되는지, nested block에도 동일한 구조가 적용되는지 버전 업그레이드 때
  회귀 확인해야 합니다.
- `shared.schema.grammar`의 span offset이 필요해지는 시점에 위 계약을 확장합니다.
- Chroma 데이터가 필요하면 `agent/chroma_data`가 생성되며, 배포 환경에서는 해당
  디렉터리의 영속 볼륨과 인덱스 시드를 별도로 준비해야 합니다.
