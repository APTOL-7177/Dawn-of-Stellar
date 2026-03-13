"""
combat_tooltip.py - 전투 캐릭터 상세 툴팁 렌더러

전투 중 아군/적에 마우스를 올리면 상세 상태 패널을 표시합니다:
- 이름, 직업, 레벨
- HP/MP/BRV/ATB 수치
- 기본 스탯 (ATK/DEF/MAG/SPD 등)
- 장비 특수 효과
- 활성 버프/디버프 (모든 타입 지원)
- 기믹 게이지 상태
- 속성 내성/약점 (적)
"""

from typing import Any, Dict, List, Optional, Tuple

import tcod

from src.core.logger import get_logger

logger = get_logger("ui.tooltip")

# ── 레이아웃 상수 ────────────────────────────────────────────────────────
TOOLTIP_WIDTH = 32

# ── 색상 팔레트 ──────────────────────────────────────────────────────────
BG_COLOR = (12, 12, 25)
BORDER_COLOR = (80, 100, 140)
HEADER_COLOR = (200, 230, 255)
SUBHEADER_COLOR = (140, 170, 210)
STAT_COLOR = (190, 190, 210)
STAT_LABEL_COLOR = (130, 140, 170)
HP_COLOR = (100, 255, 120)
HP_LOW_COLOR = (255, 80, 80)
MP_COLOR = (100, 160, 255)
BRV_COLOR = (255, 220, 80)
ATB_COLOR = (180, 255, 180)
BUFF_COLOR = (100, 255, 150)
DEBUFF_COLOR = (255, 100, 100)
EQUIP_COLOR = (255, 200, 100)
GIMMICK_COLOR = (200, 150, 255)
SEPARATOR_COLOR = (60, 70, 100)
RESIST_COLOR = (100, 180, 255)
WEAK_COLOR = (255, 120, 80)
NEUTRAL_COLOR = (140, 140, 140)


# ── active_buffs 키 → 한글 이름 매핑 (전체) ──────────────────────────────
_BUFF_TYPE_NAMES: Dict[str, str] = {
    # 공격 계열
    "attack_up": "공격력 증가",
    "magic_up": "마법력 증가",
    "critical_up": "치명타율 증가",
    "crit_up": "치명타율 증가",
    "crit_damage_up": "치명타 피해 증가",
    "accuracy_up": "명중률 증가",
    "bonus_hp_damage": "추가 HP 피해",
    "lifesteal": "생명력 흡수",
    # 방어 계열
    "defense_up": "방어력 증가",
    "magic_defense_up": "마법방어 증가",
    "spirit_up": "정신력 증가",
    "evasion_up": "회피율 증가",
    "damage_reduction": "피해 경감",
    "barrier": "방어막",
    "mana_shield": "마나 실드",
    "dimension_barrier": "차원 장벽",
    "status_resistance": "상태이상 저항",
    "invincible": "무적",
    # 속도/유틸
    "speed_up": "속도 증가",
    "luck": "행운 증가",
    "counter": "반격",
    "protect_target": "보호 대상",
    # 회복 계열
    "regen": "HP 재생",
    "hp_regen": "HP 재생",
    "mp_regen": "MP 재생",
    # 특수 버프
    "desperate_strength": "필사적 힘",
    "berserk": "버서크",
    # 디버프
    "attack_down": "공격력 감소",
    "defense_down": "방어력 감소",
    "magic_down": "마법력 감소",
    "magic_defense_down": "마법방어 감소",
    "spirit_down": "정신력 감소",
    "speed_down": "속도 감소",
    "critical_down": "치명타 감소",
    "accuracy_down": "명중률 감소",
    "evasion_down": "회피율 감소",
    "skill_seal": "스킬 봉인",
    "damage_taken_increase": "받는 피해 증가",
}

# 디버프로 분류되는 active_buffs 키
_ACTIVE_BUFF_DEBUFFS = {
    "attack_down", "defense_down", "magic_down", "magic_defense_down",
    "spirit_down", "speed_down", "critical_down", "accuracy_down",
    "evasion_down", "skill_seal", "damage_taken_increase",
}

