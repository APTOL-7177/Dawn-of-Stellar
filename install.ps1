# Dawn of Stellar 설치 마법사
# PowerShell 스크립트
# 버전: 1.0.0

# UTF-8 인코딩 설정
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 전역 변수
$script:StartTime = Get-Date
$script:InstallLog = @()
$script:Errors = @()

# 색상 출력 함수
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        $message = $args -join " "
        Write-Output $message
        $script:InstallLog += "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $message"
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Header($text) {
    Write-ColorOutput Cyan "`n╔══════════════════════════════════════════════════════════╗"
    Write-ColorOutput Cyan "║  $($text.PadRight(54))║"
    Write-ColorOutput Cyan "╚══════════════════════════════════════════════════════════╝`n"
}

function Write-Step($step, $text) {
    Write-ColorOutput Yellow "  [$step] $text"
}

function Write-Success($text) {
    Write-ColorOutput Green "  ✓ $text"
}

function Write-Error($text) {
    Write-ColorOutput Red "  ✗ $text"
    $script:Errors += $text
}

function Write-Info($text) {
    Write-ColorOutput White "    → $text"
}

function Write-Warning($text) {
    Write-ColorOutput Yellow "  ⚠ $text"
}


# 관리자 권한 확인
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# 프로그램 설치 확인
function Test-Command($command) {
    try {
        $null = Get-Command $command -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# Python 버전 확인
function Test-PythonVersion {
    try {
        $version = python --version 2>&1
        if ($version -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -ge 3 -and $minor -ge 10) {
                return $true, $version
            }
        }
        return $false, $version
    } catch {
        return $false, "Python이 설치되어 있지 않습니다"
    }
}

# Git 설치 확인
function Test-GitInstalled {
    try {
        $version = git --version 2>&1
        return $true, $version
    } catch {
        return $false, "Git이 설치되어 있지 않습니다"
    }
}

# Git 다운로드 URL 열기
function Open-GitDownload {
    Write-Info "Git 다운로드 페이지를 엽니다..."
    Start-Process "https://git-scm.com/download/win"
}

# Git 저장소 클론
function Clone-Repository {
    param(
        [string]$RepositoryUrl = "https://github.com/APTOL-7177/Dawn-of-Stellar.git",
        [string]$TargetPath = "Dawn-of-Stellar"
    )
    
    Write-Step "0-2" "Git 저장소 클론 중..."
    Write-Info "저장소: $RepositoryUrl"
    Write-Info "대상 폴더: $TargetPath"
    Write-Info "현재 위치: $(Get-Location)"
    Write-Output ""
    
    # Git이 설치되어 있는지 확인
    $gitInstalled, $gitVersion = Test-GitInstalled
    if (-not $gitInstalled) {
        Write-Error "Git이 설치되어 있지 않습니다"
        Write-Info "Git을 먼저 설치해야 저장소를 클론할 수 있습니다"
        $installGit = Read-Host "Git을 설치하시겠습니까? (Y/N)"
        if ($installGit -eq "Y" -or $installGit -eq "y") {
            Open-GitDownload
            Write-Info "Git 설치 후 이 스크립트를 다시 실행하세요."
            return $false
        } else {
            return $false
        }
    }
    
    # 이미 폴더가 존재하는지 확인
    if (Test-Path $TargetPath -PathType Container) {
        Write-Warning "$TargetPath 폴더가 이미 존재합니다"
        $overwrite = Read-Host "덮어쓰시겠습니까? (Y/N) - N을 선택하면 기존 폴더를 사용합니다"
        if ($overwrite -eq "Y" -or $overwrite -eq "y") {
            Write-Info "기존 폴더를 삭제하는 중..."
            Remove-Item -Path $TargetPath -Recurse -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        } else {
            Write-Info "기존 폴더를 사용합니다: $TargetPath"
            if (Test-Path (Join-Path $TargetPath "main.py")) {
                Set-Location $TargetPath
                return $true
            } else {
                Write-Warning "기존 폴더에 프로젝트 파일이 없습니다. 클론을 진행합니다..."
                Remove-Item -Path $TargetPath -Recurse -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 1
            }
        }
    }
    
    try {
        Write-Info "클론 중... (시간이 걸릴 수 있습니다)"
        Write-Info "진행 상황이 표시되지 않을 수 있지만 정상적으로 진행 중입니다..."
        Write-Output ""
        
        # git clone 실행 (출력 캡처)
        $output = & git clone $RepositoryUrl $TargetPath 2>&1
        $exitCode = $LASTEXITCODE
        
        if ($exitCode -eq 0) {
            Write-Success "저장소 클론 완료!"
            
            # 클론된 폴더로 이동
            if (Test-Path $TargetPath -PathType Container) {
                Set-Location $TargetPath
                Write-Info "프로젝트 폴더로 이동: $(Get-Location)"
                
                # requirements.txt 확인
                if (Test-Path "requirements.txt") {
                    Write-Success "requirements.txt 확인됨"
                } else {
                    Write-Error "requirements.txt를 찾을 수 없습니다"
                    return $false
                }
                
                # main.py 확인
                if (Test-Path "main.py") {
                    Write-Success "main.py 확인됨"
                } else {
                    Write-Error "main.py를 찾을 수 없습니다"
                    return $false
                }
                
                return $true
            } else {
                Write-Error "클론된 폴더를 찾을 수 없습니다"
                return $false
            }
        } else {
            Write-Error "클론 실패 (종료 코드: $exitCode)"
            if ($output) {
                Write-Info "오류 메시지: $output"
            }
            Write-Info "수동으로 클론하려면: git clone $RepositoryUrl"
            return $false
        }
    } catch {
        Write-Error "클론 중 오류 발생: $_"
        Write-Info "수동으로 클론하려면: git clone $RepositoryUrl"
        return $false
    }
}

# 프로젝트 폴더 확인
function Test-ProjectFolder {
    $hasMainPy = Test-Path "main.py"
    $hasRequirements = Test-Path "requirements.txt"
    $hasSrcFolder = Test-Path "src" -PathType Container
    
    return ($hasMainPy -and $hasRequirements -and $hasSrcFolder)
}

# Git 저장소인지 확인
function Test-GitRepository {
    if (-not (Test-Path ".git" -PathType Container)) {
        return $false
    }
    
    try {
        $output = & git rev-parse --is-inside-work-tree 2>&1
        return ($LASTEXITCODE -eq 0 -and $output -eq "true")
    } catch {
        return $false
    }
}

# 현재 Git 브랜치 확인
function Get-CurrentBranch {
    try {
        $branch = & git rev-parse --abbrev-ref HEAD 2>&1
        if ($LASTEXITCODE -eq 0) {
            return $branch
        }
        return $null
    } catch {
        return $null
    }
}

# 원격 저장소와 비교하여 업데이트 확인
function Test-UpdateAvailable {
    try {
        # 원격 정보 가져오기
        & git fetch origin --quiet 2>&1 | Out-Null
        
        # 현재 브랜치
        $currentBranch = Get-CurrentBranch
        if (-not $currentBranch) {
            return $false, "브랜치를 확인할 수 없습니다"
        }
        
        # 로컬과 원격 비교
        $localCommit = & git rev-parse HEAD 2>&1
        $remoteCommit = & git rev-parse "origin/$currentBranch" 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            return $false, "원격 브랜치를 찾을 수 없습니다"
        }
        
        if ($localCommit -ne $remoteCommit) {
            # 몇 개의 커밋이 앞서있는지 확인
            $ahead = & git rev-list --count "HEAD..origin/$currentBranch" 2>&1
            if ($LASTEXITCODE -eq 0 -and [int]$ahead -gt 0) {
                return $true, "$ahead 개의 새로운 커밋이 있습니다"
            }
        }
        
        return $false, "이미 최신 버전입니다"
    } catch {
        return $false, "업데이트 확인 실패: $_"
    }
}

