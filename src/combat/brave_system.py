"""
Brave System - 브레이브 시스템

Final Fantasy Dissidia/Opera Omnia 스타일의 BRV/HP 시스템

주요 기능:
- INT BRV: 초기 BRV (전투 시작 시 / 턴 시작 시 회복)
- MAX BRV: 최대 BRV 제한
- BRV 공격: 상대 BRV 감소 + 자신 BRV 증가
- HP 공격: 축적된 BRV를 소비하여 HP 데미지
- BREAK: 상대 BRV를 0으로 만들면 보너스 데미지 + 스턴
"""

from typing import Dict, Any, Optional
from src.core.config import get_config
from src.core.logger import get_logger
from src.core.event_bus import event_bus, Events
from src.combat.damage_calculator import get_damage_calculator
from src.combat.status_effects import StatusEffect, StatusType


class BraveSystem:
    """
    브레이브 시스템 매니저

    BRV 공격, HP 공격, BREAK 메커니즘 관리
    """

    def __init__(self) -> None:
        self.logger = get_logger("brave")
        self.config = get_config()

        # 설정 로드
        self.base_brv = self.config.get("combat.brave.base_brv", 100)
        self.max_brv_multiplier = self.config.get("combat.brave.max_brv_multiplier", 3.0)
        self.break_bonus = self.config.get("combat.brave.break_bonus", 1.5)
        self.break_stun_duration = self.config.get("combat.brave.break_stun_duration", 1)

        # BRV 효율 및 저항
        self.brv_efficiency_default = 1.0
        self.brv_loss_resistance_default = 1.0

    def calculate_int_brv(self, character: Any) -> int:
        """
        INT BRV 계산 (초기 BRV)

        Args:
            character: 캐릭터 객체

        Returns:
            계산된 INT BRV
        """
        # SimpleEnemy는 init_brv 속성을 사용 (BREAK 회복 시 current_brv가 0일 수 있음)
        if hasattr(character, '__class__') and character.__class__.__name__ == "SimpleEnemy":
            if hasattr(character, 'init_brv'):
                return character.init_brv
            else:
                # fallback: current_brv 사용 (구버전 호환성)
                return character.current_brv

        # Character 객체는 StatManager를 통해 init_brv 가져오기
        if hasattr(character, "stat_manager"):
            from src.character.stats import Stats
            base_int_brv = int(character.stat_manager.get_value(Stats.INIT_BRV, use_total=False))
        elif hasattr(character, "init_brv"):
            base_int_brv = character.init_brv
        else:
            base_int_brv = self.base_brv

        # 레벨 보너스
        level = getattr(character, "level", 1)
        level_bonus = (level - 1) * 10

        # 장비 보너스
        equipment_bonus = self._get_equipment_int_brv_bonus(character)

        total_int_brv = base_int_brv + level_bonus + equipment_bonus

        return max(50, total_int_brv)

    def calculate_max_brv(self, character: Any) -> int:
        """
        MAX BRV 계산 (최대 BRV)

        Args:
            character: 캐릭터 객체

        Returns:
            계산된 MAX BRV
        """
        # SimpleEnemy는 이미 생성자에서 max_brv가 설정되어 있으므로 그대로 사용
        if hasattr(character, '__class__') and character.__class__.__name__ == "SimpleEnemy":
            return character.max_brv

        # Character 객체는 StatManager를 통해 max_brv 가져오기
        if hasattr(character, "stat_manager"):
            from src.character.stats import Stats
            base_max_brv = int(character.stat_manager.get_value(Stats.MAX_BRV, use_total=False))
        elif hasattr(character, "max_brv") and not callable(getattr(type(character), "max_brv", None)):
            # max_brv가 property가 아닌 일반 속성인 경우
            base_max_brv = character.max_brv
        else:
            # INT BRV 기반으로 계산
            int_brv = self.calculate_int_brv(character)
            base_max_brv = int(int_brv * self.max_brv_multiplier)

        # 레벨 보너스
        level = getattr(character, "level", 1)
        level_bonus = (level - 1) * 50

        # 장비 보너스
        equipment_bonus = self._get_equipment_max_brv_bonus(character)

        total_max_brv = base_max_brv + level_bonus + equipment_bonus

        return max(200, total_max_brv)

    def _get_equipment_int_brv_bonus(self, character: Any) -> int:
        """장비로부터 INT BRV 보너스 계산"""
        bonus = 0
        if hasattr(character, "equipped_weapon") and character.equipped_weapon:
            bonus += getattr(character.equipped_weapon, "int_brv", 0)
        if hasattr(character, "equipped_armor") and character.equipped_armor:
            bonus += getattr(character.equipped_armor, "int_brv", 0)
        if hasattr(character, "equipped_accessory") and character.equipped_accessory:
            bonus += getattr(character.equipped_accessory, "int_brv", 0)
        return bonus

    def _get_equipment_max_brv_bonus(self, character: Any) -> int:
        """장비로부터 MAX BRV 보너스 계산"""
        bonus = 0
        if hasattr(character, "equipped_weapon") and character.equipped_weapon:
            bonus += getattr(character.equipped_weapon, "max_brv", 0)
        if hasattr(character, "equipped_armor") and character.equipped_armor:
            bonus += getattr(character.equipped_armor, "max_brv", 0)
        if hasattr(character, "equipped_accessory") and character.equipped_accessory:
            bonus += getattr(character.equipped_accessory, "max_brv", 0)
        return bonus

    def initialize_brv(self, character: Any) -> None:
        """
        전투 시작 시 BRV 초기화

        Args:
            character: 캐릭터 객체
        """
        # INT BRV와 MAX BRV 계산
        int_brv = self.calculate_int_brv(character)
        max_brv = self.calculate_max_brv(character)

        # 캐릭터에 저장
        character.current_brv = int_brv
        character.int_brv = int_brv
        character.max_brv = max_brv

        # BRV 효율 및 저항 초기화
        if not hasattr(character, "brv_efficiency"):
            character.brv_efficiency = self.brv_efficiency_default
        if not hasattr(character, "brv_loss_resistance"):
            character.brv_loss_resistance = self.brv_loss_resistance_default

        self.logger.debug(
            f"BRV 초기화: {character.name}",
            {"int_brv": int_brv, "max_brv": max_brv}
        )

        event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
            "character": character,
            "change": int_brv,
            "current": int_brv,
            "max": max_brv
        })

    def brv_attack(
        self,
        attacker: Any,
        defender: Any,
        damage: int
    ) -> Dict[str, Any]:
        """
        BRV 공격

        상대방의 BRV를 감소시키고 자신의 BRV를 증가시킵니다.
        효율과 저항이 반영됩니다.

        Args:
            attacker: 공격자
            defender: 방어자
            damage: BRV 데미지

        Returns:
            공격 결과 {"brv_stolen": int, "actual_gain": int, "is_break": bool}
        """
        # 빗나간 공격 (데미지 0)은 BRV 회복 없음
        if damage == 0:
            return {
                "brv_stolen": 0,
                "actual_gain": 0,
                "is_break": False,
                "damage": 0,
                "miss": True
            }

        # 공격자 레벨에 따른 BRV 데미지 증가 (레벨당 30%)
        attacker_level = getattr(attacker, 'level', 1)
        from src.core.config import get_config
        config = get_config()
        level_scaling_per_level = config.get("combat.damage.level_scaling_per_level", 0.3)
        level_scaling = 1.0 + (attacker_level - 1) * level_scaling_per_level
        scaled_damage = int(damage * level_scaling)

        # 방어자의 BRV 저항 반영
        defender_resistance = getattr(defender, "brv_loss_resistance", 1.0)
        actual_damage = int(scaled_damage / defender_resistance)

        # BRV 감소 (최소 0)
        old_defender_brv = defender.current_brv
        defender.current_brv = max(0, defender.current_brv - actual_damage)

        # BREAK 상태 확인 (공격 전 BRV가 0인지)
        was_broken = old_defender_brv == 0
        already_broken = self.is_broken(defender)

        # BRV 획득량 계산
        if was_broken:
            # BREAK 상태: 가한 데미지만큼 BRV 획득
            brv_stolen = actual_damage
        else:
            # 일반 상태: 실제로 훔친 BRV
            brv_stolen = min(actual_damage, max(0, old_defender_brv))

        # 공격자의 BRV 효율 반영
        attacker_efficiency = getattr(attacker, "brv_efficiency", 1.0)
        brv_gain = int(brv_stolen * attacker_efficiency)

        # BRV 흡수 (MAX BRV 제한)
        old_attacker_brv = attacker.current_brv
        attacker.current_brv = min(
            attacker.current_brv + brv_gain,
            attacker.max_brv
        )
        actual_gain = attacker.current_brv - old_attacker_brv

        # BREAK 판정: BRV가 0인 상태에서 추가로 BRV 공격을 받았을 때 BREAK
        is_break = False
        
        # BRV가 0인 상태에서 추가로 BRV 공격을 받았을 때 BREAK
        if was_broken and actual_damage > 0 and not already_broken:
            is_break = True
            self.logger.info(f"[BREAK] {attacker.name} -> {defender.name} (BRV 0 상태에서 추가 공격, BRV 획득: {brv_gain})")

            # BREAK 상태 플래그 설정
            defender.is_broken = True

            # =========================================================================================
            # [NEW] 브레이커: SCATTER 시스템
            # =========================================================================================
            if hasattr(attacker, "job_id") and attacker.job_id == "breaker":
                defender.is_scattered = True
                defender.scatter_source = attacker
                defender.scatter_stacks = 0
                
                # 시각적 알림 (로그)
                self.logger.info(f"[SCATTER] {attacker.name}이 {defender.name}을 산산조각 냈습니다!")
                
                # [FIX] StatusEffect로 SCATTER 상태 적용 (UI 표시 및 지속시간 관리)
                if hasattr(defender, 'status_manager'):
                    scatter_status = StatusEffect(
                        name="SCATTER",
                        status_type=StatusType.SCATTER,
                        duration=2, # 지속시간 2턴 설정
                        metadata={"source": attacker},
                        is_stackable=True,
                        max_stacks=99
                    )
                    defender.status_manager.add_status(scatter_status)
                
                # 특성 체크: 증기 흡수 (Steam Siphon) => SCATTER 시 브레이커 HP 10% 회복
                is_siphon = False
                if hasattr(attacker, "system_traits") and "steam_siphon" in attacker.system_traits: is_siphon = True
                if hasattr(attacker, "traits"):
                     for t in attacker.traits:
                         tid = t if isinstance(t, str) else t.get("id")
                         if tid == "steam_siphon": is_siphon = True
                
                if is_siphon and hasattr(attacker, "heal") and hasattr(attacker, "max_hp"):
                    heal_amt = int(attacker.max_hp * 0.10)
                    attacker.heal(heal_amt)
                    self.logger.info(f"[증기 흡수] SCATTER 효과로 HP 회복: {heal_amt}")

                # 추가 행동 (연격) 체크
                # 조건: 연격 기믹 수치가 브레이커 공격력의 50%를 넘는가?
                # 비용: 공격력의 50%만큼 감소
                if hasattr(attacker, "combo_gauge"):
                    # 공격력 가져오기
                    atk_val = 0
                    if hasattr(attacker, "stat_manager"):
                        from src.character.stats import Stats
                        atk_val = attacker.stat_manager.get_value(Stats.STRENGTH)
                    else:
                        atk_val = getattr(attacker, "physical_attack", 100)
                    
                    cost = int(atk_val * 0.5)
                    
                    if attacker.combo_gauge >= cost:
                        # 비용 소비
                        attacker.combo_gauge -= cost
                        
                        # ATB 재충전 (추가 행동)
                        from src.combat.atb_system import get_atb_system
                        atb_sys = get_atb_system()
                        gauge = atb_sys.get_gauge(attacker)
                        if gauge:
                            # 턴 즉시 획득 처리를 위해 게이지를 threshold + 1로 설정?
                            # 단순 full charge로는 현재 턴 프로세스에 바로 끼어들지 못할 수 있음.
                            # 하지만 게임 루프가 ATB 높은 순으로 다시 가져오므로 Max로 채우면 됨.
                            # 턴 즉시 획득 처리를 위해 게이지를 max_gauge로 설정
                            # (턴 종료 시 threshold만큼 소비하므로, max로 채워야 턴이 돌아옴)
                            gauge.current = gauge.max_gauge
                            self.logger.info(f"[연격 발동] {attacker.name} 추가 행동! (게이지 소모: {cost}, 남은 게이지: {attacker.combo_gauge})")
                            
                            # 특성: 파괴 추진력 (break_momentum) -> 다음 공격 강화
                            # 여기서는 SCATTER 발동 시 효과로도 볼 수 있음
                            event_bus.publish("breaker.extra_action", {"attacker": attacker})

                            # UI 알림
                            from src.combat.combat_manager import get_combat_manager
                            cm = get_combat_manager()
                            if cm and hasattr(cm, "combat_ui") and cm.combat_ui:
                                if hasattr(cm.combat_ui, "add_message"):
                                    cm.combat_ui.add_message(f"[연격 발동] {attacker.name}의 추가 행동!", (0, 255, 255))

            # BREAK 전용 효과음 재생
            from src.audio import play_sfx
            play_sfx("combat", "break")

            event_bus.publish("brave.break", {
                "attacker": attacker,
                "defender": defender,
                "brv_stolen": brv_stolen
            })
        elif was_broken and actual_damage > 0 and already_broken:
            # 이미 BREAK 상태라면 추가 BREAK 면역 (로그만 출력)
            self.logger.debug(f"{defender.name}은(는) 이미 BREAK 상태여서 추가 BREAK 면역")
            
            # [NEW] 이미 SCATTER 상태인 경우 스택 리셋 등은 하지 않음 (기획서: "중복 BREAK는 1회로 간주" -> 무시)
            pass

        # [NEW] BRV 공격 시 SCATTER 스택 증가 (콤보 게이지는 증가하지 않음)
        # SCATTER 상태인 적에게 BRV 공격 시 스택만 증가
        if actual_damage > 0 and hasattr(defender, 'status_manager'):
            if defender.status_manager.has_status(StatusType.SCATTER):
                scatter_status = defender.status_manager.get_status(StatusType.SCATTER)
                if scatter_status:
                    scatter_status.stack_count += 1
                    self.logger.info(f"[SCATTER-BRV-STACK] {defender.name} 스택 증가: {scatter_status.stack_count - 1} -> {scatter_status.stack_count} (BRV 공격, 콤보 게이지 증가 없음)")

        # 이벤트 발행
        event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
            "character": attacker,
            "change": actual_gain,
            "current": attacker.current_brv,
            "max": attacker.max_brv
        })

        event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
            "character": defender,
            "change": -brv_stolen,
            "current": defender.current_brv,
            "max": defender.max_brv
        })

        return {
            "brv_stolen": brv_stolen,
            "actual_gain": actual_gain,
            "is_break": is_break,
            "damage": actual_damage,
            "miss": False
        }

    def hp_attack(
        self,
        attacker: Any,
        defender: Any,
        brv_multiplier: float = 1.0,
        damage_type: str = "physical",
        **kwargs
    ) -> Dict[str, Any]:
        """
        HP 공격

        축적된 BRV를 소비하여 HP 데미지를 가합니다.
        공격자의 스탯(힘/마법)과 방어자의 스탯(방어/정신)을 고려합니다.

        Args:
            attacker: 공격자
            defender: 방어자
            brv_multiplier: BRV 배율 (스킬에 따라 다름)
            damage_type: 데미지 타입 ("physical" 또는 "magical")

        Returns:
            공격 결과 {"hp_damage": int, "brv_consumed": int}
        """
        if attacker.current_brv <= 0:
            self.logger.warning(f"{attacker.name}: BRV가 0이라 HP 공격 불가")
            return {"hp_damage": 0, "brv_consumed": 0}

        # 데미지 계산기 사용
        damage_calc = get_damage_calculator()

        # BREAK 상태 확인 (is_broken 플래그 사용, BRV=0만으로는 BREAK가 아님)
        is_defender_broken = self.is_broken(defender)

        # HP 데미지 계산 (스탯 기반)
        damage_result, wound_damage = damage_calc.calculate_hp_damage(
            attacker=attacker,
            defender=defender,
            brv_points=attacker.current_brv,
            hp_multiplier=brv_multiplier,
            is_break=is_defender_broken,
            damage_type=damage_type,
            **kwargs  # 관통탄 방어 관통력 등 전달
        )

        # HP 데미지 적용 전에 상처 적용 플래그 설정 (중복 방지)
        if hasattr(defender, "wound"):
            defender._wound_applied_this_turn = True
        
        # HP 데미지 적용
        # shield_mastery 등의 DEFEND_BOOST 효과는 take_damage 내부의 calculate_damage_reduction에서 처리됨
        # 여기서는 BRV 회복만 처리
        from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
        trait_manager = get_trait_effect_manager()
        
        # 방어 중인지 확인
        is_defending = False
        if hasattr(defender, 'status_manager'):
            from src.combat.status_effects import StatusType
            if hasattr(defender.status_manager, 'has_status'):
                is_defending = defender.status_manager.has_status(StatusType.GUARDIAN) or \
                               defender.status_manager.has_status(StatusType.SHIELD)
        
        # 방어 보너스: BRV 회복만 여기서 처리 (피해 감소는 take_damage에서 처리)
        if is_defending and hasattr(defender, 'active_traits'):
            for trait_data in defender.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                effects = trait_manager.get_trait_effects(trait_id)
                for effect in effects:
                    if effect.effect_type == TraitEffectType.DEFEND_BOOST:
                        # BRV 회복만 처리
                        if effect.metadata and "brv_regen" in effect.metadata:
                            brv_regen = effect.metadata["brv_regen"]
                            brv_recovered = int(defender.max_brv * brv_regen)
                            old_brv = defender.current_brv
                            defender.current_brv = min(defender.current_brv + brv_recovered, defender.max_brv)
                            actual_brv_regen = defender.current_brv - old_brv
                            if actual_brv_regen > 0:
                                self.logger.info(f"[{trait_id}] {defender.name} BRV 회복: +{actual_brv_regen} ({brv_regen * 100:.0f}%)")
        
        # 보호 효과를 위해 원본 공격 정보 저장
        defender._last_attacker = attacker
        defender._last_damage_type = damage_type
        defender._last_brv_points = attacker.current_brv
        defender._last_hp_multiplier = brv_multiplier
        defender._last_is_break = is_defender_broken
        defender._last_damage_kwargs = kwargs.copy()
        defender._last_original_damage = damage_result.base_damage  # 방어력 적용 전 원본 데미지
        
        # 치명적 피해 면역 확인 (last_stand 특성 등)
        final_hp_damage = damage_result.final_damage
        immunity_triggered = False
        if hasattr(defender, 'active_traits'):
            immunity_triggered, final_hp_damage = trait_manager.check_fatal_damage_immunity(
                defender, damage_result.final_damage
            )
        
        # HP 데미지 적용 (피해 감소는 take_damage 내부에서 처리)
        hp_damage = defender.take_damage(final_hp_damage)
        
        # [NEW] SCATTER 스택 증가 (피해 적중 시)
        # combat_manager가 아닌 여기서 처리하여 누락 방지
        is_scattered_hit = damage_result.details.get("is_scattered", False)
        if is_scattered_hit and hp_damage > 0:
            if hasattr(defender, "status_manager"):
                scatter_status = defender.status_manager.get_status(StatusType.SCATTER)
                if scatter_status:
                    scatter_status.stack_count += 1
                    self.logger.info(f"[SCATTER-STACK] {defender.name} 스택 증가: {scatter_status.stack_count - 1} -> {scatter_status.stack_count}")

            # 2. 콤보 게이지 증가 (원인 제공자에게)
            source = damage_result.details.get("scatter_source")
            if source and hasattr(source, "combo_gauge") and hasattr(source, "max_combo_gauge"):
                 # 데미지량의 8% (또는 scatter_ramp 만큼) 게이지 증가
                 scatter_ramp = damage_result.details.get("scatter_ramp", 0.08)
                 gain = int(hp_damage * scatter_ramp)
                 
                 if gain > 0:
                     old_gauge = source.combo_gauge
                     source.combo_gauge = min(source.max_combo_gauge, source.combo_gauge + gain)
                     actual_gain = source.combo_gauge - old_gauge
                     
                     if actual_gain > 0:
                         self.logger.info(f"[SCATTER-GAUGE] {source.name} 콤보 게이지 증가: +{actual_gain} (피해의 {int(scatter_ramp*100)}%, 현재: {source.combo_gauge}/{source.max_combo_gauge})")

        # 보호 효과 처리 후 원본 정보 제거
        if hasattr(defender, '_last_attacker'):
            delattr(defender, '_last_attacker')
        if hasattr(defender, '_last_damage_type'):
            delattr(defender, '_last_damage_type')
        if hasattr(defender, '_last_brv_points'):
            delattr(defender, '_last_brv_points')
        if hasattr(defender, '_last_hp_multiplier'):
            delattr(defender, '_last_hp_multiplier')
        if hasattr(defender, '_last_is_break'):
            delattr(defender, '_last_is_break')
        if hasattr(defender, '_last_damage_kwargs'):
            delattr(defender, '_last_damage_kwargs')
        if hasattr(defender, '_last_original_damage'):
            delattr(defender, '_last_original_damage')
        
        # 상처 데미지 적용 (HP 데미지의 일부가 상처로 전환)
        # WoundSystem의 이벤트 핸들러는 플래그로 인해 무시됨
        # 환영이 피해를 대신 받았을 때는 상처가 쌓이지 않음
        phantom_absorbed = getattr(defender, '_phantom_absorbed_damage', False)
        if phantom_absorbed:
            # 환영 피해 분산 플래그 제거
            delattr(defender, '_phantom_absorbed_damage')
            wound_damage = 0  # 상처 적용하지 않음
            self.logger.debug(f"[환술사] 환영이 피해 대신 받아 상처 적용하지 않음: {defender.name}")

        if hasattr(defender, "wound") and wound_damage > 0:
            # WoundSystem의 설정 사용
            from src.systems.wound_system import get_wound_system
            wound_system = get_wound_system()
            max_wound = int(defender.max_hp * wound_system.max_wound_percentage)
            if defender.wound + wound_damage > max_wound:
                wound_damage = max(0, max_wound - defender.wound)

            defender.wound += wound_damage
            self.logger.info(f"상처 축적: {defender.name} +{wound_damage} (총 {defender.wound}/{max_wound})")
        
        # 플래그 해제
        if hasattr(defender, "_wound_applied_this_turn"):
            defender._wound_applied_this_turn = False

        # 생명력/마력 흡수 적용 (lifesteal, mana_leech)
        from src.character.trait_effects import get_trait_effect_manager
        trait_manager = get_trait_effect_manager()
        
        lifesteal_rate = trait_manager.calculate_lifesteal(attacker)
        if lifesteal_rate > 0 and hp_damage > 0:
            heal_amount = int(hp_damage * lifesteal_rate)
            if hasattr(attacker, 'heal'):
                actual_heal = attacker.heal(heal_amount)
                if actual_heal > 0:
                    self.logger.info(f"[생명력 흡수] {attacker.name} HP 회복: +{actual_heal} ({lifesteal_rate * 100:.0f}%)")
        
        mana_leech_rate = trait_manager.calculate_mana_leech(attacker)
        if mana_leech_rate > 0 and hp_damage > 0:
            mp_amount = int(hp_damage * mana_leech_rate)
            if hasattr(attacker, 'restore_mp'):
                actual_mp = attacker.restore_mp(mp_amount)
                if actual_mp > 0:
                    self.logger.info(f"[마력 흡수] {attacker.name} MP 회복: +{actual_mp} ({mana_leech_rate * 100:.0f}%)")
        brv_consumed = attacker.current_brv
        self.logger.debug(f"[HP 공격] {attacker.name} BRV 소비: {brv_consumed}")
        
        attacker.current_brv = 0

        event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
            "character": attacker,
            "change": -brv_consumed,
            "current": 0,
            "max": attacker.max_brv
        })

        self.logger.info(
            f"HP 공격: {attacker.name} -> {defender.name}",
            {
                "brv_consumed": brv_consumed,
                "hp_damage": hp_damage,
                "wound_damage": wound_damage,
                "total_wound": defender.wound if hasattr(defender, "wound") else 0,
                "damage_type": damage_type,
                "stat_modifier": damage_result.variance,
                "is_critical": damage_result.is_critical,
                "is_break_bonus": is_defender_broken,
                "attacker_brv_after": attacker.current_brv
            }
        )

        # 세피로스 카운터 체크 (적이 피해를 받았을 때)
        defender_id = getattr(defender, 'enemy_id', None)
        self.logger.debug(f"[HP공격] defender: {defender.name}, enemy_id: {defender_id}, hp_damage: {hp_damage}")
        
        if defender_id == 'sephiroth' and hp_damage > 0:
            self.logger.debug(f"[세피로스 피격] 피해량: {hp_damage}, 공격자: {attacker.name}")
            from src.combat.combat_manager import get_combat_manager
            cm = get_combat_manager()
            
            # boss_gimmick_system이 없으면 자동 초기화
            if cm and not hasattr(cm, 'boss_gimmick_system'):
                from src.combat.boss_gimmicks import reset_boss_gimmicks, get_boss_gimmick_system
                reset_boss_gimmicks()
                cm.boss_gimmick_system = get_boss_gimmick_system()
                # 기존 표식 모두 제거 (이전 전투 잔여물)
                for ally in cm.allies:
                    if hasattr(ally, '_sephiroth_mark'):
                        delattr(ally, '_sephiroth_mark')
                    if hasattr(ally, '_cain_mark'):
                        delattr(ally, '_cain_mark')
                self.logger.debug("[보스 기믹] 시스템 자동 초기화 완료 (세피로스)")
            
            if cm and hasattr(cm, 'boss_gimmick_system'):
                # 직접 기믹 처리
                gimmick = cm.boss_gimmick_system
                counter_result = gimmick.on_sephiroth_damaged(defender, hp_damage, attacker)
                
                # UI에 스택 표시
                ui = getattr(cm, 'combat_ui', None)
                current_stack = gimmick.sephiroth_counter_stack
                if ui and hasattr(ui, 'add_message'):
                    if current_stack > 0:
                        ui.add_message(f"[광기] 스택 {current_stack}/3", (255, 150, 100))
                
                # 반격 실행
                if counter_result:
                    if ui and hasattr(ui, 'add_message'):
                        ui.add_message(counter_result.get('message', ''), (255, 50, 50))
                        ui.add_message(f"[{counter_result['skill_name']}] 반격!", (255, 100, 100))
                    
                    # 실제 반격 데미지 처리 (세피로스 공격력 vs 방어자 방어력)
                    target = counter_result['target']
                    
                    # 세피로스 공격력
                    seph_atk = getattr(defender, 'physical_attack', 100)
                    if hasattr(defender, 'stat_manager'):
                        from src.character.stats import Stats
                        seph_atk = defender.stat_manager.get_value(Stats.ATTACK)
                    
                    # 타겟 방어력
                    target_def = getattr(target, 'physical_defense', 50)
                    if hasattr(target, 'stat_manager'):
                        from src.character.stats import Stats
                        target_def = target.stat_manager.get_value(Stats.DEFENSE)
                    
                    if counter_result['is_hp_attack']:
                        # HP 공격: (공격력 / 방어력) × 250
                        if target_def > 0:
                            base_damage = (seph_atk / target_def) * 250
                        else:
                            base_damage = seph_atk * 2.5  # 방어력 0일 때 대체
                        counter_damage = int(base_damage)
                        counter_damage = max(10, counter_damage)  # 최소 10
                        
                        if hasattr(target, 'current_hp'):
                            counter_damage = min(counter_damage, target.current_hp)
                            target.current_hp -= counter_damage
                        
                        if ui and hasattr(ui, 'add_message'):
                            ui.add_message(f"[{counter_result['skill_name']}] {target.name}에게 {counter_damage} HP 피해!", (255, 100, 100))
                    else:
                        # BRV 공격: 공격력 기반
                        brv_damage = int(seph_atk * counter_result['damage_multiplier'])
                        counter_brv_result = self.brv_attack(defender, target, brv_damage)
                        if ui and hasattr(ui, 'add_message'):
                            ui.add_message(f"[{counter_result['skill_name']}] {target.name}에게 BRV 공격!", (255, 150, 100))
            
            # 공유 고통: 표식된 아군이 세피로스 공격 시 아군 전체 피해
            if cm and hasattr(cm, 'boss_gimmick_system'):
                marked_target = gimmick.sephiroth_marked_target
                has_mark_attr = hasattr(attacker, '_sephiroth_mark')
                
                # allies 가져오기 (여러 소스에서 시도)
                allies_list = getattr(cm, 'allies', None) or []
                if not allies_list and hasattr(cm, 'party'):
                    allies_list = getattr(cm.party, 'members', [])
                
                self.logger.info(f"[공유 고통 체크] 공격자: {attacker.name}, has_attr: {has_mark_attr}, allies: {len(allies_list)}명")
                
                if has_mark_attr and allies_list:
                    shared_result = gimmick.check_shared_pain(attacker, hp_damage, allies_list)
                    if shared_result and shared_result.get('damaged_allies'):
                        # UI에 표시
                        ui = getattr(cm, 'combat_ui', None)
                        if ui and hasattr(ui, 'add_message'):
                            ui.add_message(shared_result['message'], (255, 100, 100))
                            total_shared = sum(d['damage'] for d in shared_result['damaged_allies'])
                            ui.add_message(f"[공유 고통] 아군 전체 {total_shared} 피해!", (255, 50, 50))
                            for d in shared_result['damaged_allies']:
                                ui.add_message(f"  → {d['name']}에게 {d['damage']} 피해!", (255, 150, 150))

        return {
            "hp_damage": hp_damage,
            "wound_damage": wound_damage,
            "brv_consumed": brv_consumed,
            "is_break_bonus": is_defender_broken,
            "is_critical": damage_result.is_critical,
            "damage_type": damage_type,
            "stat_modifier": damage_result.variance,
            "is_scattered": damage_result.details.get("is_scattered", False),
            "scatter_source": damage_result.details.get("scatter_source")
        }

    def brv_hp_attack(
        self,
        attacker: Any,
        defender: Any,
        brv_damage: int,
        hp_multiplier: float = 1.0,
        damage_type: str = "physical"
    ) -> Dict[str, Any]:
        """
        BRV + HP 복합 공격

        BRV 공격 후 즉시 HP 공격을 수행합니다.

        Args:
            attacker: 공격자
            defender: 방어자
            brv_damage: BRV 데미지
            hp_multiplier: HP 배율
            damage_type: 데미지 타입 ("physical" 또는 "magical")

        Returns:
            공격 결과
        """
        # 1. BRV 공격
        brv_result = self.brv_attack(attacker, defender, brv_damage)

        # 2. HP 공격 (데미지 타입 전달)
        hp_result = self.hp_attack(attacker, defender, hp_multiplier, damage_type)

        return {
            **brv_result,
            **hp_result,
            "is_combo": True
        }

    def restore_brv(self, character: Any, amount: int) -> int:
        """
        BRV 회복

        Args:
            character: 캐릭터
            amount: 회복량

        Returns:
            실제 회복량
        """
        old_brv = character.current_brv
        character.current_brv = min(character.current_brv + amount, character.max_brv)
        actual_restore = character.current_brv - old_brv

        event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
            "character": character,
            "change": actual_restore,
            "current": character.current_brv,
            "max": character.max_brv
        })

        return actual_restore

    def reset_brv(self, character: Any) -> None:
        """BRV를 초기값으로 리셋"""
        old_brv = character.current_brv
        character.current_brv = character.init_brv

        event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
            "character": character,
            "change": character.current_brv - old_brv,
            "current": character.current_brv,
            "max": character.max_brv
        })

    def is_broken(self, character: Any) -> bool:
        """BREAK 상태 여부"""
        return getattr(character, "is_broken", False)

    def recover_int_brv(self, character: Any) -> int:
        """
        턴 시작 시 INT BRV 회복

        BRV가 0일 때 INT BRV로 회복합니다.

        Args:
            character: 캐릭터

        Returns:
            회복된 BRV 양
        """
        # BREAK 상태 확인
        if self.is_broken(character):
            # BREAK 턴 카운터 증가
            if not hasattr(character, "break_turn_count"):
                character.break_turn_count = 0
            character.break_turn_count += 1

            # BREAK 상태를 1턴 동안만 유지
            if character.break_turn_count >= 1:
                # BREAK 해제 및 BRV 회복 (init_brv 사용)
                init_brv_value = self.calculate_int_brv(character)  # 실제 초기 BRV 계산
                character.is_broken = False
                character.break_turn_count = 0
                character.current_brv = init_brv_value

                # [FIX] SCATTER 상태도 함께 해제
                if hasattr(character, 'status_manager'):
                    from src.combat.status_effects import StatusType
                    if character.status_manager.has_status(StatusType.SCATTER):
                        character.status_manager.remove_status(StatusType.SCATTER)
                        if hasattr(character, 'is_scattered'):
                            character.is_scattered = False
                        if hasattr(character, 'scatter_source'):
                            character.scatter_source = None
                        self.logger.info(f"{character.name} SCATTER 상태 해제 (BREAK 회복)")

                self.logger.info(f"{character.name} BREAK 해제 및 BRV 회복: {init_brv_value}")

                event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
                    "character": character,
                    "change": init_brv_value,
                    "current": character.current_brv,
                    "max": character.max_brv
                })

                return init_brv_value
            else:
                # 아직 BREAK 상태 유지
                self.logger.debug(f"{character.name} BREAK 상태 유지")
                return 0

        # 일반적인 경우: BRV가 0일 때만 회복 (init_brv 사용)
        if character.current_brv <= 0:
            init_brv_value = self.calculate_int_brv(character)  # 실제 초기 BRV 계산
            character.current_brv = init_brv_value

            event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
                "character": character,
                "change": init_brv_value,
                "current": character.current_brv,
                "max": character.max_brv
            })

            return init_brv_value

        return 0

    def clear_break_state(self, character: Any) -> None:
        """BREAK 상태 강제 해제"""
        if hasattr(character, "is_broken"):
            character.is_broken = False
        if hasattr(character, "break_turn_count"):
            character.break_turn_count = 0

        # [FIX] SCATTER 상태도 함께 해제
        if hasattr(character, 'status_manager'):
            from src.combat.status_effects import StatusType
            if character.status_manager.has_status(StatusType.SCATTER):
                character.status_manager.remove_status(StatusType.SCATTER)
        if hasattr(character, 'is_scattered'):
            character.is_scattered = False
        if hasattr(character, 'scatter_source'):
            character.scatter_source = None


# 전역 인스턴스
_brave_system: Optional[BraveSystem] = None


def get_brave_system() -> BraveSystem:
    """전역 Brave 시스템 인스턴스"""
    global _brave_system
    if _brave_system is None:
        _brave_system = BraveSystem()
    return _brave_system