# StatusType 값 → 한글 이름 매핑
_STATUS_TYPE_NAMES: Dict[str, str] = {
    # 디버프
    "poison": "독", "burn": "화상", "freeze": "빙결", "stun": "기절",
    "sleep": "수면", "silence": "침묵", "blind": "실명", "slow": "둔화",
    "shock": "감전", "curse": "저주", "weaken": "약화", "weakness": "취약",
    "defense_down": "방어력 감소", "attack_down": "공격력 감소",
    "provoke": "도발", "hp_recovery_block": "회복 불가",
    "curse_mark": "저주 낙인", "doom": "죽음의 선고",
    "scatter": "자세 무너짐", "paralyze": "마비",
    "bleed": "출혈", "confuse": "혼란", "fear": "공포",
    "petrify": "석화", "entangle": "속박", "root": "속박",
    "burning": "작열", "frozen_solid": "완전빙결",
    "electrocuted": "감전", "slowed": "둔화",
    "defense_shatter": "방어 파쇄", "wound": "부상",
    # 버프
    "haste": "가속", "regen": "재생", "barrier": "방어막",
    "blessing": "축복", "strengthen": "강화",
    "defense_up": "방어력 증가", "attack_up": "공격력 증가",
    "stealth": "은신", "guardian": "수호",
    "shield": "실드", "buff": "강화",
    # 특수 마크
    "rune": "룬 각인", "mark": "표식",
    # 속성 브랜드
    "fire_brand": "화염 각인", "ice_brand": "빙결 각인",
    "lightning_brand": "번개 각인", "elemental_aegis": "원소 방벽",
}

# 디버프로 분류되는 StatusType 값
_STATUS_DEBUFF_TYPES = {
    "poison", "burn", "freeze", "stun", "sleep", "silence", "blind", "slow",
    "shock", "curse", "weaken", "weakness", "defense_down", "attack_down",
    "provoke", "hp_recovery_block", "curse_mark", "doom", "scatter",
    "paralyze", "bleed", "confuse", "fear", "petrify", "entangle", "root",
    "burning", "frozen_solid", "electrocuted", "slowed",
    "defense_shatter", "wound",
}


def _get_status_icon(category: str) -> str:
    """버프/디버프 아이콘"""
    return "+" if category == "buff" else "-"


def _classify_status(status_type) -> str:
    """상태 효과가 버프인지 디버프인지 분류"""
    name = ""
    try:
        name = status_type.value if hasattr(status_type, 'value') else str(status_type)
    except Exception:
        name = str(status_type)
    name = name.lower()

    if name in _STATUS_DEBUFF_TYPES:
        return "debuff"

    # 키워드 기반 폴백
    debuff_keywords = [
        "독", "화상", "출혈", "기절", "수면", "침묵", "실명", "빙결",
        "둔화", "마비", "속박", "저주", "공포", "작열", "혼란",
        "감소", "약화", "취약", "노출", "절망", "괴사", "부식", "질병",
        "감전", "냉기", "석화", "광기", "매혹",
        "poison", "burn", "bleed", "stun", "sleep", "silence",
        "blind", "freeze", "slow", "paralyze", "root", "entangle",
    ]
    for kw in debuff_keywords:
        if kw in name:
            return "debuff"

    buff_keywords = [
        "재생", "가속", "보호", "축복", "무적", "반사", "방패", "실드",
        "배리어", "강화", "증가", "집중", "영감", "수호", "예지",
        "regen", "haste", "shield", "blessing",
        "invincible", "reflect", "barrier",
    ]
    for kw in buff_keywords:
        if kw in name:
            return "buff"

    return "buff"


def _format_active_buff_line(buff_key: str, buff_data: Any) -> Tuple[str, str]:
    """active_buffs 딕셔너리 항목을 한 줄 텍스트로 포맷팅"""
    name = _BUFF_TYPE_NAMES.get(buff_key, buff_key.replace("_", " ").title())
    category = "debuff" if buff_key in _ACTIVE_BUFF_DEBUFFS else "buff"
    icon = _get_status_icon(category)

    duration = 0
    value_str = ""
    if isinstance(buff_data, dict):
        duration = buff_data.get("duration", 0)
        value = buff_data.get("value", 0)
        if value and value != 0:
            pct = int(abs(value) * 100)
            if pct > 0 and pct != 100:
                value_str = f" {pct}%"
    elif isinstance(buff_data, (int, float)):
        duration = int(buff_data)

    line = f" {icon}{name}{value_str} ({duration}턴)"
    if len(line) > TOOLTIP_WIDTH - 2:
        line = line[: TOOLTIP_WIDTH - 3] + "…"
    return line, category


