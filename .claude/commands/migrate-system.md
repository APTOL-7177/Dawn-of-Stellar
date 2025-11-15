# /migrate-system - 시스템 이식 명령어

기존 로그라이크_2 프로젝트에서 특정 시스템을 현재 Dos 프로젝트로 이식합니다.

## 사용법
```
/migrate-system <system_name>
```

## 지원 시스템
- `character` - Character 클래스 및 28개 직업
- `combat` - ATB, Brave, Damage 계산
- `skills` - 스킬 시스템
- `status` - StatusEffect 시스템 (165+ 상태효과)
- `world` - World, Dungeon 생성
- `ai` - AI 시스템 (동료/적)
- `audio` - Audio 시스템
- `ui` - UI/Display 시스템

## 예시
```bash
/migrate-system character
/migrate-system combat
```

---

**작업 내용:**

1. 기존 프로젝트(X:\로그라이크_2\game\)에서 해당 시스템 코드를 읽습니다
2. 새 프로젝트 구조(src/)에 맞게 리팩토링합니다
3. 이벤트 버스 기반으로 변환합니다
4. 의존성을 정리합니다
5. 테스트 코드를 생성합니다

**Task 에이전트를 사용하여 자동으로 처리합니다.**
