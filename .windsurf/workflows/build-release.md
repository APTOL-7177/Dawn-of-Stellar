---
description: 릴리스 빌드를 생성하는 워크플로우
---

# 릴리스 빌드

## 1. 코드 품질 검사
```bash
black --check src tests
isort --check-only src tests
pylint src
mypy src
```

## 2. 테스트 실행
// turbo
```bash
pytest tests/ -ra -q --strict-markers
```

## 3. Windows 빌드
```bash
build_final.bat
```
빌드 결과물은 `dist/` 디렉토리에 생성된다.

## 4. Linux 빌드
```bash
./build_final_linux.sh
```

## 5. 인스톨러 생성 (Windows)
```bash
build_installer.bat
```
NSIS 스크립트(`install.nsi`)를 사용하여 `DawnOfStellar_Setup.exe`를 생성한다.

## 6. 빌드 검증
- `dist/` 디렉토리에 실행 파일 존재 확인
- 설정 파일(`config.yaml`, `config/`) 포함 확인
- `data/` 디렉토리 (스킬, 캐릭터 YAML) 포함 확인
- `assets/` (폰트, 오디오) 포함 확인

## 7. 버전 태깅
```bash
git tag -a v<version> -m "Release v<version>"
git push origin v<version>
```
`pyproject.toml`의 `version` 필드와 일치시킨다.