# 게임 업데이트
function Update-Game {
    Write-Header "게임 업데이트"
    
    # Git 저장소인지 확인
    if (-not (Test-GitRepository)) {
        Write-Error "현재 폴더가 Git 저장소가 아닙니다"
        Write-Info "Git으로 클론한 프로젝트만 업데이트할 수 있습니다"
        return $false
    }
    
    # Git이 설치되어 있는지 확인
    $gitInstalled, $gitVersion = Test-GitInstalled
    if (-not $gitInstalled) {
        Write-Error "Git이 설치되어 있지 않습니다"
        return $false
    }
    
    # 현재 브랜치 확인
    $currentBranch = Get-CurrentBranch
    if ($currentBranch) {
        Write-Info "현재 브랜치: $currentBranch"
    } else {
        Write-Warning "브랜치를 확인할 수 없습니다"
    }
    
    Write-Output ""
    
    # 업데이트 확인
    Write-Step "1" "업데이트 확인 중..."
    $hasUpdate, $updateMessage = Test-UpdateAvailable
    
    if (-not $hasUpdate) {
        Write-Info $updateMessage
        Write-Success "이미 최신 버전입니다!"
        return $true
    }
    
    Write-Warning $updateMessage
    Write-Output ""
    
    # 변경사항이 있으면 백업 확인
    $status = & git status --porcelain 2>&1
    if ($status -and $status.Count -gt 0) {
        Write-Warning "로컬에 변경사항이 있습니다"
        Write-Info "변경된 파일:"
        $status | ForEach-Object { Write-Info "  $_" }
        Write-Output ""
        $backup = Read-Host "변경사항을 스태시(임시 저장)하시겠습니까? (Y/N)"
        if ($backup -eq "Y" -or $backup -eq "y") {
            try {
                & git stash push -m "업데이트 전 자동 백업 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "변경사항이 스태시되었습니다"
                } else {
                    Write-Warning "스태시 실패 (계속 진행합니다)"
                }
            } catch {
                Write-Warning "스태시 중 오류 발생 (계속 진행합니다): $_"
            }
        }
    }
    
    # 업데이트 실행
    Write-Step "2" "업데이트 다운로드 중..."
    try {
        $pullOutput = & git pull origin $currentBranch 2>&1
        $exitCode = $LASTEXITCODE
        
        if ($exitCode -eq 0) {
            Write-Success "업데이트 완료!"
            if ($pullOutput) {
                Write-Info "업데이트 내용:"
                $pullOutput | ForEach-Object { Write-Info "  $_" }
            }
        } else {
            Write-Error "업데이트 실패 (종료 코드: $exitCode)"
            if ($pullOutput) {
                Write-Info "오류 메시지:"
                $pullOutput | ForEach-Object { Write-Info "  $_" }
            }
            return $false
        }
    } catch {
        Write-Error "업데이트 중 오류 발생: $_"
        return $false
    }
    
    # requirements.txt 변경 확인 및 재설치
    Write-Output ""
    Write-Step "3" "의존성 확인 중..."
    
    # Git으로 requirements.txt 변경 확인
    $reqChanged = $false
    try {
        $diff = & git diff HEAD@{1} HEAD --name-only requirements.txt 2>&1
        if ($diff -and $diff -match "requirements.txt") {
            $reqChanged = $true
        }
    } catch {
        # 이전 커밋이 없을 수 있으므로 무시
    }
    
    if ($reqChanged -or -not (Test-Path ".requirements_installed")) {
        Write-Info "requirements.txt가 변경되었거나 패키지 설치가 필요합니다"
        $reinstall = Read-Host "Python 패키지를 다시 설치하시겠습니까? (Y/N)"
        if ($reinstall -eq "Y" -or $reinstall -eq "y") {
            Update-Pip
            Install-Requirements
            # 설치 완료 마커 생성
            "" | Out-File -FilePath ".requirements_installed" -Encoding UTF8
        }
    } else {
        Write-Success "의존성 변경 없음"
    }
    
    Write-Output ""
    Write-Success "게임 업데이트가 완료되었습니다!"
    return $true
}

