// Dawn of Stellar - 전투 시스템 데모

class Character {
    constructor(name, hp, mp, brv, maxBrv, attack, defense) {
        this.name = name;
        this.hp = hp;
        this.maxHp = hp;
        this.mp = mp;
        this.maxMp = mp;
        this.brv = brv;
        this.maxBrv = maxBrv;
        this.attack = attack;
        this.defense = defense;
        this.atb = 0;
        this.speed = 50 + Math.random() * 20;
        this.isBroken = false;
    }

    updateATB() {
        if (this.atb < 2000) {
            this.atb += this.speed;
            if (this.atb > 2000) this.atb = 2000;
        }
    }

    canAct() {
        return this.atb >= 1000 && this.hp > 0;
    }

    consumeATB() {
        this.atb -= 1000;
    }

    brvAttack(target) {
        const brvDamage = Math.floor((this.attack / target.defense) * 2.0 * 75 * (0.9 + Math.random() * 0.2));
        target.brv -= brvDamage;
        this.brv += brvDamage;

        if (this.brv > this.maxBrv) this.brv = this.maxBrv;

        // BREAK 체크
        let breakBonus = 1.0;
        if (target.brv <= 0) {
            target.isBroken = true;
            breakBonus = 1.5;
            target.brv = 0;
            log(`💥 BREAK! ${target.name}이(가) 무력화되었습니다!`, 'break');
        }

        return { brvDamage, breakBonus };
    }

    hpAttack(target) {
        const hpDamage = Math.floor(this.brv * 0.25 * (this.attack / (target.defense + 1)) * (target.isBroken ? 1.5 : 1.0));
        target.hp -= hpDamage;
        if (target.hp < 0) target.hp = 0;

        this.brv = 100; // 초기화
        target.isBroken = false;

        return hpDamage;
    }
}

// 캐릭터 초기화
const player = new Character('전사', 210, 32, 1000, 1500, 60, 60);
const enemy = new Character('고블린', 150, 20, 800, 1000, 40, 30);

let gameInterval = null;
let autoMode = false;

// UI 업데이트
function updateUI() {
    // Player
    document.getElementById('player-hp').style.width = `${(player.hp / player.maxHp) * 100}%`;
    document.getElementById('player-hp-text').textContent = `${player.hp}/${player.maxHp}`;
    document.getElementById('player-mp').style.width = `${(player.mp / player.maxMp) * 100}%`;
    document.getElementById('player-mp-text').textContent = `${player.mp}/${player.maxMp}`;
    document.getElementById('player-brv').style.width = `${(player.brv / player.maxBrv) * 100}%`;
    document.getElementById('player-brv-text').textContent = `${player.brv}/${player.maxBrv}`;
    document.getElementById('player-atb').style.width = `${(player.atb / 2000) * 100}%`;
    document.getElementById('player-atb-text').textContent = `${Math.floor(player.atb)}/2000`;

    // Enemy
    document.getElementById('enemy-hp').style.width = `${(enemy.hp / enemy.maxHp) * 100}%`;
    document.getElementById('enemy-hp-text').textContent = `${enemy.hp}/${enemy.maxHp}`;
    document.getElementById('enemy-mp').style.width = `${(enemy.mp / enemy.maxMp) * 100}%`;
    document.getElementById('enemy-mp-text').textContent = `${enemy.mp}/${enemy.maxMp}`;
    document.getElementById('enemy-brv').style.width = `${(enemy.brv / enemy.maxBrv) * 100}%`;
    document.getElementById('enemy-brv-text').textContent = `${enemy.brv}/${enemy.maxBrv}`;
    document.getElementById('enemy-atb').style.width = `${(enemy.atb / 2000) * 100}%`;
    document.getElementById('enemy-atb-text').textContent = `${Math.floor(enemy.atb)}/2000`;

    // 버튼 활성화
    const canPlayerAct = player.canAct();
    document.getElementById('brv-attack').disabled = !canPlayerAct;
    document.getElementById('hp-attack').disabled = !canPlayerAct;
    document.getElementById('skill-attack').disabled = !canPlayerAct || player.mp < 15;
}

