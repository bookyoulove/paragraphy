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
- `AI_CLOUD_GRADING_TEMPERATURE` (선택, Gemini 3.1 계열 기본 `0.8`; 그 외 모델은 미전송, 비워 두면 게이트웨이 기본값 사용)
- `AI_CLOUD_GRADING_REPLICAS` (선택, 기본 `3`; 채점 요청을 병렬 생성할 횟수)
- `BAREUN_API_KEY` (맞춤법 검사를 사용할 때 필수)
- `BAREUN_HOST`, `BAREUN_PORT` (선택, 기본값 `api.bareun.ai:443`)

`bareunpy`와 `chromadb`는 agent 패키지 의존성으로 선언되어 있습니다. agent 전용
환경을 새로 만들 때는 agent 디렉터리에서 `uv sync`를 실행하면 됩니다. 백엔드에서
사용할 때는 백엔드의 `uv.lock`도 agent 패키지를 editable dependency로 포함해야 합니다.

JSON 결과를 프롬프트로 강제하거나 직접 파싱하지 않고, 각 LLM 그래프의 Pydantic 출력
모델을 `with_structured_output()`에 전달합니다.

채점 그래프는 기본적으로 동일한 입력을 세 번 비동기로 병렬 생성하고, 각 채점 항목의
중위값을 최종 점수로 사용합니다. 설명과 근거는 중위 점수 벡터에 가장 가까운 실행의
결과를 대표값으로 사용합니다. `AI_CLOUD_GRADING_REPLICAS=1`로 단일 생성과 비교할 수
있으며, Gemini 3.1 계열에는 기본 `0.8`을 적용합니다. GPT 계열이나 Gemini 3.5/3.6,
Anthropic 계열처럼 temperature를 지원하지 않는 것으로 확인된 모델은 기본적으로 해당
파라미터를 보내지 않습니다. 별도로 지원 여부를 확인한 모델은
`AI_CLOUD_GRADING_TEMPERATURE`에 값을 명시할 수 있습니다.

## 채점 모델 벤치마크

`eval_models.example.json`을 `eval_models.json`으로 복사한 뒤, gitignore된
`eval_models.json`에 모델·base URL·temperature 후보를 기록합니다. 이후 NIKL 골든셋으로
다음 명령을 실행합니다. 기본값은 Q4~Q9에서 균등하게 뽑은 12건이며,
비용을 확인한 후 `--limit 0`으로 전체 데이터셋을 실행할 수 있습니다.

```bash
uv run --package agent --group dev python agent/scripts/evaluate_grading.py --limit 12
```

이 스크립트는 후보와 실행 조합마다 별도 프로세스를 띄워 모델 캐시가 섞이지 않게 하고,
DeepEval 사용자 정의 metric으로 두 명의 사람 채점 결과와 항목별 중위값을 비교합니다.
골든셋의 `con1`~`org2` 준거명은 원본에 codebook이 포함되어 있지 않으므로, 최종 모델
선정에서는 총점 MAE와 구조화 출력 성공률을 우선 확인해야 합니다. API 키는 후보 JSON에
넣지 말고 `api_key_env`로 환경변수 이름만 지정합니다.

벤치마크가 끝나면 다음 명령으로 결과를 Plotly 기반 브라우저용 HTML 리포트로 변환할
수 있습니다. 출력은 gitignore된 `dataset/` 아래에 생성되며, Plotly JavaScript를 파일에
포함하므로 네트워크 없이도 열 수 있습니다.

```bash
uv run --package agent --group dev python agent/scripts/visualize_grading.py
```

리포트에는 항목별 MAE, 총점 MAE, 구조화 출력 성공률, 정확도-지연시간 산점도와
MAE 기준 정렬 표가 포함됩니다. Plotly의 hover·zoom·pan·범례 토글을 사용할 수 있고,
후보 조합이 많을 때 그래프와 표를 가로로 스크롤할 수 있습니다. 산점도 점에 마우스를
올리면 모델·temperature·replicas를 확인할 수 있습니다.

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

## Observability & 프롬프트 관리 (Langfuse)

`.env`에 아래 키가 있으면 자동으로 활성화됩니다(없으면 트레이싱/프롬프트 조회를
조용히 건너뛰고 로컬 fallback 프롬프트로 동작 -- fail-open):

- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`
- `LANGFUSE_BASE_URL`(또는 `LANGFUSE_HOST`)

구성 요소:

- `integrations/langfuse_client.py` -- 프로세스 시작 시 Langfuse 클라이언트를 한 번
  구성합니다. `model.py`가 여기의 `is_enabled`를 보고 LangChain `CallbackHandler`를
  모델에 바인딩합니다(`get_chat_model`/`get_structured_model` 둘 다 -- 특히
  `with_structured_output()`은 앞서 바인딩한 콜백을 상속하지 않으므로 별도로 다시
  바인딩합니다). 각 그래프 노드 함수에는 `@observe()`를 붙여 개별 span으로
  기록됩니다.
- `facade.py`의 각 어댑터(`AnalysisAgent`/`RubricAgent`/`TutorChatAgent`)는
  `@observe()`로 trace 루트를 만들고, `propagate_attributes()`로 요청에 실려온
  `user_identifier`/`session_id`를 trace의 `user_id`/`session_id`로 붙입니다 --
  Langfuse 대시보드에서 사용자ㆍ세션별로 trace를 필터링할 수 있습니다. (`feedback`
  그래프는 아직 facade/protocol에 연결되지 않아 이 트레이스 그룹핑이 없습니다 --
  연결할 때 같은 패턴을 적용하면 됩니다.)
- `integrations/prompts.py` -- 채점/첨삭/루브릭/Tutor Chat 시스템 프롬프트를
  `langfuse.get_prompt(name)`으로 조회합니다. 로컬 `PROMPT_TEMPLATES`가 fallback이자
  최초 업로드 소스입니다.
- `scripts/register_prompts.py` -- `PROMPT_TEMPLATES`를 Langfuse Prompt Management에
  업로드/갱신합니다(재실행 시 새 버전 생성). `.env` 설정 후 한 번 실행하세요:
  `uv run --package agent python agent/scripts/register_prompts.py`
- `scripts/verify_langfuse_grading.py` -- 실제 채점 요청 1건을 실행하고 Langfuse
  trace(순서대로의 span, user_id/session_id)를 API로 조회해 검증합니다.

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
