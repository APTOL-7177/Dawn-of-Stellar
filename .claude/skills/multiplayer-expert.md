# Multiplayer Expert Skill

멀티플레이어 시스템 개발 및 디버깅 전문 스킬

## 핵심 파일 맵
```
src/multiplayer/       — 24개 파일
├── server.py          — WebSocket 서버
├── client.py          — WebSocket 클라이언트
├── lobby.py           — 로비 시스템
├── matchmaking.py     — 매칭 시스템
├── sync.py            — 상태 동기화
├── protocol.py        — 통신 프로토콜
└── ...
```

## 의존성
- `websockets>=12.0`
- `aiohttp>=3.9.0`
- 설치: `pip install -e .[multiplayer]`

## 테스트
```bash
# 멀티플레이어 전용 테스트
python tests/run_multiplayer_tests.py

# 관련 pytest
pytest tests/ -k "multiplayer" -x -v
```

## 디버깅 포인트
1. **연결 실패**: WebSocket 포트 충돌, 방화벽
2. **동기화 지연**: 상태 직렬화/역직렬화 확인
3. **프로토콜 불일치**: 클라이언트/서버 버전 확인
4. **비동기 오류**: async/await 누락, 이벤트 루프 충돌
