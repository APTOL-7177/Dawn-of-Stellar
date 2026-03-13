#!/bin/bash
# Dawn of Stellar - Linux 빌드 스크립트 (WSL 또는 네이티브 Linux에서 실행)

echo "========================================"
echo "Dawn of Stellar - Linux 빌드"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Python 확인
if ! command -v python3 &> /dev/null; then
    echo "[오류] python3이 설치되어 있지 않습니다."
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    exit 1
fi
echo "[1/6] Python 버전: $(python3 --version)"

# pip 확인 및 설치
echo ""
echo "[2/6] 필수 패키지 설치 확인..."
if ! python3 -m pip --version &> /dev/null; then
    echo "pip가 없습니다. 설치 중..."
    sudo apt-get update -qq && sudo apt-get install -y -qq python3-pip python3-venv
fi

python3 -m pip install --break-system-packages pyinstaller 2>/dev/null || \
python3 -m pip install --user pyinstaller 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[오류] PyInstaller 설치에 실패했습니다."
    exit 1
fi
echo "PyInstaller 설치 확인 완료."

# 게임 의존성 설치
echo ""
echo "[3/6] 게임 의존성 설치..."
if [ -f "requirements.txt" ]; then
    python3 -m pip install --break-system-packages -r requirements.txt 2>/dev/null || \
    python3 -m pip install --user -r requirements.txt 2>/dev/null || true
fi
# 핵심 패키지 확인
python3 -m pip install --break-system-packages tcod pygame pyyaml numpy python-dotenv 2>/dev/null || \
python3 -m pip install --user tcod pygame pyyaml numpy python-dotenv 2>/dev/null || true
echo "의존성 설치 완료."

# 이전 빌드 정리
echo ""
echo "[4/6] 이전 Linux 빌드 정리..."
rm -rf build_linux dist_linux

# 빌드
echo ""
echo "[5/6] Linux 실행 파일 빌드 시작..."
echo "이 작업은 몇 분 정도 걸릴 수 있습니다..."
echo ""

python3 -m PyInstaller build_folder_linux.spec \
    --clean --noconfirm \
    --distpath dist_linux \
    --workpath build_linux

if [ $? -ne 0 ]; then
    echo "[오류] 빌드에 실패했습니다."
    exit 1
fi

# 리소스 복사
echo ""
echo "[6/6] 게임 리소스 복사..."

DIST_DIR="dist_linux/DawnOfStellar"

# config.yaml 복사
cp config.yaml "$DIST_DIR/config.yaml"

# config 디렉토리 복사 (key_bindings.yaml 등)
if [ -d "config" ]; then
    cp -r config "$DIST_DIR/config"
fi

# 메타 진행 파일
mkdir -p "$DIST_DIR/user_data"
cp "$DIST_DIR/config/meta_progress.json" "$DIST_DIR/user_data/meta_progress.json"

# 폰트 파일
cp *.ttf "$DIST_DIR/" 2>/dev/null || true
cp *.ttc "$DIST_DIR/" 2>/dev/null || true
cp *.bdf "$DIST_DIR/" 2>/dev/null || true

# data 폴더
if [ -d "data" ]; then
    cp -r data "$DIST_DIR/data"
fi

# assets 폴더
if [ -d "assets" ]; then
    cp -r assets "$DIST_DIR/assets"
fi

# 실행 권한 부여
chmod +x "$DIST_DIR/DawnOfStellar"

# tar.gz 아카이브 생성
echo ""
echo "배포용 아카이브 생성..."
cd dist_linux
tar -czf DawnOfStellar_Linux.tar.gz DawnOfStellar
cd ..

echo ""
echo "========================================"
echo "Linux 빌드 완료!"
echo "========================================"
echo ""
echo "게임 폴더: dist_linux/DawnOfStellar"
echo "배포 아카이브: dist_linux/DawnOfStellar_Linux.tar.gz"
echo ""
