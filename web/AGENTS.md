<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# web/

## Purpose
게임의 웹 클라이언트/데모 인터페이스. 브라우저에서 게임을 실행하거나 데모를 제공하기 위한 HTML/JS/CSS 파일 6개로 구성된다.

## Key Files
| File | Description |
|------|-------------|
| `index.html` | 웹 클라이언트 진입점 |
| `game.html` | 게임 메인 페이지 |
| `play.html` | 게임 플레이 페이지 |
| `demo.html` | 데모 페이지 |
| `demo.js` | 데모 JavaScript 로직 |
| `style.css` | 전체 웹 스타일시트 |

## For AI Agents
### Working In This Directory
- 웹 클라이언트는 Python 게임 백엔드와 통신하는 프론트엔드
- 스타일 변경 시 `style.css` 수정
- 게임 로직은 `src/` 에 있으며 웹은 표시 레이어만 담당

## Dependencies
### Internal
- `src/` — 백엔드 게임 로직
### External
- 브라우저 표준 API

<!-- MANUAL: -->