def _format_status_line(effect: Any) -> Tuple[str, str]:
    """상태 효과를 한 줄 텍스트로 포맷팅"""
    raw_name = getattr(effect, "name", str(effect))
    duration = getattr(effect, "duration", 0)
    stack_count = getattr(effect, "stack_count", 1)
    intensity = getattr(effect, "intensity", 1.0)
    status_type = getattr(effect, "status_type", None)

    # StatusType 값으로 한글 이름 찾기
    st_val = ""
    try:
        st_val = status_type.value if hasattr(status_type, 'value') else str(status_type)
    except Exception:
        st_val = str(status_type) if status_type else ""
    name = _STATUS_TYPE_NAMES.get(st_val.lower(), raw_name)

    category = _classify_status(status_type)
    icon = _get_status_icon(category)

    stack_str = f" x{stack_count}" if stack_count > 1 else ""
    intensity_str = ""
    if intensity != 1.0 and intensity > 0:
        pct = int(intensity * 100)
        if pct != 100:
            intensity_str = f" {pct}%"

    line = f" {icon}{name}{intensity_str} ({duration}턴){stack_str}"
    if len(line) > TOOLTIP_WIDTH - 2:
        line = line[: TOOLTIP_WIDTH - 3] + "…"
    return line, category


def _truncate(text: str, max_len: int = TOOLTIP_WIDTH - 2) -> str:
    """텍스트를 최대 길이로 자르기"""
    if len(text) > max_len:
        return text[:max_len - 1] + "…"
    return text


def _add_separator(lines: List[Tuple[str, Tuple[int, int, int]]]) -> None:
    """구분선 추가"""
    sep = " " + "─" * (TOOLTIP_WIDTH - 4)
    lines.append((sep, SEPARATOR_COLOR))