# Python 다운로드 URL 열기
function Open-PythonDownload {
    Write-Info "Python 다운로드 페이지를 엽니다..."
    Start-Process "https://www.python.org/downloads/"
}

# pip 업그레이드
function Update-Pip {
    Write-Step "3-1" "pip 업그레이드 중..."
    try {
        $output = python -m pip install --upgrade pip 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "pip 업그레이드 완료"
            return $true
        } else {
            Write-Warning "pip 업그레이드 중 경고가 발생했습니다 (계속 진행합니다)"
            return $true
        }
    } catch {
        Write-Warning "pip 업그레이드 실패 (계속 진행합니다): $_"
        return $true
    }
}

# requirements.txt 설치
function Install-Requirements {
    Write-Step "3-2" "Python 패키지 설치 중..."
    
    if (-not (Test-Path "requirements.txt")) {
        Write-Error "requirements.txt 파일을 찾을 수 없습니다"
        return $false
    }
    
    Write-Info "패키지 목록을 확인하는 중..."
    $packages = Get-Content "requirements.txt" | Where-Object { $_ -notmatch '^#' -and $_.Trim() -ne '' }
    $packageCount = ($packages | Measure-Object).Count
    Write-Info "총 $packageCount 개의 패키지를 설치합니다..."
    Write-Info "이 작업은 몇 분 정도 걸릴 수 있습니다..."
    Write-Output ""
    
    $maxRetries = 2
    $retryCount = 0
    $installed = $false
    
    while ($retryCount -lt $maxRetries -and -not $installed) {
        try {
            Write-Info "패키지 설치 중... (시도 $($retryCount + 1)/$maxRetries)"
            
            # pip install with progress
            $process = Start-Process python -ArgumentList "-m", "pip", "install", "-r", "requirements.txt", "--disable-pip-version-check" -NoNewWindow -PassThru -Wait
            
            if ($process.ExitCode -eq 0) {
                $installed = $true
                Write-Success "모든 패키지 설치 완료"
            } else {
                $retryCount++
                if ($retryCount -lt $maxRetries) {
                    Write-Warning "설치 실패. 재시도 중... ($retryCount/$maxRetries)"
                    Start-Sleep -Seconds 3
                }
            }
        } catch {
            $retryCount++
            if ($retryCount -lt $maxRetries) {
                Write-Warning "오류 발생. 재시도 중... ($retryCount/$maxRetries)"
                Write-Info "오류: $_"
                Start-Sleep -Seconds 3
            } else {
                Write-Error "패키지 설치 실패: $_"
            }
        }
    }
    
    if (-not $installed) {
        Write-Error "패키지 설치에 실패했습니다"
        Write-Info "수동으로 설치하려면 다음 명령어를 실행하세요:"
        Write-ColorOutput Yellow "  pip install -r requirements.txt"
        return $false
    }
    
    return $true
}

