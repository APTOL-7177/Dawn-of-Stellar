#!/bin/bash
echo "========================================"
echo "Dawn of Stellar - Linux 개발 모드 패키징"
echo "========================================"
echo

# 스크립트 위치로 이동
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Python이 설치되어 있는지 확인
if ! command -v python3 &> /dev/null; then
    echo "[오류] Python3이 설치되어 있지 않습니다."
    echo "Python 3.10 이상을 설치해주세요."
    exit 1
fi

echo "[1/7] Python 버전 확인..."
python3 --version

echo
echo "[2/7] 필수 파일 확인..."
if [ ! -f "config.yaml" ]; then
    echo "[오류] config.yaml 파일을 찾을 수 없습니다."
    exit 1
fi
if [ ! -f "main.py" ]; then
    echo "[오류] main.py 파일을 찾을 수 없습니다."
    exit 1
fi
echo "필수 파일 확인 완료."

echo
echo "[3/7] 필요한 패키지 설치 확인..."
python3 -m pip install --upgrade pip > /dev/null 2>&1
python3 -m pip install --break-system-packages pyinstaller 2>/dev/null || \
python3 -m pip install pyinstaller 2>/dev/null

if [ $? -ne 0 ]; then
    echo "[오류] PyInstaller 설치에 실패했습니다."
    exit 1
fi

# 게임 의존성 설치
if [ -f "requirements.txt" ]; then
    python3 -m pip install --break-system-packages -r requirements.txt 2>/dev/null || \
    python3 -m pip install -r requirements.txt 2>/dev/null || true
fi

echo
echo "[4/7] 이전 빌드 파일 정리..."
rm -rf build
rm -rf dist/DawnOfStellar_Dev
rm -rf __pycache__

echo
echo "[5/7] 실행 파일 빌드 시작..."
echo "이 작업은 몇 분 정도 걸릴 수 있습니다..."
echo

python3 -m PyInstaller build_folder_linux.spec --clean --noconfirm

if [ $? -ne 0 ]; then
    echo
    echo "[오류] 빌드에 실패했습니다."
    exit 1
fi

echo
echo "[6/7] 개발 모드 폴더로 복사..."
rm -rf dist/DawnOfStellar_Dev
mv dist/DawnOfStellar dist/DawnOfStellar_Dev

echo
echo "[7/7] 게임 리소스 복사 (개발 모드)..."
echo

cd dist/DawnOfStellar_Dev

# config.yaml 복사 후 개발 모드 활성화
cp ../../config.yaml config.yaml

# 개발 모드 활성화
sed -i 's/debug_mode: false/debug_mode: true/g' config.yaml
sed -i 's/  enabled: false/  enabled: true/g' config.yaml
sed -i 's/unlock_all_classes: false/unlock_all_classes: true/g' config.yaml

# config 디렉토리 복사 (key_bindings.yaml 등)
if [ -d ../../config ]; then
    cp -r ../../config .
fi

# 기본 메타 진행 파일 복사
mkdir -p user_data
cp config/meta_progress.json user_data/meta_progress.json

# 폰트 파일들 복사
cp ../../*.ttf . 2>/dev/null || true
cp ../../*.ttc . 2>/dev/null || true
cp ../../*.bdf . 2>/dev/null || true

# data 폴더 복사
if [ -d ../../data ]; then
    cp -r ../../data .
fi

# assets 폴더 복사
if [ -d ../../assets ]; then
    cp -r ../../assets .
fi

# 실행 권한 부여
chmod +x DawnOfStellar

cd ../..

echo
echo "========================================"
echo "개발 모드 패키징 완료!"
echo "========================================"
echo
echo "게임 폴더 위치: dist/DawnOfStellar_Dev"
echo
echo "[주의] 이 빌드는 개발 모드입니다:"
echo "  - 디버그 모드 활성화"
echo "  - 모든 직업/특성/패시브 해금"
echo
echo "실행: cd dist/DawnOfStellar_Dev && ./DawnOfStellar"
echo
echo "완료되었습니다!"