def render_tooltip(
    console: tcod.console.Console,
    character: Any,
    screen_x: int,
    screen_y: int,
    screen_width: int,
    screen_height: int,
    combat_manager: Any = None,
) -> None:
    """
    캐릭터 상세 툴팁을 콘솔에 렌더링합니다.
    """
    if character is None:
        return

    content_lines: List[Tuple[str, Tuple[int, int, int]]] = []

    # ── 1. 헤더: 이름/직업/레벨 ──────────────────────────────────────────
    name = getattr(character, "name", "???")
    job = getattr(character, "job_name", getattr(character, "character_class", ""))
    level = getattr(character, "level", 1)
    is_enemy = getattr(character, "is_enemy", False)

    title = f" {name} Lv.{level}"
    if job:
        title = f" {name} Lv.{level} [{job}]"
    content_lines.append((_truncate(title), HEADER_COLOR))

    # ── 2. HP/MP/BRV/ATB 바 ──────────────────────────────────────────────
    _add_separator(content_lines)

    current_hp = getattr(character, "current_hp", 0)
    max_hp = getattr(character, "max_hp", 1)
    current_mp = getattr(character, "current_mp", 0)
    max_mp = getattr(character, "max_mp", 1)
    current_brv = getattr(character, "current_brv", 0)
    max_brv = getattr(character, "max_brv", 999)

    hp_ratio = current_hp / max_hp if max_hp > 0 else 0
    hp_color = HP_LOW_COLOR if hp_ratio < 0.3 else HP_COLOR

    content_lines.append((_truncate(f" HP {current_hp:>5}/{max_hp}"), hp_color))
    content_lines.append((_truncate(f" MP {current_mp:>5}/{max_mp}"), MP_COLOR))
    content_lines.append((_truncate(f" BRV {current_brv:>4}/{max_brv}"), BRV_COLOR))

    # ATB 정보
    atb_pct = 0
    if combat_manager and hasattr(combat_manager, "atb"):
        gauge = combat_manager.atb.get_gauge(character)
        if gauge:
            atb_pct = int(gauge.current / 10) if gauge.current else 0
    content_lines.append((_truncate(f" ATB {atb_pct:>3}%"), ATB_COLOR))

    # ── 3. 기본 스탯 ─────────────────────────────────────────────────────
    _add_separator(content_lines)
    content_lines.append((" [스탯]", SUBHEADER_COLOR))

    atk = getattr(character, "attack", getattr(character, "physical_attack", getattr(character, "strength", 0)))
    dfn = getattr(character, "defense", getattr(character, "physical_defense", 0))
    mag = getattr(character, "magic", getattr(character, "magic_attack", 0))
    mdf = getattr(character, "magic_defense", getattr(character, "spirit", 0))
    spd = getattr(character, "speed", 0)

    content_lines.append((_truncate(f" ATK {atk:>4}  DEF {dfn:>4}"), STAT_COLOR))
    content_lines.append((_truncate(f" MAG {mag:>4}  MDF {mdf:>4}"), STAT_COLOR))
    content_lines.append((_truncate(f" SPD {spd:>4}"), STAT_COLOR))

    # ── 4. 장비 특수 효과 (아군만) ────────────────────────────────────────
    if not is_enemy and hasattr(character, "equipment"):
        equip_effects = _collect_equipment_effects(character)
        if equip_effects:
            _add_separator(content_lines)
            content_lines.append((" [장비 효과]", EQUIP_COLOR))
            for eff_line in equip_effects[:6]:
                content_lines.append((_truncate(f" {eff_line}"), EQUIP_COLOR))

    # ── 5. 속성 내성/약점 (적) ────────────────────────────────────────────
    if is_enemy:
        resist_lines = _collect_resistances(character)
        if resist_lines:
            _add_separator(content_lines)
            content_lines.append((" [속성]", SUBHEADER_COLOR))
            for rline, rcolor in resist_lines:
                content_lines.append((_truncate(f" {rline}"), rcolor))

    # ── 5-1. 사무라이 예측 정보 (적 호버 시) ──────────────────────────────
    if is_enemy and combat_manager:
        prediction = _get_prediction_for_enemy(character, combat_manager)
        if prediction:
            _add_separator(content_lines)
            pred_color = (200, 255, 200)
            pred_header_color = (255, 255, 120)
            content_lines.append((" [요미: 행동 예측]", pred_header_color))
            act = prediction.get("action", "알 수 없음")
            atb_pct = prediction.get("atb_percentage", 0)
            turns_left = prediction.get("turns_remaining", 0)
            content_lines.append((_truncate(f" 예측 행동: {act}"), pred_color))
            content_lines.append((_truncate(f" ATB: {atb_pct}%"), pred_color))
            if turns_left > 0:
                content_lines.append((_truncate(f" 남은 예측: {turns_left}턴"), pred_color))

    # ── 6. 버프/디버프 ───────────────────────────────────────────────────
    buffs: List[Tuple[str, str]] = []
    debuffs: List[Tuple[str, str]] = []

    # StatusManager 상태 효과
    status_effects = []
    if hasattr(character, "status_manager"):
        sm = character.status_manager
        status_effects = getattr(sm, "status_effects", [])
        if isinstance(status_effects, dict):
            # dict 형태인 경우 값들을 리스트로
            status_effects = list(status_effects.values()) if status_effects else []
    elif hasattr(character, "status_effects"):
        se = character.status_effects
        if isinstance(se, dict):
            status_effects = list(se.values()) if se else []
        else:
            status_effects = se if se else []

    for eff in status_effects:
        if eff is None:
            continue
        try:
            line, category = _format_status_line(eff)
            if category == "buff":
                buffs.append((line, category))
            else:
                debuffs.append((line, category))
        except Exception:
            pass

    # active_buffs 딕셔너리
    active_buffs = getattr(character, "active_buffs", None)
    if active_buffs and isinstance(active_buffs, dict):
        for buff_key, buff_data in active_buffs.items():
            try:
                line, category = _format_active_buff_line(buff_key, buff_data)
                if category == "buff":
                    buffs.append((line, category))
                else:
                    debuffs.append((line, category))
            except Exception:
                pass

    if buffs or debuffs:
        _add_separator(content_lines)

    if buffs:
        content_lines.append((" [버프]", BUFF_COLOR))
        for line, _ in buffs[:8]:
            content_lines.append((line, BUFF_COLOR))

    if debuffs:
        if buffs:
            content_lines.append(("", (0, 0, 0)))  # 빈줄
        content_lines.append((" [디버프]", DEBUFF_COLOR))
        for line, _ in debuffs[:8]:
            content_lines.append((line, DEBUFF_COLOR))

    # ── 7. 기믹 게이지 ───────────────────────────────────────────────────
    gimmick_type = getattr(character, "gimmick_type", None)
    if gimmick_type:
        gimmick_lines = _collect_gimmick_info(character, gimmick_type)
        if gimmick_lines:
            _add_separator(content_lines)
            content_lines.append((" [기믹]", GIMMICK_COLOR))
            for gl in gimmick_lines:
                content_lines.append((_truncate(f" {gl}"), GIMMICK_COLOR))

    # ── 렌더링 ───────────────────────────────────────────────────────────
    tooltip_height = len(content_lines) + 2  # 테두리 상하

    try:
        console_w = getattr(console, 'width', screen_width)
        console_h = getattr(console, 'height', screen_height)
    except Exception:
        console_w = screen_width
        console_h = screen_height
    sw = min(screen_width, console_w)
    sh = min(screen_height, console_h)

    # 최대 높이 제한
    max_tooltip_h = sh - 2
    if tooltip_height > max_tooltip_h:
        tooltip_height = max_tooltip_h
        content_lines = content_lines[:max_tooltip_h - 2]

    # 위치 보정
    tx = screen_x + 2
    ty = screen_y - tooltip_height // 2

    if tx + TOOLTIP_WIDTH >= sw:
        tx = screen_x - TOOLTIP_WIDTH - 1
    if tx < 0:
        tx = 0
    if ty < 0:
        ty = 0
    if ty + tooltip_height >= sh:
        ty = sh - tooltip_height - 1
    if ty < 0:
        ty = 0

    # 배경
    for dy in range(tooltip_height):
        for dx in range(TOOLTIP_WIDTH):
            cx, cy = tx + dx, ty + dy
            if 0 <= cx < sw and 0 <= cy < sh:
                console.rgb["ch"][cy, cx] = ord(" ")
                console.rgb["bg"][cy, cx] = BG_COLOR

    # 테두리
    _draw_border(console, tx, ty, TOOLTIP_WIDTH, tooltip_height, sw, sh)

    # 내용
    for i, (text, color) in enumerate(content_lines):
        cy = ty + 1 + i
        if 0 <= cy < sh and text:
            max_text_len = max(0, sw - tx - 2)
            if max_text_len > 0:
                console.print(tx + 1, cy, text[:max_text_len], fg=color, bg=BG_COLOR)


