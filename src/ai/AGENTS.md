<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# AI/LLM 통합 시스템

## 목적
OpenAI API를 통한 언어 모델 기반 AI 플레이어 구현. 적 행동 선택, 탐색 지능, 플레이 데이터 로깅, 게임 상태 인코딩을 포함합니다. LLM 봇이 게임 규칙을 이해하고 전략적 결정을 내릴 수 있도록 합니다.

## 주요 파일
| 파일 | 설명 |
|------|------|
| llm_provider.py | LLM API 추상화 (OpenAI 클라이언트 래퍼) |
| openai_client.py | OpenAI API 직접 호출 (토큰 관리, 프롬프팅) |
| job_prompts.py | 직업별 LLM 프롬프트 템플릿 |
| exploration_state_converter.py | 탐색 상태를 LLM 입력으로 변환 |
| play_data_logger.py | 플레이 데이터 로깅 (분석용) |
| enemy_ai.py | 적 AI 의사결정 |

## AI 에이전트를 위한 가이드
### 이 디렉토리에서 작업할 때
- LLM 프롬프트는 게임 규칙, 현재 상태, 가능한 행동을 명확하게 설명해야 합니다.
- API 호출은 비용이 발생하므로 캐싱과 배치 처리를 고려합니다.
- 상태 변환은 정확하고 일관성 있어야 합니다 (LLM이 이해할 수 있는 형식).
- 타임아웃과 재시도 로직이 필요합니다.

### 테스트 요구사항
- LLM 프롬프트는 샘플 응답으로 파싱 테스트를 합니다.
- 상태 변환은 라운드 트립 테스트 (변환 후 역변환)를 합니다.
- API 호출은 목(mock)으로 단위 테스트합니다.

### 일반적인 패턴
- LLM 응답은 JSON 형식으로 파싱됩니다.
- 프롬프트는 시스템 메시지(역할) + 사용자 메시지(상태)로 구성됩니다.
- 토큰 사용량을 추적하여 비용을 관리합니다.

## 의존성
### 내부
- `src/character/` - 캐릭터 직업, 스킬
- `src/combat/` - 전투 상태
- `src/world/` - 탐색 상태
- `src/multiplayer/` - 멀티플레이 봇

### 외부
- `openai` - OpenAI API 클라이언트
- `pydantic` - 프롬프트/응답 검증
- `requests` - HTTP 호출 (재시도 로직)

<!-- MANUAL: -->
