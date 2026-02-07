---
description: 새로운 튜토리얼 스텝을 추가하는 워크플로우
---

# 튜토리얼 추가

## 1. 기존 튜토리얼 패턴 확인
// turbo
`data/tutorials/` 디렉토리의 기존 YAML을 읽어 구조를 파악한다.

## 2. 튜토리얼 YAML 생성
`data/tutorials/<번호>_<topic>.yaml` 파일을 생성한다.
기존 번호 체계를 이어서 다음 번호를 부여한다.

## 3. 튜토리얼 로직 구현
`src/tutorial/` 디렉토리의 관련 파일에서 새 튜토리얼의 진행 로직을 구현한다:
- 트리거 조건
- 단계별 진행
- 완료 조건
- UI 표시 내용

## 4. UI 연동
`src/ui/` 관련 파일에서 튜토리얼 팝업/가이드 표시를 확인한다.

## 5. 테스트
```bash
pytest tests/ -k "tutorial" -x -q
```