# 필수 파일 검증
function Test-RequiredFiles {
    Write-Step "4-1" "필수 파일 검증 중..."
    
    $requiredFiles = @(
        "main.py",
        "requirements.txt",
        "config.yaml"
    )
    
    $requiredDirs = @(
        "src",
        "data"
    )
    
    $allOk = $true
    
    foreach ($file in $requiredFiles) {
        if (Test-Path $file) {
            Write-Success "$file 확인됨"
        } else {
            Write-Error "$file 파일이 없습니다"
            $allOk = $false
        }
    }
    
    foreach ($dir in $requiredDirs) {
        if (Test-Path $dir -PathType Container) {
            Write-Success "$dir 폴더 확인됨"
        } else {
            Write-Error "$dir 폴더가 없습니다"
            $allOk = $false
        }
    }
    
    return $allOk
}

# 게임 실행 테스트
function Test-GameRun {
    Write-Step "4-2" "게임 실행 테스트 중..."
    
    Write-Info "필수 패키지 import 테스트 중..."
    
    $testScript = @"
import sys
errors = []
try:
    import tcod
    print('✓ tcod')
except ImportError as e:
    errors.append('tcod')
    print('✗ tcod:', e)

try:
    import yaml
    print('✓ yaml')
except ImportError as e:
    errors.append('yaml')
    print('✗ yaml:', e)

try:
    import numpy
    print('✓ numpy')
except ImportError as e:
    errors.append('numpy')
    print('✗ numpy:', e)

if errors:
    print(f'\n누락된 패키지: {", ".join(errors)}')
    sys.exit(1)
else:
    print('\n모든 필수 패키지가 정상적으로 설치되었습니다!')
    sys.exit(0)
"@
    
    try {
        $testScript | python 2>&1 | ForEach-Object {
            if ($_ -match '^✓') {
                Write-ColorOutput Green "    $_"
            } elseif ($_ -match '^✗') {
                Write-ColorOutput Red "    $_"
            } else {
                Write-Output "    $_"
            }
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "게임 실행 준비 완료!"
            return $true
        } else {
            Write-Error "일부 패키지가 누락되었습니다"
            Write-Info "수동으로 설치하려면: pip install -r requirements.txt"
            return $false
        }
    } catch {
        Write-Error "테스트 실패: $_"
        return $false
    }
}

