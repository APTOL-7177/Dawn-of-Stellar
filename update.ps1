# Dawn of Stellar 업데이트 스크립트
# PowerShell 스크립트
# 버전: 1.0.0

# UTF-8 인코딩 설정
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 색상 출력 함수
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        $message = $args -join " "
        Write-Output $message
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
}

function Write-Info($text) {
    Write-ColorOutput White "    → $text"
}

function Write-Warning($text) {
    Write-ColorOutput Yellow "  ⚠ $text"
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

# 게임 업데이트
function Update-Game {
    Write-Header "게임 업데이트"
    
    # Git 저장소인지 확인
    if (-not (Test-GitRepository)) {
        Write-Error "현재 폴더가 Git 저장소가 아닙니다"
        Write-Info "Git으로 클론한 프로젝트만 업데이트할 수 있습니다"
        Write-Info "설치 마법사를 사용하세요: .\install.ps1"
        return $false
    }
    
    # Git이 설치되어 있는지 확인
    $gitInstalled, $gitVersion = Test-GitInstalled
    if (-not $gitInstalled) {
        Write-Error "Git이 설치되어 있지 않습니다"
        Write-Info "Git을 설치해야 업데이트할 수 있습니다"
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

# 메인 실행
try {
    Clear-Host
    Write-Header "⭐ Dawn of Stellar 업데이트 ⭐"
    Write-ColorOutput Cyan "  버전: 1.0.0"
    Write-ColorOutput Cyan "  게임: Dawn of Stellar (별빛의 여명)"
    Write-Output ""
    
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
                Write-Info "수동으로 실행해주세요: python main.py"
            }
        }
    }
    
    Write-Output ""
    Write-ColorOutput Cyan "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-ColorOutput Cyan "업데이트 완료! ⭐"
    Write-ColorOutput Cyan "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Output ""
    Read-Host "종료하려면 Enter를 누르세요"
} catch {
    Write-Error "치명적인 오류가 발생했습니다: $_"
    Read-Host "종료하려면 Enter를 누르세요"
    exit 1
}

