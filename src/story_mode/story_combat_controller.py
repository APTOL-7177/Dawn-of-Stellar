"""
스토리 모드 전투 컨트롤러
Dawn of Stellar - 별빛의 여명

스크립트 전투: 약한 적, 강제 행동 유도, 인라인 힌트
기존 CombatManager를 래핑하여 튜토리얼 난이도로 제공
"""

import time
from typing import List, Dict, Any, Optional

import tcod.console
import tcod.event

from src.core.logger import get_logger
from src.audio import play_bgm, play_sfx
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, unified_input_handler
from src.story_mode.inline_tutorial_overlay import (
    InlineTutorialOverlay,
    NPC_NAMES,
    NPC_COLORS,
)

logger = get_logger("story_mode")


class StoryCombatController:
    """
    스토리 모드 전용 전투 컨트롤러

    - 약한 적 생성
    - forced_actions로 특정 행동만 허용
    - 조건부 힌트 트리거
    - 자동 부활 (절대 게임오버 불가)
    """

    def __init__(
        self,
        console: tcod.console.Console,
        context: tcod.context.Context,
        overlay: InlineTutorialOverlay,
    ):
        self.console = console
        self.context = context
        self.overlay = overlay

    def run_scripted_combat(
        self,
        chapter_id: str,
        enemies_data: List[Dict[str, Any]],
        combat_hints: List[Dict[str, Any]] = None,
    ) -> str:
        """
        스크립트 전투 실행

        간소화된 전투 루프:
        턴 기반으로 플레이어가 적을 공격, 힌트와 함께 진행

        Returns:
            "victory", "quit"
        """
        if not enemies_data:
            enemies_data = [{"name": "시간 파편", "hp": 30, "brv": 40, "speed": 20}]
        if combat_hints is None:
            combat_hints = []

        # 막(Act) 기반 적 스탯 스케일링 (실제 게임과 유사한 난이도)
        # 전사 Lv1 기준: ATK=68, DEF=68 → 적 ATK가 최소 40~70이어야 의미있는 BRV 데미지
        act_scaling = {
            "act1": {"atk_base": 40, "def_base": 20, "hp_mult": 1.0, "brv_mult": 1.0},
            "act2": {"atk_base": 50, "def_base": 28, "hp_mult": 1.3, "brv_mult": 1.2},
            "act3": {"atk_base": 55, "def_base": 32, "hp_mult": 1.5, "brv_mult": 1.4},
            "act4": {"atk_base": 60, "def_base": 38, "hp_mult": 1.8, "brv_mult": 1.6},
            "act5": {"atk_base": 68, "def_base": 45, "hp_mult": 2.2, "brv_mult": 2.0},
        }
        act = "act1"
        for a in ["act5", "act4", "act3", "act2", "act1"]:
            if chapter_id.startswith(a):
                act = a
                break
        scaling = act_scaling.get(act, act_scaling["act1"])
        is_boss = "boss" in chapter_id or "finale" in chapter_id

        # 적 데이터 준비 (스케일링 적용)
        enemies = []
        for ed in enemies_data:
            raw_atk = ed.get("attack", 35)
            raw_def = ed.get("defense", 30)
            raw_hp = ed.get("hp", 100)
            raw_brv = ed.get("brv", 80)

            # 스케일링: YAML 값은 상대적 강도, 실제 수치는 Act에 맞게 조정
            scaled_atk = max(raw_atk, scaling["atk_base"]) + (10 if is_boss else 0)
            scaled_def = max(raw_def, scaling["def_base"])
            scaled_hp = int(raw_hp * scaling["hp_mult"]) + (100 if is_boss else 0)
            scaled_brv = int(raw_brv * scaling["brv_mult"])

            enemies.append({
                "name": ed.get("name", "시간 파편"),
                "hp": scaled_hp,
                "max_hp": scaled_hp,
                "brv": scaled_brv,
                "max_brv": scaled_brv * 2,
                "init_brv": scaled_brv,
                "attack": scaled_atk,
                "defense": scaled_def,
                "speed": ed.get("speed", 50),
                "element": ed.get("element", "none"),
            })

        # 플레이어 데이터 (전사 직업 1레벨 기본 스탯 - warrior.yaml 기준)
        player = {
            "name": "전사",
            "hp": 210,
            "max_hp": 210,
            "mp": 32,
            "max_mp": 32,
            "brv": 135,
            "max_brv": 343,
            "init_brv": 135,
            "attack": 68,
            "defense": 68,
            "speed": 68,
            "is_player": True,
        }

        # 챕터별 파티원 합류 (NPC - AI 자동 행동)
        party = [player]
        party.extend(self._create_party_members(chapter_id))

        # 전투 BGM
        play_bgm("battle_normal")

        turn = 0

        while True:
            # 적이 모두 쓰러졌는지 확인
            alive_enemies = [e for e in enemies if e["hp"] > 0]
            if not alive_enemies:
                play_sfx("combat", "victory")
                self._show_victory_screen()
                return "victory"

            # 파티 전멸 체크 → 자동 부활
            alive_party = [m for m in party if m["hp"] > 0]
            if not alive_party:
                for m in party:
                    m["hp"] = m["max_hp"] // 2
                    m["brv"] = m["init_brv"]
                self._show_combat_message("파티가 쓰러졌지만 의지의 힘으로 부활!")
                alive_party = party

            turn += 1
            current_enemy = alive_enemies[0]

            # 현재 턴에 적용할 힌트/강제행동 확인
            current_hint = None
            forced_action = None
            for hint in combat_hints:
                trigger = hint.get("trigger", "")
                if trigger == "first_turn" and turn == 1:
                    current_hint = hint
                    forced_action = hint.get("forced_action")
                    break
                elif trigger == "after_brv_attack" and turn == 2:
                    current_hint = hint
                    forced_action = hint.get("forced_action")
                    break
                elif trigger == "enemy_brv_zero" and current_enemy["brv"] <= 0:
                    current_hint = hint
                    break
                elif trigger == f"turn_{turn}":
                    current_hint = hint
                    forced_action = hint.get("forced_action")
                    break

            # 전투 화면 렌더링 (플레이어만 조작)
            action = self._render_combat_and_get_action(
                player, alive_enemies, current_hint, forced_action, turn,
                party=party
            )

            if action == "quit":
                return "quit"

            # ── 행동 처리 ──
            # 데미지 공식: 실제 게임(damage_calculator.py)과 동일
            #   BRV 데미지 = (ATK / (DEF + 1)) * brv_multiplier(1.5) * level_mult(1.3) * 분산
            #   HP 데미지  = 현재BRV * hp_multiplier(0.15)
            import random as _rng
            BRV_MULT = 75.0   # config.yaml: combat.damage.brv_multiplier
            HP_MULT = 0.1     # config.yaml: combat.damage.hp_multiplier
            LV_MULT = 1.3     # 레벨 1 기준: 1.0 + 1*0.3
            CRIT_CHANCE = 0.1
            CRIT_MULT = 1.5
            defending = False

            def _calc_brv_damage(atk, dfs, skill_mult=1.0):
                """실제 게임과 동일한 BRV 데미지 공식"""
                stat_mod = atk / (dfs + 1.0)
                base = max(1, int(stat_mod * skill_mult * BRV_MULT))
                base = int(base * LV_MULT)
                variance = _rng.uniform(0.9, 1.1)
                dmg = base * variance
                is_crit = _rng.random() < CRIT_CHANCE
                if is_crit:
                    dmg *= CRIT_MULT
                return max(1, int(dmg)), is_crit

            if action == "brv_attack":
                damage, is_crit = _calc_brv_damage(player["attack"], current_enemy["defense"])
                current_enemy["brv"] = max(0, current_enemy["brv"] - damage)
                player["brv"] = min(player["max_brv"], player["brv"] + damage)
                play_sfx("combat", "attack_physical")
                crit_text = " ★크리티컬!" if is_crit else ""
                self._show_combat_message(
                    f"BRV 공격!{crit_text} 적 BRV -{damage} → {current_enemy['brv']}"
                    f"  |  내 BRV +{damage} → {player['brv']}"
                )
                if current_enemy["brv"] <= 0:
                    self._show_combat_message(
                        "★ BREAK! ★ 적의 BRV가 0! 보너스 BRV 획득!"
                    )
                    player["brv"] = min(
                        player["max_brv"],
                        player["brv"] + current_enemy["init_brv"],
                    )

            elif action == "hp_attack":
                hp_damage = max(1, int(player["brv"] * HP_MULT))
                current_enemy["hp"] = max(0, current_enemy["hp"] - hp_damage)
                player["brv"] = player["init_brv"]
                play_sfx("combat", "damage_high")
                self._show_combat_message(
                    f"HP 공격! BRV {player['init_brv']}→리셋 | "
                    f"적에게 {hp_damage} HP 데미지! ({current_enemy['hp']}/{current_enemy['max_hp']})"
                )

            elif action == "skill":
                if player["mp"] >= 10:
                    player["mp"] -= 10
                    # 스킬: 1.8배 BRV 데미지 후 즉시 HP 공격
                    brv_dmg, is_crit = _calc_brv_damage(player["attack"], current_enemy["defense"], 1.8)
                    player["brv"] = min(player["max_brv"], player["brv"] + brv_dmg)
                    hp_damage = max(1, int(player["brv"] * HP_MULT))
                    current_enemy["hp"] = max(0, current_enemy["hp"] - hp_damage)
                    player["brv"] = player["init_brv"]
                    play_sfx("skill", "fire")
                    crit_text = " ★크리티컬!" if is_crit else ""
                    self._show_combat_message(
                        f"스킬!{crit_text} BRV+{brv_dmg} → HP {hp_damage} 데미지! "
                        f"MP:{player['mp']}/{player['max_mp']}"
                    )
                else:
                    self._show_combat_message("MP가 부족합니다!")

            elif action == "defend":
                defending = True
                play_sfx("combat", "guard")
                self._show_combat_message("방어 자세! 이번 턴 받는 HP 데미지 절반!")

            elif action == "item":
                heal = int(player["max_hp"] * 0.3)
                player["hp"] = min(player["max_hp"], player["hp"] + heal)
                play_sfx("item", "potion")
                self._show_combat_message(f"포션! HP +{heal} → {player['hp']}/{player['max_hp']}")

            # ── 파티원 AI 턴 (플레이어 제외) ──
            alive_enemies = [e for e in enemies if e["hp"] > 0]
            for member in party:
                if member.get("is_player") or member["hp"] <= 0:
                    continue
                if not alive_enemies:
                    break
                target = alive_enemies[0]
                # AI: BRV가 max의 60% 미만이면 BRV 공격, 아니면 HP 공격
                if member["brv"] < member["max_brv"] * 0.6:
                    m_dmg, m_crit = _calc_brv_damage(member["attack"], target["defense"])
                    target["brv"] = max(0, target["brv"] - m_dmg)
                    member["brv"] = min(member["max_brv"], member["brv"] + m_dmg)
                    crit_t = " ★크리!" if m_crit else ""
                    self._show_combat_message(
                        f"{member['name']}의 BRV 공격!{crit_t} 적 BRV -{m_dmg}"
                    )
                    if target["brv"] <= 0:
                        member["brv"] = min(member["max_brv"], member["brv"] + target["init_brv"])
                        self._show_combat_message(f"★ {member['name']}이(가) BREAK 유발!")
                else:
                    m_hp_dmg = max(1, int(member["brv"] * HP_MULT))
                    target["hp"] = max(0, target["hp"] - m_hp_dmg)
                    member["brv"] = member["init_brv"]
                    self._show_combat_message(
                        f"{member['name']}의 HP 공격! {m_hp_dmg} 데미지! "
                        f"적 HP: {target['hp']}/{target['max_hp']}"
                    )
                alive_enemies = [e for e in enemies if e["hp"] > 0]

            # ── 적 턴 (각 적이 랜덤 파티원 공격) ──
            alive_enemies = [e for e in enemies if e["hp"] > 0]
            alive_party = [m for m in party if m["hp"] > 0]
            for enemy in alive_enemies:
                if not alive_party:
                    break
                # 랜덤 타겟 선택
                target = _rng.choice(alive_party)
                e_brv_dmg, e_crit = _calc_brv_damage(enemy["attack"], target["defense"])
                target["brv"] = max(0, target["brv"] - e_brv_dmg)

                enemy["_accum_brv"] = enemy.get("_accum_brv", 0) + e_brv_dmg
                if enemy["_accum_brv"] >= enemy["init_brv"]:
                    e_hp_dmg = max(1, int(enemy["_accum_brv"] * HP_MULT))
                    if defending and target.get("is_player"):
                        e_hp_dmg = max(1, e_hp_dmg // 2)
                    target["hp"] = max(1, target["hp"] - e_hp_dmg)
                    enemy["_accum_brv"] = 0
                    e_crit_text = " ★크리!" if e_crit else ""
                    self._show_combat_message(
                        f"{enemy['name']} → {target['name']} HP 공격!{e_crit_text} "
                        f"{e_hp_dmg} 데미지! ({target['hp']}/{target['max_hp']})"
                    )
                else:
                    self._show_combat_message(
                        f"{enemy['name']} → {target['name']} BRV 공격! -{e_brv_dmg}"
                    )
                alive_party = [m for m in party if m["hp"] > 0]

    def _create_party_members(self, chapter_id: str) -> list:
        """챕터별 파티원 생성 (실제 직업 YAML에서 스탯 로드)"""
        # 합류 시점: act2_ch3부터 1명, act3부터 2명, act5부터 3명
        party_config = []
        if chapter_id.startswith("act2") and chapter_id not in ("act2_ch1", "act2_ch2"):
            party_config = [("karnos", "knight")]  # 카르노스 = 기사
        elif chapter_id.startswith("act3"):
            party_config = [("karnos", "knight"), ("mira", "magician")]
        elif chapter_id.startswith("act4"):
            party_config = [("karnos", "knight"), ("mira", "magician")]
        elif chapter_id.startswith("act5"):
            party_config = [("karnos", "knight"), ("mira", "magician"), ("selena", "cleric")]

        members = []
        for npc_name, job_id in party_config:
            stats = self._load_job_stats(job_id)
            npc_display = {
                "karnos": "카르노스",
                "mira": "미라",
                "selena": "셀레나",
                "tord": "토르드",
                "lina": "리나",
            }.get(npc_name, npc_name)
            members.append({
                "name": npc_display,
                "hp": stats["hp"],
                "max_hp": stats["hp"],
                "mp": stats["mp"],
                "max_mp": stats["mp"],
                "brv": stats["init_brv"],
                "max_brv": stats["max_brv"],
                "init_brv": stats["init_brv"],
                "attack": stats["physical_attack"],
                "defense": stats["physical_defense"],
                "speed": stats["speed"],
                "is_player": False,
            })
        return members

    @staticmethod
    def _load_job_stats(job_id: str) -> dict:
        """직업 YAML에서 base_stats 로드"""
        import yaml
        from pathlib import Path
        path = Path(f"data/characters/{job_id}.yaml")
        default = {
            "hp": 200, "mp": 30, "init_brv": 120, "max_brv": 300,
            "physical_attack": 60, "physical_defense": 60, "speed": 60,
        }
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                base = data.get("base_stats", {})
                return {
                    "hp": base.get("hp", default["hp"]),
                    "mp": base.get("mp", default["mp"]),
                    "init_brv": base.get("init_brv", default["init_brv"]),
                    "max_brv": base.get("max_brv", default["max_brv"]),
                    "physical_attack": base.get("physical_attack", default["physical_attack"]),
                    "physical_defense": base.get("physical_defense", default["physical_defense"]),
                    "speed": base.get("speed", default["speed"]),
                }
        except Exception:
            pass
        return default

    def _render_combat_and_get_action(
        self,
        player: dict,
        enemies: list,
        hint: Optional[dict],
        forced_action: Optional[str],
        turn: int,
        party: list = None,
    ) -> str:
        """전투 화면 렌더링 + 행동 선택"""
        actions = ["brv_attack", "hp_attack", "skill", "item", "defend"]
        action_names = ["BRV 공격", "HP 공격", "스킬", "아이템", "방어"]
        cursor = 0

        # forced_action이면 해당 행동의 인덱스로 커서 고정
        if forced_action and forced_action in actions:
            cursor = actions.index(forced_action)

        # 입력 큐 비우기
        for _ in tcod.event.get():
            pass
        unified_input_handler.clear_input_state()

        while True:
            self.console.clear()
            w, h = self.console.width, self.console.height

            # 배경
            for y in range(h):
                for x in range(w):
                    self.console.rgb[y, x] = (ord(" "), (8, 8, 20), (8, 8, 20))

            # 전투 헤더
            self.console.print(2, 1, f"─── 전투 (턴 {turn}) ───", fg=(150, 150, 255))

            # 적 표시
            y_offset = 4
            for i, enemy in enumerate(enemies):
                hp_ratio = enemy["hp"] / enemy["max_hp"] if enemy["max_hp"] > 0 else 0
                hp_color = (
                    int(255 * (1 - hp_ratio)),
                    int(255 * hp_ratio),
                    0,
                )
                self.console.print(
                    4, y_offset + i * 3, f"[적] {enemy['name']}", fg=(255, 100, 100)
                )
                # HP 바
                bar_width = 30
                filled = int(bar_width * hp_ratio)
                hp_bar = "█" * filled + "░" * (bar_width - filled)
                self.console.print(
                    6, y_offset + i * 3 + 1,
                    f"HP [{hp_bar}] {enemy['hp']}/{enemy['max_hp']}",
                    fg=hp_color,
                )
                # BRV
                self.console.print(
                    6, y_offset + i * 3 + 2,
                    f"BRV: {enemy['brv']}/{enemy['max_brv']}",
                    fg=(0, 200, 255),
                )

            # 파티원 표시
            all_members = party if party else [player]
            py = y_offset + len(enemies) * 3 + 1
            for mi, member in enumerate(all_members):
                alive = member["hp"] > 0
                is_main = member.get("is_player", False)
                tag = "★" if is_main else "·"
                name_color = (100, 255, 100) if alive else (100, 100, 100)
                self.console.print(
                    4, py, f"[{tag}] {member['name']}", fg=name_color
                )
                hp_ratio = member["hp"] / member["max_hp"] if member["max_hp"] > 0 else 0
                bar_w = 20
                filled = int(bar_w * hp_ratio)
                hp_bar = "█" * filled + "░" * (bar_w - filled)
                hp_c = (int(255 * (1 - hp_ratio)), int(255 * hp_ratio), 0) if alive else (60, 60, 60)
                self.console.print(
                    6, py + 1,
                    f"HP[{hp_bar}]{member['hp']}/{member['max_hp']}  BRV:{member['brv']}",
                    fg=hp_c,
                )
                py += 2

            # 행동 메뉴
            menu_y = py + 2
            self.console.print(4, menu_y - 1, "행동 선택:", fg=(255, 215, 0))
            for i, name in enumerate(action_names):
                is_enabled = (forced_action is None) or (actions[i] == forced_action)
                if i == cursor:
                    prefix = "> "
                    fg = (255, 255, 200) if is_enabled else (100, 100, 60)
                else:
                    prefix = "  "
                    fg = Colors.UI_TEXT if is_enabled else (60, 60, 60)
                self.console.print(6, menu_y + i, f"{prefix}{name}", fg=fg)

            # 힌트 오버레이
            if hint:
                hint_text = hint.get("text", "")
                speaker = hint.get("speaker")
                self.overlay.show_hint(hint_text, speaker=speaker, position="bottom")
                self.overlay.render(self.console)

            # 조작 안내
            self.console.print(
                2, h - 2, "↑↓: 선택  Z: 확인  X: 돌아가기", fg=Colors.GRAY
            )

            self.context.present(self.console)

            # 입력 처리
            try:
                import pygame
                pygame.event.pump()
            except Exception:
                pass

            keyboard_processed = False
            for event in tcod.event.get():
                action = unified_input_handler.process_tcod_event(event)
                if action:
                    keyboard_processed = True

                if action == GameAction.MOVE_UP:
                    # forced_action이면 커서 이동 불가
                    if not forced_action:
                        cursor = max(0, cursor - 1)
                        play_sfx("ui", "cursor_move")
                elif action == GameAction.MOVE_DOWN:
                    if not forced_action:
                        cursor = min(len(actions) - 1, cursor + 1)
                        play_sfx("ui", "cursor_move")
                elif action == GameAction.CONFIRM:
                    selected = actions[cursor]
                    if forced_action and selected != forced_action:
                        play_sfx("ui", "cursor_error")
                    else:
                        play_sfx("ui", "cursor_select")
                        return selected
                elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                    return "quit"

                if isinstance(event, tcod.event.Quit):
                    return "quit"

            if not keyboard_processed:
                gamepad_action = unified_input_handler.get_action()
                if gamepad_action:
                    if gamepad_action == GameAction.MOVE_UP and not forced_action:
                        cursor = max(0, cursor - 1)
                    elif gamepad_action == GameAction.MOVE_DOWN and not forced_action:
                        cursor = min(len(actions) - 1, cursor + 1)
                    elif gamepad_action == GameAction.CONFIRM:
                        selected = actions[cursor]
                        if not forced_action or selected == forced_action:
                            return selected
                    elif gamepad_action == GameAction.CANCEL:
                        return "quit"

            time.sleep(0.016)

    def _show_combat_message(self, text: str):
        """전투 중 메시지 표시 (1.5초)"""
        self.console.draw_frame(
            5,
            self.console.height - 6,
            self.console.width - 10,
            3,
            "",
            fg=Colors.UI_BORDER,
            bg=(15, 15, 30),
        )
        self.console.print(7, self.console.height - 5, text[:70], fg=Colors.UI_TEXT)
        self.context.present(self.console)
        time.sleep(1.2)

    def _show_victory_screen(self):
        """승리 화면"""
        self.console.clear()
        w, h = self.console.width, self.console.height

        for y in range(h):
            for x in range(w):
                self.console.rgb[y, x] = (ord(" "), (5, 5, 15), (5, 5, 15))

        text = "★ 전투 승리! ★"
        self.console.print(
            (w - len(text)) // 2, h // 2, text, fg=(255, 215, 0)
        )
        self.context.present(self.console)
        time.sleep(2.0)
