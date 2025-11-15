# 렌더링 설정 가이드

## 문자 간격 문제 해결하기

게임에서 문자 사이에 공백이 너무 많아 보인다면 렌더러를 변경해보세요.

## 렌더러 종류

`config.yaml`의 `display.renderer` 옵션을 수정하세요:

### 1. OpenGL2 (권장)
```yaml
renderer: "opengl2"
```
- **장점**: 가장 부드러운 폰트 렌더링, 문자 간격 최소화
- **단점**: GPU 필요
- **권장**: 대부분의 경우 이걸 사용하세요

### 2. OpenGL
```yaml
renderer: "opengl"
```
- **장점**: 하드웨어 가속
- **단점**: OpenGL2보다 품질 낮음
- **권장**: OpenGL2가 작동하지 않을 때

### 3. SDL2
```yaml
renderer: "sdl2"
```
- **장점**: CPU 기반, 호환성 높음
- **단점**: 문자 간격이 더 넓을 수 있음
- **권장**: 구형 시스템

### 4. Auto (자동)
```yaml
renderer: "auto"
```
- TCOD가 자동으로 최적의 렌더러 선택
- 문제가 있을 때만 수동 설정

## 문자 간격 추가 조정

### 1. 폰트 크기 조정
```yaml
font_size: 40  # 크게 할수록 선명하지만 느려질 수 있음
```

### 2. 문자 간격 미세 조정
```yaml
char_spacing_adjust: 2  # 값이 클수록 문자가 넓어짐
```
- **0**: 기본 간격
- **양수**: 문자를 넓게 (간격 감소)
- **음수**: 문자를 좁게 (간격 증가)

### 3. 화면 크기 조정
```yaml
screen_width: 80   # 문자 수 (가로)
screen_height: 45  # 문자 수 (세로)
```

## 추천 설정 조합

### 최고 품질 (강력한 PC)
```yaml
renderer: "opengl2"
font_size: 48
char_spacing_adjust: 3
```

### 균형 (일반 PC)
```yaml
renderer: "opengl2"
font_size: 40
char_spacing_adjust: 2
```

### 호환성 우선 (구형 PC)
```yaml
renderer: "sdl2"
font_size: 32
char_spacing_adjust: 1
```

## 폰트 변경

프로젝트 루트에 `GalmuriMono9.ttf` 같은 고정폭 한글 폰트를 넣으면
자동으로 로드됩니다. 추천 폰트:
- D2Coding (네이버)
- Galmuri (갈무리체)
- Nanum Gothic Coding

## 문제 해결

### 문자가 너무 흐리게 보임
→ `renderer: "opengl2"` 사용

### 문자 간격이 여전히 넓음
→ `char_spacing_adjust` 값을 높이세요 (예: 4, 6, 8)

### 게임이 느려짐
→ `font_size`를 줄이거나 `renderer: "sdl2"` 사용

### 한글이 깨져 보임
→ 시스템에 한글 폰트 설치 필요 (Ubuntu: `apt install fonts-nanum`)