def _draw_border(
    console: tcod.console.Console,
    x: int, y: int,
    width: int, height: int,
    sw: int, sh: int,
) -> None:
    """이중선 박스 테두리 그리기"""
    # 상단
    if 0 <= y < sh:
        for dx in range(width):
            cx = x + dx
            if 0 <= cx < sw:
                if dx == 0:
                    ch = ord("╔")
                elif dx == width - 1:
                    ch = ord("╗")
                else:
                    ch = ord("═")
                console.rgb["ch"][y, cx] = ch
                console.rgb["fg"][y, cx] = BORDER_COLOR
                console.rgb["bg"][y, cx] = BG_COLOR

    # 하단
    by = y + height - 1
    if 0 <= by < sh:
        for dx in range(width):
            cx = x + dx
            if 0 <= cx < sw:
                if dx == 0:
                    ch = ord("╚")
                elif dx == width - 1:
                    ch = ord("╝")
                else:
                    ch = ord("═")
                console.rgb["ch"][by, cx] = ch
                console.rgb["fg"][by, cx] = BORDER_COLOR
                console.rgb["bg"][by, cx] = BG_COLOR

    # 좌우
    for dy in range(1, height - 1):
        cy = y + dy
        if 0 <= cy < sh:
            if 0 <= x < sw:
                console.rgb["ch"][cy, x] = ord("║")
                console.rgb["fg"][cy, x] = BORDER_COLOR
                console.rgb["bg"][cy, x] = BG_COLOR
            rx = x + width - 1
            if 0 <= rx < sw:
                console.rgb["ch"][cy, rx] = ord("║")
                console.rgb["fg"][cy, rx] = BORDER_COLOR
                console.rgb["bg"][cy, rx] = BG_COLOR