// 로그
function log(message, type = 'normal') {
    const logDiv = document.getElementById('combat-log');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = message;
    logDiv.appendChild(entry);
    logDiv.scrollTop = logDiv.scrollHeight;
}

// 게임 루프
function gameLoop() {
    // ATB 증가
    player.updateATB();
    enemy.updateATB();

    // AI 행동
    if (enemy.canAct() && !checkGameOver()) {
        enemyAI();
        enemy.consumeATB();
    }

    // 자동 모드
    if (autoMode && player.canAct() && !checkGameOver()) {
        playerBrvAttack();
        player.consumeATB();
    }

    updateUI();
}

// 플레이어 행동
function playerBrvAttack() {
    const result = player.brvAttack(enemy);
    log(`⚔️ ${player.name}의 BRV 공격! ${enemy.name}의 BRV ${result.brvDamage} 감소, ${player.name}의 BRV ${result.brvDamage} 증가`, 'damage');
    player.consumeATB();
    updateUI();
    checkGameOver();
}

function playerHpAttack() {
    const damage = player.hpAttack(enemy);
    log(`💥 ${player.name}의 HP 공격! ${enemy.name}에게 ${damage} 데미지!`, 'damage');
    player.consumeATB();
    updateUI();
    checkGameOver();
}

function playerSkillAttack() {
    if (player.mp < 15) return;
    player.mp -= 15;

    const brvDamage = Math.floor((player.attack / enemy.defense) * 2.5 * 75 * (0.9 + Math.random() * 0.2));
    enemy.brv -= brvDamage;
    player.brv += brvDamage;

    if (player.brv > player.maxBrv) player.brv = player.maxBrv;

    if (enemy.brv <= 0) {
        enemy.isBroken = true;
        enemy.brv = 0;
        log(`💥 BREAK! ${enemy.name}이(가) 무력화되었습니다!`, 'break');
    }

    log(`🔥 ${player.name}의 강타! ${enemy.name}의 BRV ${brvDamage} 감소!`, 'damage');
    player.consumeATB();
    updateUI();
    checkGameOver();
}

// AI
function enemyAI() {
    const action = Math.random();

    if (action < 0.4 || enemy.brv < 300) {
        // BRV 공격
        const result = enemy.brvAttack(player);
        log(`👹 ${enemy.name}의 BRV 공격! ${player.name}의 BRV ${result.brvDamage} 감소`, 'damage');
    } else {
        // HP 공격
        const damage = enemy.hpAttack(player);
        log(`👹 ${enemy.name}의 HP 공격! ${player.name}에게 ${damage} 데미지!`, 'damage');
    }

    checkGameOver();
}

// 승패 체크
function checkGameOver() {
    if (player.hp <= 0) {
        log('💀 패배! 전사가 쓰러졌습니다.', 'damage');
        stopGame();
        setTimeout(() => {
            if (confirm('다시 도전하시겠습니까?')) {
                location.reload();
            }
        }, 1000);
        return true;
    }

    if (enemy.hp <= 0) {
        log('🎉 승리! 고블린을 처치했습니다!', 'heal');
        stopGame();
        setTimeout(() => {
            if (confirm('다시 플레이하시겠습니까?')) {
                location.reload();
            }
        }, 1000);
        return true;
    }

    return false;
}

function startGame() {
    if (!gameInterval) {
        gameInterval = setInterval(gameLoop, 100);
        log('⏯️ 게임 시작!');
    }
}

function stopGame() {
    if (gameInterval) {
        clearInterval(gameInterval);
        gameInterval = null;
    }
}

function toggleAuto() {
    autoMode = !autoMode;
    document.getElementById('auto-btn').textContent = autoMode ? '자동 중지' : '자동 전투';
    if (autoMode) {
        log('🤖 자동 전투 모드 활성화');
    } else {
        log('👤 수동 전투 모드');
    }
}

// 이벤트 리스너
document.getElementById('brv-attack').addEventListener('click', playerBrvAttack);
document.getElementById('hp-attack').addEventListener('click', playerHpAttack);
document.getElementById('skill-attack').addEventListener('click', playerSkillAttack);
document.getElementById('auto-btn').addEventListener('click', toggleAuto);

// 게임 시작
startGame();
updateUI();
