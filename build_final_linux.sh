#!/bin/bash
echo "========================================"
echo "Dawn of Stellar - Linux 최종 패키징"
echo "========================================"
echo

# Python이 설치되어 있는지 확인
if ! command -v python3 &> /dev/null; then
    echo "[오류] Python3이 설치되어 있지 않습니다."
    echo "Python 3.10 이상을 설치해주세요."
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "CentOS/RHEL: sudo yum install python3 python3-pip"
    exit 1
fi

echo "[1/6] Python 버전 확인..."
python3 --version

echo
echo "[2/6] 필수 파일 확인..."
if [ ! -f "config.yaml" ]; then
    echo "[오류] config.yaml 파일을 찾을 수 없습니다."
    echo "현재 위치: $(pwd)"
    echo "이 스크립트는 프로젝트 루트 폴더에서 실행해야 합니다."
    exit 1
fi

if [ ! -f "main.py" ]; then
    echo "[오류] main.py 파일을 찾을 수 없습니다."
    echo "현재 위치: $(pwd)"
    echo "이 스크립트는 프로젝트 루트 폴더에서 실행해야 합니다."
    exit 1
fi

echo "필수 파일 확인 완료."

echo
echo "[3/6] 필요한 패키지 설치 확인..."
python3 -m pip install --upgrade pip > /dev/null 2>&1
python3 -m pip install pyinstaller > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "[오류] PyInstaller 설치에 실패했습니다."
    exit 1
fi

echo
echo "[4/6] 이전 빌드 파일 정리..."
rm -rf build
rm -rf dist/DawnOfStellar
rm -rf __pycache__

echo
echo "[5/6] 실행 파일 빌드 시작..."
echo "이 작업은 몇 분 정도 걸릴 수 있습니다..."
echo

python3 -m PyInstaller build_folder_linux.spec --clean --noconfirm

if [ $? -ne 0 ]; then
    echo
    echo "[오류] 빌드에 실패했습니다."
    echo "오류 메시지를 확인해주세요."
    exit 1
fi

echo
echo "[6/6] 게임 리소스 복사..."
echo

# 빌드된 폴더로 이동
cd dist/DawnOfStellar

# config.yaml 복사 (실행 파일과 같은 위치에)
cp ../../config.yaml config.yaml

# 기본 메타 진행 파일 복사 (배포판용)
if [ ! -d user_data ]; then
    mkdir user_data
fi
cp ../../config/meta_progress.json user_data/meta_progress.json

# 폰트 파일들 복사
cp ../../*.ttf . 2>/dev/null
cp ../../*.ttc . 2>/dev/null
cp ../../*.bdf . 2>/dev/null

# data 폴더 복사
if [ -d ../../data ]; then
    cp -r ../../data .
fi

# assets 폴더 복사
if [ -d ../../assets ]; then
    cp -r ../../assets .
fi

cd ../..

echo
echo "========================================"
echo "패키징 완료!"
echo "========================================"
echo
echo "게임 폴더 위치: dist/DawnOfStellar"
echo
echo "게임 실행 방법:"
echo "1. dist/DawnOfStellar 폴더로 이동"
echo "2. ./DawnOfStellar 실행 (또는 더블클릭)"
echo
echo "배포 방법:"
echo "1. dist/DawnOfStellar 폴더 전체를 압축"
echo "2. DawnOfStellar_Linux.tar.gz 등으로 배포"
echo
echo "완료되었습니다!"
