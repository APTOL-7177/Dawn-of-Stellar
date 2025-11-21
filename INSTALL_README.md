# Dawn of Stellar 설치 가이드

## 설치 방법

### 방법 1: PowerShell 스크립트 실행 (권장)

1. **PowerShell 실행 정책 설정** (최초 1회만 필요)

   관리자 권한으로 PowerShell을 열고 다음 명령어를 실행하세요:

   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

   또는 사용자 권한으로:

   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
   ```

2. **설치 스크립트 실행**

   ```powershell
   .\install.ps1
   ```

   또는 우클릭 → "PowerShell로 실행"

### 방법 2: 실행 정책 우회 (일시적)

PowerShell을 열고 다음 명령어를 실행:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\install.ps1
```

### 방법 3: 배치 파일 사용 (자동 우회)

`install.bat` 파일을 더블클릭하면 자동으로 실행 정책을 우회하고 스크립트를 실행합니다.

## 업데이트 방법

### 방법 1: 업데이트 스크립트 실행

```powershell
.\update.ps1
```

또는 실행 정책 우회:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\update.ps1
```

### 방법 2: 설치 마법사에서 업데이트 선택

```powershell
.\install.ps1
```

메뉴에서 "2. 게임 업데이트" 선택

## 문제 해결

### "디지털 서명되지 않았다" 오류

이 오류는 Windows의 보안 정책 때문입니다. 다음 중 하나를 선택하세요:

1. **실행 정책 변경** (영구적, 권장)
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. **일시적 우회** (매번 필요)
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File .\install.ps1
   ```

3. **배치 파일 사용**
   - `install.bat` 파일을 더블클릭

### "실행이 비활성화되었습니다" 오류

PowerShell을 관리자 권한으로 열고:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

### Git이 설치되지 않았을 때

1. [Git 다운로드 페이지](https://git-scm.com/download/win)에서 다운로드
2. 설치 시 기본 옵션 사용
3. 설치 후 PowerShell 재시작

### Python이 설치되지 않았을 때

1. [Python 다운로드 페이지](https://www.python.org/downloads/)에서 다운로드
2. 설치 시 **"Add Python to PATH"** 옵션 체크 필수!
3. 설치 후 PowerShell 재시작

## 수동 설치

스크립트를 사용하지 않고 수동으로 설치하려면:

```bash
# 1. 저장소 클론
git clone https://github.com/APTOL-7177/Dawn-of-Stellar.git
cd Dawn-of-Stellar

# 2. Python 패키지 설치
pip install -r requirements.txt

# 3. 게임 실행
python main.py
```

## 시스템 요구사항

- **운영체제**: Windows 10/11
- **Python**: 3.10 이상
- **Git**: 선택 사항 (업데이트용)
- **인터넷 연결**: 필수 (패키지 다운로드용)

## 추가 도움말

문제가 지속되면:
1. 설치 로그 파일 확인: `install_log_*.txt`
2. 오류 로그 확인: `install_error_*.txt`
3. [GitHub Issues](https://github.com/APTOL-7177/Dawn-of-Stellar/issues)에 문의

