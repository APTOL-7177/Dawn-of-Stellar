#!/usr/bin/env python3
"""
Dawn of Stellar 게임 런처

게임 실행, 세이브 관리, 로그 확인 등 다양한 기능 제공
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


class Color:
    """터미널 색상 코드"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class GameLauncher:
    """게임 런처 클래스"""

    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.saves_dir = self.root_dir / "saves"
        self.logs_dir = self.root_dir / "logs"
        self.config_file = self.root_dir / "config.yaml"
        self.main_script = self.root_dir / "main.py"

        # 디렉토리 생성
        self.saves_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

    def clear_screen(self):
        """화면 지우기"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        """헤더 출력"""
        self.clear_screen()
        print(f"{Color.CYAN}{Color.BOLD}")
        print("╔════════════════════════════════════════════════════════════════╗")
        print("║                                                                ║")
        print("║              ⭐ Dawn of Stellar - 별빛의 여명 ⭐              ║")
        print("║                                                                ║")
        print("║                    게임 런처 v1.0.0                            ║")
        print("║                                                                ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print(f"{Color.ENDC}")

    def print_menu(self):
        """메인 메뉴 출력"""
        print(f"\n{Color.BOLD}[ 메인 메뉴 ]{Color.ENDC}\n")
        print(f"{Color.GREEN}1.{Color.ENDC} 🎮 게임 시작")
        print(f"{Color.GREEN}2.{Color.ENDC} 🔧 개발 모드로 시작 (모든 직업 해금)")
        print(f"{Color.GREEN}3.{Color.ENDC} 🐛 디버그 모드로 시작")
        print(f"{Color.GREEN}4.{Color.ENDC} 💾 세이브 파일 관리")
        print(f"{Color.GREEN}5.{Color.ENDC} 📋 로그 확인")
        print(f"{Color.GREEN}6.{Color.ENDC} 🧪 테스트 실행")
        print(f"{Color.GREEN}7.{Color.ENDC} ⚙️  설정")
        print(f"{Color.GREEN}8.{Color.ENDC} ℹ️  게임 정보")
        print(f"{Color.GREEN}9.{Color.ENDC} 🔍 시스템 체크")
        print(f"{Color.RED}0.{Color.ENDC} 🚪 종료")
        print()

    def run_game(self, mode: str = "normal"):
        """게임 실행

        Args:
            mode: "normal", "dev", "debug"
        """
        print(f"\n{Color.YELLOW}게임을 시작합니다...{Color.ENDC}\n")

        cmd = [sys.executable, str(self.main_script)]

        if mode == "dev":
            cmd.append("--dev")
            print(f"{Color.CYAN}📌 개발 모드: 모든 직업 잠금 해제{Color.ENDC}")
        elif mode == "debug":
            cmd.extend(["--debug", "--log=DEBUG"])
            print(f"{Color.CYAN}📌 디버그 모드: 상세 로그 출력{Color.ENDC}")

        print(f"{Color.CYAN}명령어: {' '.join(cmd)}{Color.ENDC}\n")
        print(f"{Color.GREEN}게임 창이 열립니다. 게임 종료 시 이 창으로 돌아옵니다.{Color.ENDC}\n")

        try:
            result = subprocess.run(cmd, cwd=self.root_dir)
            if result.returncode == 0:
                print(f"\n{Color.GREEN}✓ 게임이 정상 종료되었습니다.{Color.ENDC}")
            else:
                print(f"\n{Color.RED}✗ 게임이 오류로 종료되었습니다. (코드: {result.returncode}){Color.ENDC}")
        except Exception as e:
            print(f"\n{Color.RED}✗ 게임 실행 중 오류 발생: {e}{Color.ENDC}")

        input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")

    def manage_saves(self):
        """세이브 파일 관리"""
        while True:
            self.print_header()
            print(f"\n{Color.BOLD}[ 💾 세이브 파일 관리 ]{Color.ENDC}\n")

            # 세이브 파일 목록
            save_files = sorted(self.saves_dir.glob("*.json"), key=os.path.getmtime, reverse=True)

            if not save_files:
                print(f"{Color.YELLOW}세이브 파일이 없습니다.{Color.ENDC}\n")
            else:
                print(f"{Color.CYAN}총 {len(save_files)}개의 세이브 파일:{Color.ENDC}\n")
                for i, save_file in enumerate(save_files, 1):
                    size = save_file.stat().st_size
                    mtime = datetime.fromtimestamp(save_file.stat().st_mtime)
                    print(f"{i}. {Color.GREEN}{save_file.name}{Color.ENDC}")
                    print(f"   크기: {size:,} bytes | 수정: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

                    # 세이브 정보 미리보기
                    try:
                        with open(save_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if 'party' in data:
                                party_names = [char.get('name', 'Unknown') for char in data['party']]
                                print(f"   파티: {', '.join(party_names)}")
                            if 'floor' in data:
                                print(f"   층수: {data['floor']}층")
                    except Exception:
                        pass
                    print()

            print(f"\n{Color.GREEN}1.{Color.ENDC} 세이브 파일 백업")
            print(f"{Color.GREEN}2.{Color.ENDC} 세이브 파일 삭제")
            print(f"{Color.GREEN}3.{Color.ENDC} 세이브 파일 정보 상세보기")
            print(f"{Color.RED}0.{Color.ENDC} 뒤로 가기")
            print()

            choice = input(f"{Color.YELLOW}선택: {Color.ENDC}").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.backup_saves()
            elif choice == "2":
                self.delete_save(save_files)
            elif choice == "3":
                self.show_save_info(save_files)

    def backup_saves(self):
        """세이브 파일 백업"""
        backup_dir = self.root_dir / "saves_backup"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"backup_{timestamp}"

        try:
            backup_path.mkdir(parents=True, exist_ok=True)
            count = 0
            for save_file in self.saves_dir.glob("*.json"):
                shutil.copy2(save_file, backup_path / save_file.name)
                count += 1

            print(f"\n{Color.GREEN}✓ {count}개의 세이브 파일을 백업했습니다.{Color.ENDC}")
            print(f"{Color.CYAN}위치: {backup_path}{Color.ENDC}")
        except Exception as e:
            print(f"\n{Color.RED}✗ 백업 중 오류 발생: {e}{Color.ENDC}")

        input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")

    def delete_save(self, save_files: List[Path]):
        """세이브 파일 삭제"""
        if not save_files:
            return

        print(f"\n{Color.YELLOW}삭제할 파일 번호 입력 (0: 취소): {Color.ENDC}", end="")
        choice = input().strip()

        try:
            idx = int(choice)
            if idx == 0:
                return
            if 1 <= idx <= len(save_files):
                file_to_delete = save_files[idx - 1]
                confirm = input(f"{Color.RED}정말로 '{file_to_delete.name}'을(를) 삭제하시겠습니까? (y/N): {Color.ENDC}").strip().lower()
                if confirm == 'y':
                    file_to_delete.unlink()
                    print(f"\n{Color.GREEN}✓ 파일이 삭제되었습니다.{Color.ENDC}")
                else:
                    print(f"\n{Color.YELLOW}취소되었습니다.{Color.ENDC}")
            else:
                print(f"\n{Color.RED}✗ 잘못된 번호입니다.{Color.ENDC}")
        except ValueError:
            print(f"\n{Color.RED}✗ 숫자를 입력해주세요.{Color.ENDC}")
        except Exception as e:
            print(f"\n{Color.RED}✗ 오류 발생: {e}{Color.ENDC}")

        input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")

    def show_save_info(self, save_files: List[Path]):
        """세이브 파일 상세 정보"""
        if not save_files:
            return

        print(f"\n{Color.YELLOW}확인할 파일 번호 입력 (0: 취소): {Color.ENDC}", end="")
        choice = input().strip()

        try:
            idx = int(choice)
            if idx == 0:
                return
            if 1 <= idx <= len(save_files):
                save_file = save_files[idx - 1]
                with open(save_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                print(f"\n{Color.CYAN}{'=' * 60}{Color.ENDC}")
                print(f"{Color.BOLD}{save_file.name}{Color.ENDC}")
                print(f"{Color.CYAN}{'=' * 60}{Color.ENDC}\n")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print(f"\n{Color.RED}✗ 잘못된 번호입니다.{Color.ENDC}")
        except Exception as e:
            print(f"\n{Color.RED}✗ 오류 발생: {e}{Color.ENDC}")

        input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")

    def view_logs(self):
        """로그 확인"""
        while True:
            self.print_header()
            print(f"\n{Color.BOLD}[ 📋 로그 확인 ]{Color.ENDC}\n")

            # 최근 로그 파일 목록
            log_files = sorted(self.logs_dir.glob("*.log"), key=os.path.getmtime, reverse=True)[:20]

            if not log_files:
                print(f"{Color.YELLOW}로그 파일이 없습니다.{Color.ENDC}\n")
            else:
                print(f"{Color.CYAN}최근 20개 로그 파일:{Color.ENDC}\n")
                for i, log_file in enumerate(log_files, 1):
                    size = log_file.stat().st_size
                    mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                    print(f"{i}. {Color.GREEN}{log_file.name}{Color.ENDC}")
                    print(f"   크기: {size:,} bytes | 수정: {mtime.strftime('%Y-%m-%d %H:%M:%S')}\n")

            print(f"{Color.GREEN}1.{Color.ENDC} 로그 파일 보기")
            print(f"{Color.GREEN}2.{Color.ENDC} 로그 파일 삭제")
            print(f"{Color.GREEN}3.{Color.ENDC} 모든 로그 삭제")
            print(f"{Color.RED}0.{Color.ENDC} 뒤로 가기")
            print()

            choice = input(f"{Color.YELLOW}선택: {Color.ENDC}").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.show_log(log_files)
            elif choice == "2":
                self.delete_log(log_files)
            elif choice == "3":
                self.clear_all_logs()

    def show_log(self, log_files: List[Path]):
        """로그 파일 내용 표시"""
        if not log_files:
            return

        print(f"\n{Color.YELLOW}확인할 로그 번호 입력 (0: 취소): {Color.ENDC}", end="")
        choice = input().strip()

        try:
            idx = int(choice)
            if idx == 0:
                return
            if 1 <= idx <= len(log_files):
                log_file = log_files[idx - 1]
                print(f"\n{Color.CYAN}{'=' * 60}{Color.ENDC}")
                print(f"{Color.BOLD}{log_file.name}{Color.ENDC}")
                print(f"{Color.CYAN}{'=' * 60}{Color.ENDC}\n")

                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # 마지막 50줄만 표시
                    for line in lines[-50:]:
                        print(line.rstrip())
            else:
                print(f"\n{Color.RED}✗ 잘못된 번호입니다.{Color.ENDC}")
        except Exception as e:
            print(f"\n{Color.RED}✗ 오류 발생: {e}{Color.ENDC}")

        input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")

    def delete_log(self, log_files: List[Path]):
        """로그 파일 삭제"""
        if not log_files:
            return

        print(f"\n{Color.YELLOW}삭제할 로그 번호 입력 (0: 취소): {Color.ENDC}", end="")
        choice = input().strip()

        try:
            idx = int(choice)
            if idx == 0:
                return
            if 1 <= idx <= len(log_files):
                log_file = log_files[idx - 1]
                log_file.unlink()
                print(f"\n{Color.GREEN}✓ 로그 파일이 삭제되었습니다.{Color.ENDC}")
            else:
                print(f"\n{Color.RED}✗ 잘못된 번호입니다.{Color.ENDC}")
        except Exception as e:
            print(f"\n{Color.RED}✗ 오류 발생: {e}{Color.ENDC}")

        input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")

    def clear_all_logs(self):
        """모든 로그 삭제"""
        confirm = input(f"{Color.RED}정말로 모든 로그를 삭제하시겠습니까? (y/N): {Color.ENDC}").strip().lower()
        if confirm == 'y':
            try:
                count = 0
                for log_file in self.logs_dir.glob("*.log"):
                    log_file.unlink()
                    count += 1
                print(f"\n{Color.GREEN}✓ {count}개의 로그 파일이 삭제되었습니다.{Color.ENDC}")
            except Exception as e:
                print(f"\n{Color.RED}✗ 오류 발생: {e}{Color.ENDC}")
        else:
            print(f"\n{Color.YELLOW}취소되었습니다.{Color.ENDC}")

        input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")

    def run_tests(self):
        """테스트 실행"""
        self.print_header()
        print(f"\n{Color.BOLD}[ 🧪 테스트 실행 ]{Color.ENDC}\n")
        print(f"{Color.GREEN}1.{Color.ENDC} 전체 테스트")
        print(f"{Color.GREEN}2.{Color.ENDC} 유닛 테스트만")
        print(f"{Color.GREEN}3.{Color.ENDC} 통합 테스트만")
        print(f"{Color.GREEN}4.{Color.ENDC} 커버리지 포함")
        print(f"{Color.RED}0.{Color.ENDC} 뒤로 가기")
        print()

        choice = input(f"{Color.YELLOW}선택: {Color.ENDC}").strip()

        if choice == "0":
            return

        cmd = [sys.executable, "-m", "pytest"]

        if choice == "2":
            cmd.append("tests/unit")
        elif choice == "3":
            cmd.append("tests/integration")
        elif choice == "4":
            cmd.extend(["--cov=src", "--cov-report=html"])

        cmd.append("-v")

        print(f"\n{Color.YELLOW}테스트를 실행합니다...{Color.ENDC}\n")
        print(f"{Color.CYAN}명령어: {' '.join(cmd)}{Color.ENDC}\n")

        try:
            subprocess.run(cmd, cwd=self.root_dir)
        except Exception as e:
            print(f"\n{Color.RED}✗ 테스트 실행 중 오류 발생: {e}{Color.ENDC}")

        input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")

    def show_settings(self):
        """설정 확인"""
        self.print_header()
        print(f"\n{Color.BOLD}[ ⚙️  설정 ]{Color.ENDC}\n")

        if self.config_file.exists():
            print(f"{Color.CYAN}설정 파일: {self.config_file}{Color.ENDC}\n")
            with open(self.config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 처음 30줄만 표시
                lines = content.split('\n')[:30]
                for line in lines:
                    print(line)
                if len(content.split('\n')) > 30:
                    print(f"\n{Color.YELLOW}... (이하 생략){Color.ENDC}")
        else:
            print(f"{Color.RED}설정 파일이 없습니다.{Color.ENDC}")

        print(f"\n{Color.GREEN}1.{Color.ENDC} 설정 파일 편집 (기본 편집기)")
        print(f"{Color.GREEN}2.{Color.ENDC} 설정 파일 위치 열기")
        print(f"{Color.RED}0.{Color.ENDC} 뒤로 가기")
        print()

        choice = input(f"{Color.YELLOW}선택: {Color.ENDC}").strip()

        if choice == "1":
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(str(self.config_file))
                else:  # Unix/Linux/Mac
                    subprocess.run(['xdg-open', str(self.config_file)])
            except Exception as e:
                print(f"\n{Color.RED}✗ 편집기 실행 중 오류: {e}{Color.ENDC}")
                input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")
        elif choice == "2":
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(str(self.config_file.parent))
                else:  # Unix/Linux/Mac
                    subprocess.run(['xdg-open', str(self.config_file.parent)])
            except Exception as e:
                print(f"\n{Color.RED}✗ 폴더 열기 중 오류: {e}{Color.ENDC}")
                input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")

    def show_game_info(self):
        """게임 정보 표시"""
        self.print_header()
        print(f"\n{Color.BOLD}[ ℹ️  게임 정보 ]{Color.ENDC}\n")

        print(f"{Color.CYAN}게임 이름:{Color.ENDC} Dawn of Stellar - 별빛의 여명")
        print(f"{Color.CYAN}버전:{Color.ENDC} 5.0.0 (재구조화)")
        print(f"{Color.CYAN}장르:{Color.ENDC} 로그라이크 RPG + JRPG 퓨전")
        print(f"{Color.CYAN}엔진:{Color.ENDC} Python 3.10+ / TCOD")
        print()
        print(f"{Color.YELLOW}[ 주요 기능 ]{Color.ENDC}")
        print(f"  • 28개 직업 시스템")
        print(f"  • ATB + Brave 전투 시스템")
        print(f"  • AI 동료 시스템")
        print(f"  • 절차적 던전 생성")
        print(f"  • 멀티플레이어 지원")
        print()
        print(f"{Color.YELLOW}[ 프로젝트 구조 ]{Color.ENDC}")
        print(f"  • src/         : 소스 코드")
        print(f"  • data/        : 게임 데이터 (YAML)")
        print(f"  • assets/      : 에셋 (오디오, 폰트)")
        print(f"  • saves/       : 세이브 파일")
        print(f"  • logs/        : 로그 파일")
        print(f"  • tests/       : 테스트")
        print()
        print(f"{Color.YELLOW}[ 문서 ]{Color.ENDC}")
        print(f"  • .claude/CLAUDE.md  : 프로젝트 가이드")
        print(f"  • README.md          : 프로젝트 설명")

        input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")

    def system_check(self):
        """시스템 체크"""
        self.print_header()
        print(f"\n{Color.BOLD}[ 🔍 시스템 체크 ]{Color.ENDC}\n")

        # Python 버전
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        print(f"{Color.CYAN}Python 버전:{Color.ENDC} {python_version}", end="")
        if sys.version_info >= (3, 10):
            print(f" {Color.GREEN}✓{Color.ENDC}")
        else:
            print(f" {Color.RED}✗ (3.10+ 필요){Color.ENDC}")

        # 필수 파일 확인
        print(f"\n{Color.YELLOW}[ 필수 파일 확인 ]{Color.ENDC}")
        essential_files = [
            ("main.py", self.main_script),
            ("config.yaml", self.config_file),
            ("src/", self.root_dir / "src"),
            ("data/", self.root_dir / "data"),
        ]

        for name, path in essential_files:
            exists = path.exists()
            status = f"{Color.GREEN}✓{Color.ENDC}" if exists else f"{Color.RED}✗{Color.ENDC}"
            print(f"  {name:20} {status}")

        # 디렉토리 용량
        print(f"\n{Color.YELLOW}[ 디렉토리 용량 ]{Color.ENDC}")
        dirs_to_check = [
            ("세이브", self.saves_dir),
            ("로그", self.logs_dir),
        ]

        for name, dir_path in dirs_to_check:
            if dir_path.exists():
                total_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                file_count = len(list(dir_path.rglob('*')))
                print(f"  {name:10} {total_size:>12,} bytes ({file_count}개 파일)")
            else:
                print(f"  {name:10} {Color.RED}디렉토리 없음{Color.ENDC}")

        # 필수 라이브러리 확인
        print(f"\n{Color.YELLOW}[ 필수 라이브러리 ]{Color.ENDC}")
        required_libs = ["tcod", "yaml", "pytest"]

        for lib in required_libs:
            try:
                __import__(lib)
                print(f"  {lib:15} {Color.GREEN}✓{Color.ENDC}")
            except ImportError:
                print(f"  {lib:15} {Color.RED}✗ (설치 필요: pip install {lib}){Color.ENDC}")

        input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")

    def run(self):
        """런처 메인 루프"""
        while True:
            self.print_header()
            self.print_menu()

            choice = input(f"{Color.YELLOW}선택: {Color.ENDC}").strip()

            if choice == "1":
                self.run_game("normal")
            elif choice == "2":
                self.run_game("dev")
            elif choice == "3":
                self.run_game("debug")
            elif choice == "4":
                self.manage_saves()
            elif choice == "5":
                self.view_logs()
            elif choice == "6":
                self.run_tests()
            elif choice == "7":
                self.show_settings()
            elif choice == "8":
                self.show_game_info()
            elif choice == "9":
                self.system_check()
            elif choice == "0":
                print(f"\n{Color.CYAN}게임 런처를 종료합니다. 안녕히 가세요!{Color.ENDC}\n")
                break
            else:
                print(f"\n{Color.RED}잘못된 선택입니다. 다시 선택해주세요.{Color.ENDC}")
                input(f"\n{Color.YELLOW}Press Enter to continue...{Color.ENDC}")


def main():
    """메인 함수"""
    try:
        launcher = GameLauncher()
        launcher.run()
    except KeyboardInterrupt:
        print(f"\n\n{Color.CYAN}게임 런처를 종료합니다.{Color.ENDC}\n")
    except Exception as e:
        print(f"\n{Color.RED}오류 발생: {e}{Color.ENDC}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
