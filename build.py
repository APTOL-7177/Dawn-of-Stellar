#!/usr/bin/env python3
"""
Dawn of Stellar - 독립 실행 파일 빌드 스크립트

PyInstaller를 사용하여 Python 설치 없이 실행 가능한 EXE 파일을 생성합니다.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def print_banner():
    """빌드 시작 배너"""
    print("=" * 70)
    print("    ⭐ Dawn of Stellar - 독립 실행 파일 빌드 ⭐")
    print("=" * 70)
    print()


def check_pyinstaller():
    """PyInstaller 설치 확인"""
    print("[1/5] PyInstaller 확인 중...")
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} 발견")
        return True
    except ImportError:
        print("⚠️  PyInstaller가 설치되어 있지 않습니다.")
        print()
        install = input("지금 설치하시겠습니까? (Y/N): ").strip().upper()
        if install == 'Y':
            print("\n📦 PyInstaller 설치 중...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✅ PyInstaller 설치 완료!")
            return True
        else:
            print("❌ PyInstaller가 필요합니다. 빌드를 중단합니다.")
            return False


def clean_build_dirs():
    """이전 빌드 디렉토리 정리"""
    print("\n[2/5] 이전 빌드 정리 중...")

    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  - {dir_name}/ 삭제됨")

    # .spec 파일 삭제
    spec_files = list(Path('.').glob('*.spec'))
    for spec_file in spec_files:
        spec_file.unlink()
        print(f"  - {spec_file} 삭제됨")

    print("✅ 정리 완료!")


def build_executable():
    """PyInstaller로 실행 파일 빌드"""
    print("\n[3/5] 실행 파일 빌드 중...")
    print("   시간이 다소 걸릴 수 있습니다 (5-10분)...")
    print()

    # PyInstaller 옵션
    build_options = [
        sys.executable, "-m", "PyInstaller",
        "--name=DawnOfStellar",           # 출력 파일명
        "--onefile",                       # 단일 실행 파일
        "--windowed",                      # 콘솔 창 숨김 (Windows)
        "--clean",                         # 캐시 정리
        "--noconfirm",                     # 확인 없이 진행

        # 아이콘 (있으면 추가)
        # "--icon=assets/icon.ico",

        # 데이터 파일 포함
        "--add-data=data;data",            # Windows
        "--add-data=assets;assets",        # Windows
        "--add-data=config.yaml;.",        # Windows

        # 히든 임포트 (필요한 모듈 명시)
        "--hidden-import=tcod",
        "--hidden-import=yaml",
        "--hidden-import=numpy",
        "--hidden-import=src",
        "--hidden-import=src.core",
        "--hidden-import=src.combat",
        "--hidden-import=src.character",
        "--hidden-import=src.world",
        "--hidden-import=src.ui",
        "--hidden-import=src.audio",
        "--hidden-import=src.equipment",
        "--hidden-import=src.ai",
        "--hidden-import=src.gathering",
        "--hidden-import=src.cooking",
        "--hidden-import=src.field",
        "--hidden-import=src.persistence",

        # 최적화
        "--optimize=2",                    # 바이트코드 최적화

        # 메인 스크립트
        "main.py"
    ]

    # Linux/Mac의 경우 경로 구분자 변경
    if sys.platform != "win32":
        build_options = [opt.replace(';', ':') if '--add-data' in opt else opt
                        for opt in build_options]

    try:
        subprocess.check_call(build_options)
        print("\n✅ 빌드 완료!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 빌드 실패: {e}")
        return False


def verify_build():
    """빌드 결과 확인"""
    print("\n[4/5] 빌드 검증 중...")

    exe_name = "DawnOfStellar.exe" if sys.platform == "win32" else "DawnOfStellar"
    exe_path = Path("dist") / exe_name

    if not exe_path.exists():
        print(f"❌ 실행 파일을 찾을 수 없습니다: {exe_path}")
        return False

    file_size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"✅ 실행 파일 생성됨: {exe_path}")
    print(f"   크기: {file_size_mb:.2f} MB")

    return True


def create_distribution():
    """배포 패키지 생성"""
    print("\n[5/5] 배포 패키지 생성 중...")

    dist_dir = Path("dist/DawnOfStellar")
    dist_dir.mkdir(parents=True, exist_ok=True)

    # 실행 파일 복사
    exe_name = "DawnOfStellar.exe" if sys.platform == "win32" else "DawnOfStellar"
    src_exe = Path("dist") / exe_name
    dst_exe = dist_dir / exe_name

    if src_exe.exists():
        shutil.copy2(src_exe, dst_exe)
        print(f"  - {exe_name} 복사됨")

    # 필수 파일 복사
    files_to_copy = [
        "README.md",
        "INSTALL.md",
        "LICENSE",  # 있으면
    ]

    for file_name in files_to_copy:
        src_file = Path(file_name)
        if src_file.exists():
            dst_file = dist_dir / file_name
            shutil.copy2(src_file, dst_file)
            print(f"  - {file_name} 복사됨")

    # 디렉토리 복사
    dirs_to_copy = [
        "data",
        "assets",
        "docs",
    ]

    for dir_name in dirs_to_copy:
        src_dir = Path(dir_name)
        if src_dir.exists():
            dst_dir = dist_dir / dir_name
            if dst_dir.exists():
                shutil.rmtree(dst_dir)
            shutil.copytree(src_dir, dst_dir)
            print(f"  - {dir_name}/ 복사됨")

    # 실행 스크립트 생성 (선택사항)
    if sys.platform == "win32":
        run_script = dist_dir / "run.bat"
        run_script.write_text(
            "@echo off\n"
            "title Dawn of Stellar\n"
            f"{exe_name}\n"
            "pause\n"
        )
        print("  - run.bat 생성됨")

    print(f"\n✅ 배포 패키지 생성 완료: {dist_dir}/")

    return True


def main():
    """메인 함수"""
    print_banner()

    # 1. PyInstaller 확인
    if not check_pyinstaller():
        sys.exit(1)

    # 2. 이전 빌드 정리
    clean_build_dirs()

    # 3. 실행 파일 빌드
    if not build_executable():
        print("\n❌ 빌드 실패!")
        sys.exit(1)

    # 4. 빌드 검증
    if not verify_build():
        print("\n❌ 검증 실패!")
        sys.exit(1)

    # 5. 배포 패키지 생성
    if not create_distribution():
        print("\n⚠️  배포 패키지 생성 실패 (무시 가능)")

    # 완료 메시지
    print("\n" + "=" * 70)
    print("    🎉 빌드 완료! 🎉")
    print("=" * 70)
    print()
    print("📦 빌드 결과:")
    print("   - dist/DawnOfStellar.exe (단일 실행 파일)")
    print("   - dist/DawnOfStellar/ (배포용 패키지)")
    print()
    print("🚀 실행 방법:")
    print("   1. dist/DawnOfStellar.exe 더블클릭")
    print("   2. 또는 dist/DawnOfStellar/ 폴더를 압축하여 배포")
    print()
    print("💡 주의:")
    print("   - EXE 파일 실행 시 백신 프로그램에서 경고할 수 있습니다")
    print("   - 첫 실행은 압축 해제로 인해 느릴 수 있습니다")
    print()

    # 즉시 실행 옵션
    if sys.platform == "win32":
        run_now = input("지금 바로 실행해보시겠습니까? (Y/N): ").strip().upper()
        if run_now == 'Y':
            exe_path = Path("dist/DawnOfStellar.exe")
            if exe_path.exists():
                print("\n🎮 게임을 시작합니다...\n")
                subprocess.Popen([str(exe_path)])
            else:
                print("\n❌ 실행 파일을 찾을 수 없습니다.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 빌드를 취소했습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