# 설치 요약 출력
function Show-InstallSummary {
    $elapsed = (Get-Date) - $script:StartTime
    $minutes = [math]::Floor($elapsed.TotalMinutes)
    $seconds = $elapsed.Seconds
    
    Write-Header "설치 요약"
    Write-Info "설치 시간: ${minutes}분 ${seconds}초"
    Write-Info "설치 로그 항목: $($script:InstallLog.Count)개"
    
    if ($script:Errors.Count -gt 0) {
        Write-Warning "발생한 오류: $($script:Errors.Count)개"
        foreach ($error in $script:Errors) {
            Write-Info "  - $error"
        }
    } else {
        Write-Success "오류 없이 설치가 완료되었습니다!"
    }
}

# 메인 설치 프로세스
function Start-Installation {
    Clear-Host
    Write-Header "⭐ Dawn of Stellar 설치 마법사 ⭐"
    Write-ColorOutput Cyan "  버전: 1.0.0"
    Write-ColorOutput Cyan "  게임: Dawn of Stellar (별빛의 여명)"
    Write-Output ""
    
    # 메뉴 선택
    $isProjectFolder = Test-ProjectFolder
    $isGitRepo = Test-GitRepository
    
    if ($isProjectFolder) {
        Write-ColorOutput Cyan "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        Write-ColorOutput Cyan "메뉴 선택"
        Write-ColorOutput Cyan "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        Write-Output ""
        Write-ColorOutput White "  1. 새로 설치하기"
        if ($isGitRepo) {
            Write-ColorOutput White "  2. 게임 업데이트"
            Write-ColorOutput White "  3. 종료"
        } else {
            Write-ColorOutput White "  2. 종료"
        }
        Write-Output ""
        
        $menuChoice = Read-Host "선택하세요 (1-$(if ($isGitRepo) { '3' } else { '2' }))"
        
        if ($menuChoice -eq "2" -and $isGitRepo) {
            # 업데이트 모드
            $updateSuccess = Update-Game
            Write-Output ""
            if ($updateSuccess) {
                $runNow = Read-Host "지금 게임을 실행하시겠습니까? (Y/N)"
                if ($runNow -eq "Y" -or $runNow -eq "y") {
                    Write-Info "게임을 시작합니다..."
                    try {
                        if (Test-Path "start_game.bat") {
                            Start-Process "start_game.bat" -NoNewWindow
                        } else {
                            Start-Process python -ArgumentList "main.py" -NoNewWindow
                        }
                        Write-Success "게임이 시작되었습니다!"
                    } catch {
                        Write-Error "게임 실행 실패: $_"
                    }
                }
            }
            Read-Host "종료하려면 Enter를 누르세요"
            return
        } elseif ($menuChoice -eq "2" -and -not $isGitRepo) {
            Write-Info "종료합니다."
            return
        } elseif ($menuChoice -eq "3" -and $isGitRepo) {
            Write-Info "종료합니다."
            return
        } elseif ($menuChoice -ne "1") {
            Write-Info "잘못된 선택입니다. 설치를 계속합니다..."
            Write-Output ""
        }
    }
    
    # 0단계: 프로젝트 폴더 확인
    Write-Header "0단계: 프로젝트 폴더 확인"
    
    if (-not $isProjectFolder) {
        Write-Warning "현재 폴더에 프로젝트 파일이 없습니다"
        Write-Info "현재 위치: $(Get-Location)"
        Write-Output ""
        Write-Info "GitHub에서 프로젝트를 클론해야 합니다"
        $cloneRepo = Read-Host "저장소를 클론하시겠습니까? (Y/N)"
        
        if ($cloneRepo -eq "Y" -or $cloneRepo -eq "y") {
            $cloneSuccess = Clone-Repository
            if (-not $cloneSuccess) {
                Write-Error "저장소 클론에 실패했습니다"
                Write-Info "수동으로 클론하려면:"
                Write-ColorOutput Yellow "  git clone https://github.com/APTOL-7177/Dawn-of-Stellar.git"
                Write-Info "그 다음 클론된 폴더에서 이 스크립트를 다시 실행하세요"
                Read-Host "종료하려면 Enter를 누르세요"
                return
            }
            
            # 클론 후 현재 위치 확인
            Write-Info "클론 후 위치: $(Get-Location)"
            
            # 클론 후 다시 확인
            $isProjectFolder = Test-ProjectFolder
            if (-not $isProjectFolder) {
                Write-Error "클론 후에도 프로젝트 파일을 찾을 수 없습니다"
                Write-Info "현재 위치의 파일 목록:"
                Get-ChildItem -Name | ForEach-Object { Write-Info "  - $_" }
                Read-Host "종료하려면 Enter를 누르세요"
                return
            }
            
            # requirements.txt 명시적 확인
            if (Test-Path "requirements.txt") {
                Write-Success "requirements.txt 확인됨"
                $reqContent = Get-Content "requirements.txt" -TotalCount 5
                Write-Info "requirements.txt 내용 (처음 5줄):"
                $reqContent | ForEach-Object { Write-Info "  $_" }
            } else {
                Write-Error "requirements.txt를 찾을 수 없습니다!"
                Read-Host "종료하려면 Enter를 누르세요"
                return
            }
        } else {
            Write-Info "프로젝트 폴더로 이동하거나 수동으로 클론한 후 다시 실행하세요"
            Write-Info "클론 명령어: git clone https://github.com/APTOL-7177/Dawn-of-Stellar.git"
            Read-Host "종료하려면 Enter를 누르세요"
            return
        }
    } else {
        Write-Success "프로젝트 폴더 확인됨: $(Get-Location)"
    }
    
    Write-Output ""
    Write-Info "이 마법사는 다음을 자동으로 설치합니다:"
    Write-ColorOutput White "    1. Git 확인 (선택 사항)"
    Write-ColorOutput White "    2. Python 3.10+ 확인 및 안내"
    Write-ColorOutput White "    3. Python 패키지 설치 (requirements.txt)"
    Write-ColorOutput White "    4. 필수 파일 검증"
    Write-ColorOutput White "    5. 게임 실행 테스트"
    Write-Output ""
    
    Write-Warning "주의: 인터넷 연결이 필요합니다."
    Write-Output ""
    
    $continue = Read-Host "계속하시겠습니까? (Y/N)"
    if ($continue -ne "Y" -and $continue -ne "y") {
        Write-Info "설치가 취소되었습니다."
        return
    }
    
    Write-Output ""
    
    # 1단계: Git 확인
    Write-Header "1단계: Git 확인"
    $gitInstalled, $gitVersion = Test-GitInstalled
    if ($gitInstalled) {
        Write-Success "Git이 설치되어 있습니다: $gitVersion"
    } else {
        Write-Warning "Git이 설치되어 있지 않습니다"
        Write-Info "Git은 소스 코드 업데이트에 유용합니다 (선택 사항)"
        Write-Info "게임 실행에는 Git이 필수는 아닙니다"
        $installGit = Read-Host "Git을 설치하시겠습니까? (Y/N)"
        if ($installGit -eq "Y" -or $installGit -eq "y") {
            Open-GitDownload
            Write-Info "Git 설치 후 이 스크립트를 다시 실행하세요."
            Read-Host "계속하려면 Enter를 누르세요"
        } else {
            Write-Info "Git 없이 계속 진행합니다..."
        }
    }
    
    # 2단계: Python 확인
    Write-Header "2단계: Python 확인"
    $pythonOk, $pythonVersion = Test-PythonVersion
    if ($pythonOk) {
        Write-Success "Python이 설치되어 있습니다: $pythonVersion"
    } else {
        Write-Error "Python 3.10 이상이 필요합니다"
        Write-Info "현재: $pythonVersion"
        $installPython = Read-Host "Python을 설치하시겠습니까? (Y/N)"
        if ($installPython -eq "Y" -or $installPython -eq "y") {
            Open-PythonDownload
            Write-Info "Python 설치 시 'Add Python to PATH' 옵션을 체크하세요!"
            Write-Info "Python 설치 후 이 스크립트를 다시 실행하세요."
            Read-Host "계속하려면 Enter를 누르세요"
            return
        } else {
            Write-Error "Python이 없으면 게임을 실행할 수 없습니다."
            return
        }
    }
    
    # 3단계: Python 패키지 설치
    Write-Header "3단계: Python 패키지 설치"
    
    # pip 업그레이드
    Update-Pip
    
    # requirements.txt 설치
    $installSuccess = Install-Requirements
    if (-not $installSuccess) {
        Write-Error "패키지 설치에 실패했습니다."
        Write-Info "수동으로 설치하려면: pip install -r requirements.txt"
        $continue = Read-Host "계속하시겠습니까? (Y/N)"
        if ($continue -ne "Y" -and $continue -ne "y") {
            return
        }
    }
    
    # 4단계: 파일 검증 및 게임 실행 테스트
    Write-Header "4단계: 파일 검증 및 게임 실행 테스트"
    
    $filesOk = Test-RequiredFiles
    if (-not $filesOk) {
        Write-Warning "일부 필수 파일이 누락되었습니다. 게임 실행에 문제가 있을 수 있습니다."
    }
    
    $testOk = Test-GameRun
    
    # 설치 요약
    Show-InstallSummary
    
    # 완료
    Write-Header "설치 완료!"
    
    if ($testOk) {
        Write-Success "Dawn of Stellar 설치가 성공적으로 완료되었습니다!"
    } else {
        Write-Warning "설치가 완료되었지만 일부 문제가 있을 수 있습니다."
    }
    
    Write-Output ""
    Write-ColorOutput Cyan "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-ColorOutput Cyan "게임 실행 방법"
    Write-ColorOutput Cyan "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Output ""
    Write-Info "방법 1: 명령 프롬프트에서 실행"
    Write-ColorOutput Green "    python main.py"
    Write-Output ""
    Write-Info "방법 2: 배치 파일 실행"
    Write-ColorOutput Green "    start_game.bat"
    Write-Output ""
    Write-Info "방법 3: 개발 모드 (모든 직업 해금)"
    Write-ColorOutput Green "    python main.py --dev"
    Write-Output ""
    
    # 설치 로그 저장
    $logFile = "install_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
    try {
        $script:InstallLog | Out-File -FilePath $logFile -Encoding UTF8
        Write-Info "설치 로그가 저장되었습니다: $logFile"
    } catch {
        Write-Warning "설치 로그 저장 실패: $_"
    }
    
    Write-Output ""
    $runNow = Read-Host "지금 게임을 실행하시겠습니까? (Y/N)"
    if ($runNow -eq "Y" -or $runNow -eq "y") {
        Write-Info "게임을 시작합니다..."
        try {
            if (Test-Path "start_game.bat") {
                Start-Process "start_game.bat" -NoNewWindow
            } else {
                Start-Process python -ArgumentList "main.py" -NoNewWindow
            }
            Write-Success "게임이 시작되었습니다!"
        } catch {
            Write-Error "게임 실행 실패: $_"
            Write-Info "수동으로 실행해주세요: python main.py"
        }
    }
    
    Write-Output ""
    Write-ColorOutput Cyan "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-ColorOutput Cyan "즐거운 게임 되세요! ⭐"
    Write-ColorOutput Cyan "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Output ""
    Read-Host "종료하려면 Enter를 누르세요"
}

