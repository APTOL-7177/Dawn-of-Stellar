# 🐧 Linux용 게임 빌드 가이드

## 📋 요구사항

### 시스템 요구사항
- **Ubuntu/Debian/CentOS/RHEL** 등 주요 Linux 배포판
- **Python 3.10+** 설치
- **pip** 패키지 관리자
- **필요한 시스템 라이브러리**

### 필수 패키지 설치

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install python3 python3-pip python3-dev
sudo apt install libsdl2-dev libsdl2-mixer-dev libsdl2-image-dev libsdl2-ttf-dev
sudo apt install libsmpeg-dev libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev
```

#### CentOS/RHEL:
```bash
sudo yum install python3 python3-pip python3-devel
sudo yum install SDL2-devel SDL2_mixer-devel SDL2_image-devel SDL2_ttf-devel
sudo yum install libjpeg-turbo-devel libpng-devel
```

## 🚀 빌드 방법

### 방법 1: WSL에서 빌드 (Windows 사용자 추천)

Windows Subsystem for Linux에서 빌드:

1. **WSL 설치 및 설정:**
   ```powershell
   # PowerShell에서 실행
   wsl --install Ubuntu
   wsl --set-default Ubuntu
   ```

2. **WSL에서 프로젝트 복사:**
   ```bash
   # WSL 터미널에서
   cd /mnt/x/develop/Dawn-of-Stellar
   # 또는 프로젝트를 WSL 파일시스템으로 복사
   cp -r /mnt/x/develop/Dawn-of-Stellar ~/Dawn-of-Stellar
   cd ~/Dawn-of-Stellar
   ```

3. **빌드 실행:**
   ```bash
   ./build_final_linux.sh
   ```

### 방법 2: 네이티브 Linux에서 빌드

1. **프로젝트 다운로드/복사:**
   ```bash
   git clone <repository-url>
   cd Dawn-of-Stellar
   ```

2. **빌드 스크립트 실행:**
   ```bash
   chmod +x build_final_linux.sh
   ./build_final_linux.sh
   ```

### 방법 3: Docker를 사용한 빌드

Docker 컨테이너에서 빌드 (어떤 환경에서도 동일한 결과):

```dockerfile
# Dockerfile
FROM ubuntu:22.04

RUN apt update && apt install -y \
    python3 python3-pip python3-dev \
    libsdl2-dev libsdl2-mixer-dev libsdl2-image-dev libsdl2-ttf-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install pyinstaller pygame pyyaml python-dotenv
RUN chmod +x build_final_linux.sh
RUN ./build_final_linux.sh
```

```bash
# Docker 빌드
docker build -t dawn-of-stellar-builder .
docker run --rm -v $(pwd)/dist:/app/dist dawn-of-stellar-builder
```

## 📁 출력 파일

빌드 완료 후 생성되는 파일들:

```
dist/DawnOfStellar/
├── DawnOfStellar           # ⭐ Linux 실행 파일 (확장자 없음)
├── _internal/              # Python 런타임 파일들
├── config.yaml            # 게임 설정
├── assets/                # 게임 리소스
├── data/                  # 게임 데이터
├── *.ttf, *.bdf          # 폰트 파일
└── user_data/            # 사용자 데이터 (자동 생성)
```

## 🎮 실행 방법

### Linux에서 실행:
```bash
cd dist/DawnOfStellar
./DawnOfStellar
```

### 권한 문제 해결:
```bash
# 실행 권한이 없을 경우
chmod +x DawnOfStellar
./DawnOfStellar
```

## 🛠️ 문제 해결

### 빌드 실패 시:

1. **Python 버전 확인:**
   ```bash
   python3 --version  # 3.10 이상 필요
   ```

2. **필수 라이브러리 재설치:**
   ```bash
   pip install --upgrade pygame pyinstaller pyyaml python-dotenv
   ```

3. **시스템 라이브러리 확인:**
   ```bash
   # Ubuntu/Debian
   sudo apt install libsdl2-dev libsdl2-mixer-dev libsdl2-image-dev libsdl2-ttf-dev

   # CentOS/RHEL
   sudo yum install SDL2-devel SDL2_mixer-devel SDL2_image-devel SDL2_ttf-devel
   ```

### 실행 실패 시:

1. **라이브러리 경로 문제:**
   ```bash
   # LD_LIBRARY_PATH 설정
   export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu
   ./DawnOfStellar
   ```

2. **OpenGL 문제:**
   ```bash
   # Mesa 라이브러리 설치
   sudo apt install mesa-common-dev libgl1-mesa-dev
   ```

3. **오디오 문제:**
   ```bash
   # PulseAudio 또는 ALSA 확인
   sudo apt install pulseaudio alsa-utils
   ```

## 📦 배포

### 압축 및 배포:
```bash
cd dist
tar -czf DawnOfStellar_Linux.tar.gz DawnOfStellar/
```

### 배포 파일명 예시:
- `DawnOfStellar_Linux.tar.gz`
- `DawnOfStellar_Ubuntu.tar.gz`
- `DawnOfStellar_v6.1.0_Linux.tar.gz`

## 🔄 크로스 플랫폼 빌드

여러 플랫폼용 빌드를 한 번에 하고 싶다면:

```bash
# GitHub Actions 또는 Jenkins 등 CI/CD 사용
# 각 플랫폼에서 별도 빌드 후 배포
```

## 💡 팁

- **WSL 권장:** Windows 사용자는 WSL에서 빌드하는 것을 추천
- **도커 사용:** 환경 일관성을 위해 Docker 컨테이너 사용 고려
- **테스트:** 빌드 후 반드시 실행 테스트를 해보세요
- **최적화:** UPX 압축으로 파일 크기를 줄일 수 있습니다

---

**Linux 빌드가 완료되셨나요?** 🚀✨