def _collect_equipment_effects(character: Any) -> List[str]:
    """장착된 장비의 특수 효과를 수집"""
    effects = []
    equipment = getattr(character, "equipment", {})
    if not equipment:
        return effects

    # 장비 효과 한글 매핑
    effect_names = {
        "lifesteal": "생명력 흡수",
        "thorns": "가시",
        "hp_regen": "HP 재생",
        "mp_regen": "MP 재생",
        "critical_chance": "치명타율",
        "critical_rate": "치명타율",
        "dodge_chance": "회피율",
        "block_chance": "블록율",
        "vision_bonus": "시야 증가",
        "multi_strike": "다중 타격",
        "counter_attack": "반격",
        "first_strike": "선제 공격",
        "phoenix": "불사조",
        "execute": "처형",
        "berserk": "광전사",
        "glass_cannon": "유리대포",
        "tank": "중장갑",
        "heal_boost": "치유 강화",
        "overheal": "과치유",
        "exp_bonus": "경험치 보너스",
        "gold_bonus": "골드 보너스",
        "status_immunity": "상태이상 면역",
        "poison_immunity": "독 면역",
        "stun_immunity": "기절 면역",
        "wound_reduction": "부상 경감",
        "wound_immunity": "부상 면역",
        "brv_bonus": "BRV 보너스",
        "elemental": "속성 부여",
        "on_kill_heal": "처치 시 회복",
    }

    for slot, item in equipment.items():
        if item is None:
            continue
        unique_effect = getattr(item, "unique_effect", None)
        if not unique_effect:
            continue

        # unique_effect 문자열 파싱 (간단히)
        parts = unique_effect.split("|")
        for part in parts:
            if ":" not in part:
                continue
            key, val_str = part.split(":", 1)
            key = key.strip()
            display_name = effect_names.get(key, key)
            try:
                val = float(val_str.strip())
                if val >= 1.0 and key not in ("vision_bonus", "multi_strike"):
                    # 정수값 (시야, 다중타격 등)
                    effects.append(f"{display_name} +{int(val)}")
                elif key in ("vision_bonus", "multi_strike"):
                    effects.append(f"{display_name} +{int(val)}")
                else:
                    effects.append(f"{display_name} +{int(val * 100)}%")
            except ValueError:
                effects.append(f"{display_name}")

    return effects


def _collect_resistances(character: Any) -> List[Tuple[str, Tuple[int, int, int]]]:
    """적의 속성 내성/약점 정보 수집"""
    lines = []

    # 속성 내성 확인
    resistances = getattr(character, "resistances", None)
    weaknesses = getattr(character, "weaknesses", None)
    element_resist = getattr(character, "element_resist", None)

    element_names = {
        "fire": "화", "ice": "빙", "lightning": "뇌", "thunder": "뇌",
        "water": "수", "earth": "지", "wind": "풍", "light": "광",
        "dark": "암", "holy": "성", "physical": "물리", "magic": "마법",
    }

    if weaknesses:
        weak_list = []
        if isinstance(weaknesses, (list, set)):
            for w in weaknesses:
                w_str = str(w).lower()
                weak_list.append(element_names.get(w_str, w_str))
        if weak_list:
            lines.append(("약점: " + " ".join(weak_list), WEAK_COLOR))

    if resistances:
        resist_list = []
        if isinstance(resistances, (list, set)):
            for r in resistances:
                r_str = str(r).lower()
                resist_list.append(element_names.get(r_str, r_str))
        if resist_list:
            lines.append(("내성: " + " ".join(resist_list), RESIST_COLOR))

    if element_resist and isinstance(element_resist, dict):
        weak_elems = []
        resist_elems = []
        for elem, mult in element_resist.items():
            ename = element_names.get(elem.lower(), elem)
            if mult > 1.0:
                weak_elems.append(f"{ename}x{mult:.1f}")
            elif mult < 1.0:
                resist_elems.append(f"{ename}x{mult:.1f}")
        if weak_elems:
            lines.append(("약점: " + " ".join(weak_elems), WEAK_COLOR))
        if resist_elems:
            lines.append(("내성: " + " ".join(resist_elems), RESIST_COLOR))

    return lines


def _get_prediction_for_enemy(enemy: Any, combat_manager: Any) -> Optional[Dict]:
    """사무라이의 요미 예측 데이터에서 해당 적의 예측 정보를 찾는다."""
    enemy_name = getattr(enemy, "name", "")
    if not enemy_name:
        return None

    allies = getattr(combat_manager, "allies", [])
    for ally in allies:
        if not getattr(ally, "prediction_active", False):
            continue
        turns_left = getattr(ally, "prediction_turns_left", 0)
        if turns_left <= 0:
            continue
        predicted = getattr(ally, "predicted_actions", {})
        if enemy_name in predicted:
            return predicted[enemy_name]
    return None