# 스크립트 실행
try {
    # PowerShell 실행 정책 확인 및 안내
    $executionPolicy = Get-ExecutionPolicy
    if ($executionPolicy -eq "Restricted" -or $executionPolicy -eq "AllSigned") {
        Clear-Host
        Write-Header "⚠ 실행 정책 경고"
        Write-Warning "PowerShell 실행 정책이 제한되어 있습니다."
        Write-Info "현재 정책: $executionPolicy"
        Write-Output ""
        Write-ColorOutput Cyan "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        Write-ColorOutput Cyan "해결 방법"
        Write-ColorOutput Cyan "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        Write-Output ""
        Write-Info "방법 1: 실행 정책 변경 (영구적, 권장)"
        Write-ColorOutput Yellow "  PowerShell을 관리자 권한으로 열고:"
        Write-ColorOutput Green "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
        Write-Output ""
        Write-Info "방법 2: 이번 세션만 우회 (일시적)"
        Write-ColorOutput Yellow "  PowerShell에서 다음 명령어 실행:"
        Write-ColorOutput Green "  powershell.exe -ExecutionPolicy Bypass -File .\install.ps1"
        Write-Output ""
        Write-Info "방법 3: 계속 진행 (시도)"
        Write-ColorOutput Yellow "  아래에서 Y를 선택하면 계속 진행합니다"
        Write-Output ""
        
        $continue = Read-Host "계속 진행하시겠습니까? (Y/N)"
        if ($continue -ne "Y" -and $continue -ne "y") {
            Write-Info "설치가 취소되었습니다."
            Write-Info "위의 방법 중 하나를 사용하여 다시 시도하세요."
            Read-Host "종료하려면 Enter를 누르세요"
            exit 0
        }
        
        # 실행 정책 우회 시도
        try {
            Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force -ErrorAction SilentlyContinue
            Write-Success "이번 세션의 실행 정책을 우회했습니다"
        } catch {
            Write-Warning "실행 정책 우회 실패 (계속 진행합니다)"
        }
        Write-Output ""
        Start-Sleep -Seconds 1
    }
    
    Start-Installation
} catch {
    Write-Error "치명적인 오류가 발생했습니다: $_"
    Write-Error "오류 위치: $($_.InvocationInfo.ScriptLineNumber)번째 줄"
    Write-Output ""
    Write-Info "문제가 지속되면 다음을 확인하세요:"
    Write-Info "  1. Python이 올바르게 설치되어 있는지"
    Write-Info "  2. 인터넷 연결이 정상인지"
    Write-Info "  3. 관리자 권한이 필요한지"
    Write-Output ""
    
    # 오류 로그 저장
    $errorLog = "install_error_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
    try {
        @"
오류 발생 시간: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
오류 메시지: $_
오류 위치: $($_.InvocationInfo.ScriptLineNumber)
스택 트레이스:
$($_.ScriptStackTrace)
"@ | Out-File -FilePath $errorLog -Encoding UTF8
        Write-Info "오류 로그가 저장되었습니다: $errorLog"
    } catch {
        Write-Warning "오류 로그 저장 실패"
    }
    
    Read-Host "종료하려면 Enter를 누르세요"
    exit 1
}

