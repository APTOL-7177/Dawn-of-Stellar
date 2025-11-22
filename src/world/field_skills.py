"""
Field Skill System - 필드 스킬 시스템

탐험 모드에서 사용하는 직업별 고유 스킬을 관리합니다.
"""

from typing import Dict, Any, Tuple, Optional, List
import random

from src.core.logger import get_logger
from src.world.tile import TileType
from src.combat.status_effects import StatusType, create_status_effect, StatusEffect
from src.character.character import Character
from src.ui.party_setup import PartyMember

logger = get_logger("field_skills")

class FieldSkillManager:
    """필드 스킬 관리자"""

    def __init__(self, exploration_system):
        self.exploration = exploration_system
        self.dungeon = exploration_system.dungeon
        
        # 스킬 데이터 정의
        self.skills = {
            # === 전사 계열 ===
            "warrior_iron_will": {
                "name": "강철 체력", 
                "mp": 20, 
                "func": self._skill_warrior_iron_will,
                "desc": "HP 30% 회복, 10턴간 방어력 감소"
            },
            "gladiator_fighting_spirit": {
                "name": "투지", 
                "mp": 0, 
                "func": self._skill_gladiator_fighting_spirit,
                "desc": "HP 10% 소모하여 MP 30 회복"
            },
            "knight_defense": {
                "name": "방비 태세", 
                "mp": 25, 
                "func": self._skill_knight_defense,
                "desc": "파티 전체 방어력 증가 (20턴)"
            },
            "paladin_holy_light": {
                "name": "신성한 빛", 
                "mp": 40, 
                "func": self._skill_paladin_holy_light,
                "desc": "파티 전체 HP 15% 회복 및 저주 제거"
            },
            "dark_knight_pact": {
                "name": "어둠의 계약", 
                "mp": 10, 
                "func": self._skill_dark_knight_pact,
                "desc": "HP 50% 소모, 다음 공격 강화"
            },
            "berserker_rage": {
                "name": "분노 축적", 
                "mp": 10, 
                "func": self._skill_berserker_rage,
                "desc": "HP 20 소모, 공격력 대폭 상승 상태 획득"
            },
            "dragon_knight_scale": {
                "name": "용의 비늘", 
                "mp": 30, 
                "func": self._skill_dragon_knight_scale,
                "desc": "파티 전체 화염 보호막 부여 (30턴)"
            },
            "sword_saint_mind_eye": {
                "name": "심안", 
                "mp": 20, 
                "func": self._skill_sword_saint_mind_eye,
                "desc": "주변 적 감지 및 명중률 상승"
            },
            "samurai_meditation": {
                "name": "명상", 
                "mp": 0, 
                "func": self._skill_samurai_meditation,
                "desc": "정신을 집중하여 치명타율 증가"
            },
            "breaker_smash": {
                "name": "파쇄", 
                "mp": 15, 
                "func": self._skill_breaker_smash,
                "desc": "전방의 벽이나 문을 파괴"
            },
            "spellblade_conversion": {
                "name": "마력 변환", 
                "mp": 0, 
                "func": self._skill_spellblade_conversion,
                "desc": "남은 MP를 모두 소모하여 HP 대폭 회복"
            },

            # === 마법/지원 계열 ===
            "archmage_mana_sense": {
                "name": "마나 감지", 
                "mp": 20, 
                "func": self._skill_archmage_mana_sense,
                "desc": "현재 층의 상자, 크리스탈 위치 표시"
            },
            "elementalist_protection": {
                "name": "자연의 보호", 
                "mp": 30, 
                "func": self._skill_elementalist_protection,
                "desc": "파티 전체에 랜덤 원소 보호막 부여"
            },
            "time_mage_rewind": {
                "name": "시간 역행", 
                "mp": 50, 
                "func": self._skill_time_mage_rewind,
                "desc": "현재 위치 저장 (재사용 시 복귀)"
            },
            "dimensionist_phase_shift": {
                "name": "위상 이동", 
                "mp": 30, 
                "func": self._skill_dimensionist_phase_shift,
                "desc": "무작위 안전한 위치로 텔레포트"
            },
            "necromancer_drain": {
                "name": "생명 흡수", 
                "mp": 15, 
                "func": self._skill_necromancer_drain,
                "desc": "주변 적의 체력을 흡수하여 회복"
            },
            "battle_mage_shield": {
                "name": "마력 보호막", 
                "mp": 20, 
                "func": self._skill_battle_mage_shield,
                "desc": "마나 실드 부여 (MP로 데미지 흡수)"
            },
            "bard_march": {
                "name": "활력의 노래", 
                "mp": 30, 
                "func": self._skill_bard_march,
                "desc": "파티 전체 HP 재생 상태 부여 (50턴)"
            },
            "priest_blessing": {
                "name": "축복", 
                "mp": 60, 
                "func": self._skill_priest_blessing,
                "desc": "자신의 HP/상태이상 완전 회복"
            },
            "cleric_prayer": {
                "name": "치유의 기도", 
                "mp": 30, 
                "func": self._skill_cleric_prayer,
                "desc": "파티 전체 HP 20% 회복"
            },
            "druid_purify": {
                "name": "자연의 정화", 
                "mp": 25, 
                "func": self._skill_druid_purify,
                "desc": "파티 전체 상태이상 제거 및 소량 회복"
            },
            "shaman_spirit_scout": {
                "name": "혼령 정찰", 
                "mp": 20, 
                "func": self._skill_shaman_spirit_scout,
                "desc": "주변 시야를 대폭 밝힘"
            },

            # === 기술/민첩 계열 ===
            "archer_eagle_eye": {
                "name": "매의 눈", 
                "mp": 15, 
                "func": self._skill_archer_eagle_eye,
                "desc": "50턴간 시야 범위 증가"
            },
            "sniper_camouflage": {
                "name": "위장", 
                "mp": 25, 
                "func": self._skill_sniper_camouflage,
                "desc": "적에게 발각되지 않는 은신 상태 부여"
            },
            "rogue_unlock": {
                "name": "자물쇠 따기", 
                "mp": 10, 
                "func": self._skill_rogue_unlock,
                "desc": "인접한 잠긴 문이나 상자를 즉시 염"
            },
            "assassin_poison": {
                "name": "독 바르기", 
                "mp": 20, 
                "func": self._skill_assassin_poison,
                "desc": "무기에 독을 발라 첫 공격 시 중독 유발"
            },
            "pirate_plunder": {
                "name": "약탈 감각", 
                "mp": 10, 
                "func": self._skill_pirate_plunder,
                "desc": "층 내의 모든 아이템/골드 위치 표시"
            },
            "engineer_disarm": {
                "name": "함정 해체", 
                "mp": 15, 
                "func": self._skill_engineer_disarm,
                "desc": "주변 5칸 이내의 함정 제거"
            },
            "hacker_hack": {
                "name": "시스템 해킹", 
                "mp": 40, 
                "func": self._skill_hacker_hack,
                "desc": "층 내 모든 잠긴 문 해제 및 기계형 적 무력화"
            },
            "alchemist_brew": {
                "name": "포션 제조", 
                "mp": 30, 
                "func": self._skill_alchemist_brew,
                "desc": "HP 포션 1개 생성 (연금술 재료 소모)"
            },
            "monk_inner_peace": {
                "name": "내공", 
                "mp": 10, 
                "func": self._skill_monk_inner_peace,
                "desc": "HP 회복 및 상태이상 제거"
            },
            "philosopher_insight": {
                "name": "통찰", 
                "mp": 25, 
                "func": self._skill_philosopher_insight,
                "desc": "보스룸 또는 하층 계단 위치 발견"
            },
            "vampire_transfusion": {
                "name": "수혈", 
                "mp": 10, 
                "func": self._skill_vampire_transfusion,
                "desc": "자신 HP 소모하여 아군 HP 대폭 회복"
            },
        }

        # 직업 ID -> 스킬 키 매핑
        self.class_map = {
            "warrior": "warrior_iron_will",
            "gladiator": "gladiator_fighting_spirit",
            "knight": "knight_defense",
            "paladin": "paladin_holy_light",
            "dark_knight": "dark_knight_pact",
            "berserker": "berserker_rage",
            "dragon_knight": "dragon_knight_scale",
            "sword_saint": "sword_saint_mind_eye",
            "samurai": "samurai_meditation",
            "breaker": "breaker_smash",
            "spellblade": "spellblade_conversion",
            
            "archmage": "archmage_mana_sense",
            "elementalist": "elementalist_protection",
            "time_mage": "time_mage_rewind",
            "dimensionist": "dimensionist_phase_shift",
            "necromancer": "necromancer_drain",
            "battle_mage": "battle_mage_shield",
            "bard": "bard_march",
            "priest": "priest_blessing", # 신관
            "cleric": "cleric_prayer",   # 성직자
            "druid": "druid_purify",
            "shaman": "shaman_spirit_scout",

            "archer": "archer_eagle_eye",
            "sniper": "sniper_camouflage",
            "rogue": "rogue_unlock",
            "assassin": "assassin_poison",
            "pirate": "pirate_plunder",
            "engineer": "engineer_disarm",
            "hacker": "hacker_hack",
            "alchemist": "alchemist_brew",
            "monk": "monk_inner_peace",
            "philosopher": "philosopher_insight",
            "vampire": "vampire_transfusion",
        }
        
        # 시간 역행용 저장 좌표
        self.rewind_pos = None

    def get_skill_info(self, character_class: str) -> Optional[dict]:
        """직업에 해당하는 스킬 정보 반환"""
        skill_key = self.class_map.get(character_class)
        if not skill_key:
            # 매핑에 없는 경우 job_id로 다시 시도 (가끔 id가 다를 수 있음)
            return None
        return self.skills.get(skill_key)

    def use_skill(self, user: Character) -> Tuple[bool, str]:
        """스킬 사용"""
        skill_info = self.get_skill_info(user.character_class)
        if not skill_info:
            return False, "사용할 수 있는 필드 스킬이 없습니다."

        # MP 체크
        if user.current_mp < skill_info["mp"]:
            return False, "MP가 부족합니다."

        # 스킬 실행
        success, msg = skill_info["func"](user)

        if success:
            user.current_mp -= skill_info["mp"]
            # 턴 소모 (선택적 적용, 여기선 즉시 발동이라 가정하나 
            # ExplorationSystem에서 턴을 넘기도록 처리할 수 있음)
            return True, msg
        else:
            return False, msg

    # =========================================================================
    # 스킬 구현부
    # =========================================================================

    # --- 전사 계열 ---
    def _skill_warrior_iron_will(self, user: Character) -> Tuple[bool, str]:
        heal_amount = int(user.max_hp * 0.3)
        user.heal(heal_amount)
        
        # 방어력 감소 (SLOW 대신)
        status = create_status_effect(
            name="무방비",
            status_type=StatusType.REDUCE_DEF,
            duration=10,
            intensity=0.3
        )
        user.status_manager.add_status(status)
        return True, f"HP가 {heal_amount} 회복되었지만 일시적으로 방어력이 감소했습니다."

    def _skill_gladiator_fighting_spirit(self, user: Character) -> Tuple[bool, str]:
        hp_cost = int(user.max_hp * 0.1)
        if user.current_hp <= hp_cost:
            return False, "HP가 너무 적습니다."
            
        user.take_damage(hp_cost)
        user.current_mp = min(user.max_mp, user.current_mp + 30)
        return True, "HP를 태워 MP 30을 회복했습니다."

    def _skill_knight_defense(self, user: Character) -> Tuple[bool, str]:
        party = self.exploration.player.party
        count = 0
        for member in party:
            # 이미 있으면 갱신
            status = create_status_effect(
                name="방비태세",
                status_type=StatusType.BOOST_DEF,
                duration=20,
                intensity=0.3
            )
            member.status_manager.add_status(status)
            count += 1
        return True, f"파티원 {count}명의 방어력이 증가했습니다."

    def _skill_paladin_holy_light(self, user: Character) -> Tuple[bool, str]:
        party = self.exploration.player.party
        for member in party:
            member.heal(int(member.max_hp * 0.15))
            member.status_manager.remove_status(StatusType.CURSE)
        return True, "파티원을 치유하고 저주를 정화했습니다."
    
    def _skill_dark_knight_pact(self, user: Character) -> Tuple[bool, str]:
        hp_cost = user.current_hp // 2
        if hp_cost < 1:
            return False, "HP가 부족합니다."
        
        user.take_damage(hp_cost)
        status = create_status_effect(
            name="어둠의계약",
            status_type=StatusType.STRENGTHEN, # 다음 공격 강화
            duration=3, # 3턴 지속 (전투 시작 시 적용되도록)
            intensity=1.0 # 2배
        )
        user.status_manager.add_status(status)
        return True, "생명을 바쳐 강력한 힘을 얻었습니다."

    def _skill_berserker_rage(self, user: Character) -> Tuple[bool, str]:
        if user.current_hp <= 20:
            return False, "HP가 부족합니다."
        user.take_damage(20)
        status = create_status_effect(
            name="분노",
            status_type=StatusType.RAGE,
            duration=10,
            intensity=0.5
        )
        user.status_manager.add_status(status)
        return True, "분노가 끓어오릅니다!"

    def _skill_dragon_knight_scale(self, user: Character) -> Tuple[bool, str]:
        party = self.exploration.player.party
        for member in party:
            status = create_status_effect(
                name="용의비늘",
                status_type=StatusType.FIRE_SHIELD,
                duration=30,
                intensity=1.0
            )
            member.status_manager.add_status(status)
        return True, "파티원에게 화염 보호막을 부여했습니다."

    def _skill_sword_saint_mind_eye(self, user: Character) -> Tuple[bool, str]:
        # 주변 적 감지
        found = 0
        px, py = self.exploration.player.x, self.exploration.player.y
        for enemy in self.exploration.enemies:
             # 적 엔티티가 x, y 속성을 가지고 있다고 가정
            if abs(enemy.x - px) <= 5 and abs(enemy.y - py) <= 5:
                # 시야에 잠시 보이게 처리 (깜빡임 효과 등은 UI에서 처리해야 하지만 여기선 로그로)
                found += 1
        
        status = create_status_effect(
            name="심안",
            status_type=StatusType.BOOST_ACCURACY,
            duration=10,
            intensity=0.5
        )
        user.status_manager.add_status(status)
        
        msg = f"심안을 개방했습니다. (명중률 상승)"
        if found > 0:
            msg += f" 주변에 적 {found}기가 느껴집니다."
        else:
            msg += " 주변에 적의 기척이 없습니다."
        return True, msg

    def _skill_samurai_meditation(self, user: Character) -> Tuple[bool, str]:
        # 즉시 발동 (MP 회복 제거, 집중 상태만 부여)
        status = create_status_effect(
            name="명상",
            status_type=StatusType.FOCUS,
            duration=5,
            intensity=0.5  # 강도 상향 (0.3 -> 0.5)
        )
        user.status_manager.add_status(status)
        return True, "깊은 명상을 통해 정신을 가다듬었습니다."

    def _skill_breaker_smash(self, user: Character) -> Tuple[bool, str]:
        player = self.exploration.player
        dx, dy = player.dx, player.dy
        tx, ty = player.x + dx, player.y + dy
        
        tile = self.dungeon.get_tile(tx, ty)
        if not tile:
            return False, "파괴할 대상이 없습니다."
            
        if tile.tile_type in [TileType.WALL, TileType.DOOR, TileType.LOCKED_DOOR, TileType.SECRET_DOOR]:
            # 맵 경계 체크 (가장자리는 파괴 불가)
            if tx == 0 or ty == 0 or tx == self.dungeon.width - 1 or ty == self.dungeon.height - 1:
                 return False, "던전의 외벽은 파괴할 수 없습니다."
                 
            tile.tile_type = TileType.FLOOR
            tile.walkable = True
            tile.transparent = True
            tile.char = "."
            tile.fg_color = (100, 100, 100)
            tile.locked = False
            tile.block_sight = False # 시야 차단 해제
            
            # FOV 갱신 필요
            self.exploration.update_fov()
            
            return True, "벽을 산산조각 냈습니다!"
        else:
            return False, "파괴할 수 없는 대상입니다."

    def _skill_spellblade_conversion(self, user: Character) -> Tuple[bool, str]:
        mp = user.current_mp
        if mp <= 0:
            return False, "MP가 없습니다."
            
        heal = mp * 2
        user.current_mp = 0
        user.heal(heal)
        return True, f"MP를 모두 소모하여 HP {heal}을 회복했습니다."

    # --- 마법/지원 계열 ---
    def _skill_archmage_mana_sense(self, user: Character) -> Tuple[bool, str]:
        count = 0
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                tile = self.dungeon.get_tile(x, y)
                if tile.tile_type in [TileType.CHEST, TileType.CRYSTAL, TileType.SHRINE, TileType.MANA_WELL]:
                    if not tile.explored:
                        tile.explored = True
                        count += 1
        return True, f"마력 반응 {count}곳을 감지하여 지도에 기록했습니다."

    def _skill_elementalist_protection(self, user: Character) -> Tuple[bool, str]:
        shields = [StatusType.FIRE_SHIELD, StatusType.ICE_SHIELD, StatusType.SHADOW_SHIELD]
        party = self.exploration.player.party
        
        for member in party:
            shield_type = random.choice(shields)
            status = create_status_effect(
                name="원소보호",
                status_type=shield_type,
                duration=30,
                intensity=1.0
            )
            member.status_manager.add_status(status)
        return True, "파티원에게 원소의 가호를 내렸습니다."

    def _skill_time_mage_rewind(self, user: Character) -> Tuple[bool, str]:
        player = self.exploration.player
        
        if self.rewind_pos is None:
            self.rewind_pos = (player.x, player.y)
            # MP 반환 (첫 사용은 설정만)
            user.current_mp += 50 # 코스트 페이백
            return True, "현재 위치가 시간의 틈새에 기록되었습니다. 다시 사용하여 복귀합니다."
        else:
            tx, ty = self.rewind_pos
            player.x, player.y = tx, ty
            self.exploration.update_fov()
            self.rewind_pos = None
            return True, "과거의 위치로 시간을 되돌렸습니다."

    def _skill_dimensionist_phase_shift(self, user: Character) -> Tuple[bool, str]:
        # 랜덤 텔레포트 (안전한 곳으로)
        for _ in range(10): # 10번 시도
            rx = random.randint(1, self.dungeon.width - 2)
            ry = random.randint(1, self.dungeon.height - 2)
            tile = self.dungeon.get_tile(rx, ry)
            if tile and tile.walkable and tile.tile_type == TileType.FLOOR:
                self.exploration.player.x = rx
                self.exploration.player.y = ry
                self.exploration.update_fov()
                return True, "차원의 틈을 통해 이동했습니다."
        return False, "이동할 안전한 공간을 찾지 못했습니다."

    def _skill_necromancer_drain(self, user: Character) -> Tuple[bool, str]:
        px, py = self.exploration.player.x, self.exploration.player.y
        drained = 0
        
        for enemy in list(self.exploration.enemies): 
             if abs(enemy.x - px) <= 3 and abs(enemy.y - py) <= 3:
                if hasattr(enemy, 'hp'):
                    dmg = 10
                    enemy.hp -= dmg
                    drained += dmg
                    if enemy.hp <= 0:
                        pass
        
        if drained > 0:
            user.heal(drained)
            return True, f"주변 생명력 {drained}를 흡수했습니다."
        else:
            return False, "흡수할 대상이 주변에 없습니다."

    def _skill_battle_mage_shield(self, user: Character) -> Tuple[bool, str]:
        status = create_status_effect(
            name="마나실드",
            status_type=StatusType.MANA_SHIELD,
            duration=30,
            intensity=3.0 # MP 1당 HP 3 효율
        )
        user.status_manager.add_status(status)
        return True, "마나로 이루어진 보호막을 전개했습니다. (MP로 피해 흡수)"

    def _skill_bard_march(self, user: Character) -> Tuple[bool, str]:
        party = self.exploration.player.party
        for member in party:
            status = create_status_effect(
                name="활력의노래",
                status_type=StatusType.REGENERATION,
                duration=50,
                intensity=1.0 
            )
            member.status_manager.add_status(status)
        return True, "활력의 노래가 파티의 체력을 서서히 회복시킵니다."

    def _skill_priest_blessing(self, user: Character) -> Tuple[bool, str]:
        user.heal(user.max_hp)
        user.status_manager.clear_all_effects() 
        return True, "신의 축복으로 몸이 정화되었습니다."

    def _skill_cleric_prayer(self, user: Character) -> Tuple[bool, str]:
        party = self.exploration.player.party
        for member in party:
            member.heal(int(member.max_hp * 0.2))
        return True, "치유의 기도가 파티를 감쌉니다."

    def _skill_druid_purify(self, user: Character) -> Tuple[bool, str]:
        party = self.exploration.player.party
        removed_count = 0
        target_debuffs = [StatusType.POISON, StatusType.DISEASE, StatusType.CURSE, StatusType.BURN]
        
        for member in party:
            member.heal(10)
            for debuff in target_debuffs:
                if member.status_manager.remove_status(debuff):
                    removed_count += 1
        return True, f"자연의 힘으로 {removed_count}개의 해로운 효과를 정화했습니다."

    def _skill_shaman_spirit_scout(self, user: Character) -> Tuple[bool, str]:
        px, py = self.exploration.player.x, self.exploration.player.y
        if hasattr(self.exploration, 'fov_system'):
            # 현재 시야 + 8
            base_radius = getattr(self.exploration.fov_system, 'default_radius', 8)
            skill_radius = base_radius + 8
            
            visible_tiles = self.exploration.fov_system.compute_fov(
                self.dungeon, px, py, radius=skill_radius
            )
            for x, y in visible_tiles:
                tile = self.dungeon.get_tile(x, y)
                if tile:
                    tile.explored = True
            
            self.exploration.update_fov()
            return True, f"혼령들이 주변 {skill_radius}칸을 정찰하고 돌아왔습니다."
        return False, "시야 시스템 오류"

    # --- 기술/민첩 계열 ---
    def _skill_archer_eagle_eye(self, user: Character) -> Tuple[bool, str]:
        status = create_status_effect(
            name="매의눈",
            status_type=StatusType.FORESIGHT,
            duration=50,
            intensity=1.0
        )
        user.status_manager.add_status(status)
        return True, "먼 곳까지 꿰뚫어 볼 수 있게 되었습니다." 

    def _skill_sniper_camouflage(self, user: Character) -> Tuple[bool, str]:
        status = create_status_effect(
            name="위장",
            status_type=StatusType.STEALTH,
            duration=30,
            intensity=1.0
        )
        user.status_manager.add_status(status)
        return True, "주변 환경에 완벽하게 녹아들었습니다."

    def _skill_rogue_unlock(self, user: Character) -> Tuple[bool, str]:
        px, py = self.exploration.player.x, self.exploration.player.y
        unlocked = False
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                if dx == 0 and dy == 0: continue
                tile = self.dungeon.get_tile(px + dx, py + dy)
                if tile and tile.locked:
                    tile.unlock()
                    unlocked = True
        
        if unlocked:
            return True, "잠금 장치를 해제했습니다."
        else:
            return False, "주변에 잠긴 대상이 없습니다."

    def _skill_assassin_poison(self, user: Character) -> Tuple[bool, str]:
        status = create_status_effect(
            name="맹독무기",
            status_type=StatusType.BOOST_ATK,
            duration=10,
            intensity=0.3
        )
        status.metadata["on_hit_effect"] = StatusType.POISON
        user.status_manager.add_status(status)
        return True, "무기에 치명적인 독을 발랐습니다."

    def _skill_pirate_plunder(self, user: Character) -> Tuple[bool, str]:
        count = 0
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                tile = self.dungeon.get_tile(x, y)
                if tile.tile_type in [TileType.GOLD, TileType.ITEM, TileType.DROPPED_ITEM]:
                    if not tile.explored:
                        tile.explored = True
                        count += 1
        return True, f"보물 냄새를 맡았습니다! ({count}개 발견)"

    def _skill_engineer_disarm(self, user: Character) -> Tuple[bool, str]:
        px, py = self.exploration.player.x, self.exploration.player.y
        count = 0
        for y in range(py - 5, py + 6):
            for x in range(px - 5, px + 6):
                tile = self.dungeon.get_tile(x, y)
                if tile and tile.tile_type in [TileType.TRAP, TileType.SPIKE_TRAP, TileType.FIRE_TRAP, TileType.POISON_GAS]:
                    tile.tile_type = TileType.FLOOR
                    tile.char = "."
                    tile.fg_color = (100, 100, 100)
                    tile.trap_damage = 0
                    count += 1
        
        if count > 0:
            return True, f"주변의 함정 {count}개를 해체했습니다."
        else:
            return False, "주변에 함정이 없습니다."

    def _skill_hacker_hack(self, user: Character) -> Tuple[bool, str]:
        count = 0
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                tile = self.dungeon.get_tile(x, y)
                if tile and tile.locked:
                    tile.unlock()
                    count += 1
        return True, f"던전 보안 시스템 해킹 완료. {count}개의 보안을 무력화했습니다."

    def _skill_alchemist_brew(self, user: Character) -> Tuple[bool, str]:
        # 연금술 재료(기믹 수치) 소모
        if not hasattr(user, 'potion_stock'):
            return False, "연금술 도구가 없습니다."
            
        if user.potion_stock < 1:
            return False, "연금술 재료가 부족합니다."
            
        user.potion_stock -= 1
        # 실제 아이템 생성은 여기서 간단히 로그로 처리 (인벤토리 의존성 문제)
        # 아이템을 획득했다는 메시지만 출력
        return True, "연금술 재료를 소모하여 회복 포션을 제조했습니다."

    def _skill_monk_inner_peace(self, user: Character) -> Tuple[bool, str]:
        # HP 회복 + 상태이상 제거
        heal_amount = int(user.max_hp * 0.2)
        user.heal(heal_amount)
        user.status_manager.clear_all_effects()
        return True, "내면의 평화를 찾아 몸과 마음을 정화했습니다."

    def _skill_philosopher_insight(self, user: Character) -> Tuple[bool, str]:
        found = False
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                tile = self.dungeon.get_tile(x, y)
                if tile.tile_type in [TileType.BOSS_ROOM, TileType.STAIRS_DOWN]:
                    tile.explored = True
                    found = True
        
        if found:
            return True, "나아가야 할 길을 깨달았습니다."
        else:
            return False, "더 이상 찾을 것이 없습니다."

    def _skill_vampire_transfusion(self, user: Character) -> Tuple[bool, str]:
        if user.current_hp <= 20:
            return False, "HP가 부족합니다."
            
        party = self.exploration.player.party
        target = min(party, key=lambda p: p.current_hp / p.max_hp if p.max_hp > 0 else 1)
        
        if target == user:
            return False, "수혈 대상이 없습니다."
            
        user.take_damage(20)
        target.heal(50)
        return True, f"자신의 피를 나누어 {target.name}을(를) 치유했습니다."