def _collect_gimmick_info(character: Any, gimmick_type: str) -> List[str]:
    """캐릭터의 기믹 정보를 한 줄씩 수집"""
    lines: List[str] = []

    if gimmick_type == "mp_overload_system":
        state = getattr(character, "last_mp_state", "stable")
        gauge = getattr(character, "overload_gauge", 0)
        max_gauge = getattr(character, "max_overload_gauge", 5)
        state_kor = {"stable": "안정", "danger": "위험", "depleted": "고갈"}.get(state, state)
        lines.append(f"과부하: {state_kor} {gauge}/{max_gauge}")

    elif gimmick_type == "intrusion_system":
        ram = getattr(character, "ram", 0)
        max_ram = getattr(character, "max_ram", 0)
        lines.append(f"RAM: {ram}GB/{max_ram}GB")

    elif gimmick_type == "oath_system":
        current_oath = getattr(character, "current_oath", None)
        faith = getattr(character, "faith", 0)
        if current_oath:
            oath_name = getattr(character, "oaths", {}).get(current_oath, {}).get("name", current_oath)
            lines.append(f"서약: {oath_name}")
        lines.append(f"신앙: {faith}")

    elif gimmick_type in ("heat_gauge", "heat_management"):
        heat = getattr(character, "heat", 0)
        max_heat = getattr(character, "max_heat", 100)
        lines.append(f"열: {heat}/{max_heat}")

    elif gimmick_type == "rage_system":
        rage = getattr(character, "rage", 0)
        max_rage = getattr(character, "max_rage", 100)
        lines.append(f"분노: {rage}/{max_rage}")

    elif gimmick_type == "combo_system":
        combo = getattr(character, "combo_count", 0)
        lines.append(f"콤보: {combo}")

    elif gimmick_type == "elemental_counter":
        fire = getattr(character, "fire_element", 0)
        ice = getattr(character, "ice_element", 0)
        lightning = getattr(character, "lightning_element", 0)
        lines.append(f"화:{fire} 빙:{ice} 뇌:{lightning}")

    elif gimmick_type == "elemental_spirits":
        spirits = getattr(character, "active_spirits", [])
        if spirits:
            lines.append(f"정령: {', '.join(spirits)}")

    elif gimmick_type == "song_system":
        current_song = getattr(character, "current_song", None)
        if current_song:
            lines.append(f"노래: {current_song}")

    elif gimmick_type == "card_system":
        hand_size = len(getattr(character, "card_hand", []))
        lines.append(f"패: {hand_size}장")

    elif gimmick_type == "venom_system":
        pass  # 독 중첩 표시 제거

    elif gimmick_type == "mirror_system":
        mirrors = getattr(character, "mirror_count", 0)
        max_mirrors = getattr(character, "max_mirrors", 3)
        lines.append(f"거울: {mirrors}/{max_mirrors}")

    elif gimmick_type == "wound_system":
        wound = getattr(character, "wound_gauge", 0)
        max_wound = getattr(character, "max_wound", 100)
        lines.append(f"부상: {wound}/{max_wound}")

    elif gimmick_type == "spectacle_gauge":
        gauge = getattr(character, "spectacle_gauge", 0)
        max_g = getattr(character, "max_spectacle", 100)
        lines.append(f"흥행: {gauge}/{max_g}")

    elif gimmick_type == "totem_system":
        active = getattr(character, "active_totem", None)
        if active:
            lines.append(f"토템: {active}")

    elif gimmick_type == "dimension_system":
        dim = getattr(character, "current_dimension", "현실")
        lines.append(f"차원: {dim}")

    elif gimmick_type == "blood_system":
        blood = getattr(character, "blood_gauge", 0)
        max_blood = getattr(character, "max_blood", 100)
        lines.append(f"혈기: {blood}/{max_blood}")

    elif gimmick_type == "stance_system":
        stance = getattr(character, "current_stance", None)
        if stance:
            lines.append(f"자세: {stance}")

    elif gimmick_type == "possibility_system":
        possibilities = getattr(character, "active_possibilities", [])
        count = len(possibilities) if possibilities else 0
        lines.append(f"가능성: {count}개")

    return lines
