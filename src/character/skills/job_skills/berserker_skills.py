"""Berserker Skills - 광전사 스킬 (광기 역치 시스템)"""
from typing import Any, Optional
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.hp_cost import HPCost
from src.core.logger import get_logger

logger = get_logger("berserker_skills")


# ============================================================
# 피의 방패 효과 (BloodShieldEffect)
# ============================================================
class BloodShieldEffect(SkillEffect):
    """피의 방패: HP 75% 소비 → 소비량의 2배 보호막 생성 (5턴)"""
    
    def __init__(self, hp_consume_ratio: float = 0.75, shield_multiplier: float = 2.0, duration: int = 5):
        super().__init__(EffectType.GIMMICK)
        self.hp_consume_ratio = hp_consume_ratio
        self.shield_multiplier = shield_multiplier
        self.duration = duration
    
    def execute(self, user: Any, target: Any, context: Optional[dict] = None) -> EffectResult:
        """피의 방패 효과 실행"""
        # 현재 HP의 75% 계산
        hp_consumed = int(user.current_hp * self.hp_consume_ratio)
        
        # 최소 1 HP는 남김
        if user.current_hp - hp_consumed < 1:
            hp_consumed = user.current_hp - 1
        
        if hp_consumed <= 0:
            return EffectResult(
                effect_type=EffectType.GIMMICK,
                success=False,
                message="HP가 부족하여 피의 방패를 사용할 수 없습니다!"
            )
        
        # HP 소비
        user.current_hp -= hp_consumed
        
        # 보호막 생성 (소비량의 2배)
        shield_amount = int(hp_consumed * self.shield_multiplier)
        
        # 기존 보호막에 추가
        current_shield = getattr(user, 'current_shield', 0)
        user.current_shield = current_shield + shield_amount
        user.shield_duration = self.duration
        
        logger.info(f"[피의 방패] {user.name}: HP -{hp_consumed} → 보호막 +{shield_amount} (총 {user.current_shield}, {self.duration}턴)")
        
        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={"shield_gained": shield_amount, "hp_consumed": hp_consumed},
            message=f"🛡️ 피의 방패! HP -{hp_consumed} → 보호막 +{shield_amount} ({self.duration}턴)"
        )


# ============================================================
# 분노 폭발 효과 (RageEruptionEffect)
# ============================================================
class RageEruptionEffect(SkillEffect):
    """분노 폭발: 보호막 전부 소비 → 0.3배 고정 피해 + 100% 회복 (최대 70% max HP)"""
    
    def __init__(self, damage_multiplier: float = 0.3, heal_ratio: float = 1.0, max_heal_ratio: float = 0.7):
        super().__init__(EffectType.DAMAGE)
        self.damage_multiplier = damage_multiplier
        self.heal_ratio = heal_ratio
        self.max_heal_ratio = max_heal_ratio
    
    def execute(self, user: Any, target: Any, context: Optional[dict] = None) -> EffectResult:
        """분노 폭발 효과 실행"""
        # 보호막 확인
        shield_amount = getattr(user, 'current_shield', 0)
        
        if shield_amount <= 0:
            return EffectResult(
                effect_type=EffectType.DAMAGE,
                success=False,
                message="보호막이 없어 분노 폭발을 사용할 수 없습니다!"
            )
        
        # 보호막 전부 소비
        user.current_shield = 0
        user.shield_duration = 0
        
        # 고정 피해 계산 (보호막의 0.3배)
        fixed_damage = int(shield_amount * self.damage_multiplier)
        
        # 적 전체에게 피해 (context에서 enemies 가져오기)
        total_damage_dealt = 0
        enemies_hit = []
        
        combat_manager = context.get('combat_manager') if context else None
        if combat_manager and hasattr(combat_manager, 'enemies'):
            enemies = [e for e in combat_manager.enemies if getattr(e, 'is_alive', True) and getattr(e, 'current_hp', 0) > 0]
        elif isinstance(target, list):
            enemies = target
        else:
            enemies = [target] if target else []
        
        for enemy in enemies:
            if enemy and hasattr(enemy, 'current_hp'):
                # 고정 피해 적용 (방어 무시)
                actual_damage = min(fixed_damage, enemy.current_hp)
                enemy.current_hp = max(0, enemy.current_hp - fixed_damage)
                total_damage_dealt += actual_damage
                enemies_hit.append(getattr(enemy, 'name', '적'))
                
                # 사망 체크
                if enemy.current_hp <= 0:
                    enemy.is_alive = False
        
        # 회복량 계산 (피해량의 100%, 최대 HP의 70% 제한)
        heal_amount = int(total_damage_dealt * self.heal_ratio)
        max_heal = int(user.max_hp * self.max_heal_ratio)
        heal_amount = min(heal_amount, max_heal)
        
        # HP 회복
        old_hp = user.current_hp
        user.current_hp = min(user.max_hp, user.current_hp + heal_amount)
        actual_heal = user.current_hp - old_hp
        
        enemies_str = ", ".join(enemies_hit) if enemies_hit else "적"
        logger.info(f"[분노 폭발] {user.name}: 보호막 {shield_amount} 소비 → {enemies_str}에게 {fixed_damage} 피해, HP +{actual_heal} 회복")
        
        return EffectResult(
            effect_type=EffectType.DAMAGE,
            success=True,
            damage_dealt=total_damage_dealt,
            hp_damage=total_damage_dealt,
            heal_amount=actual_heal,
            gimmick_changes={"shield_consumed": shield_amount},
            message=f"💥 분노 폭발! 보호막 {shield_amount} 소비 → 전체 {fixed_damage} 피해, HP +{actual_heal} 회복"
        )


# ============================================================
# 절망의 힘 효과 (DesperateStrengthEffect)
# ============================================================
class DesperateStrengthEffect(SkillEffect):
    """절망의 힘: HP 낮을수록 공격력 증가 (HP 0%일 때 +50%), 8턴 + 매턴 HP 8% 감소"""
    
    def __init__(self, max_atk_bonus: float = 0.5, duration: int = 8, hp_drain_per_turn: float = 0.08):
        super().__init__(EffectType.BUFF)
        self.max_atk_bonus = max_atk_bonus  # HP 0%일 때 최대 공격력 보너스
        self.duration = duration
        self.hp_drain_per_turn = hp_drain_per_turn
    
    def execute(self, user: Any, target: Any, context: Optional[dict] = None) -> EffectResult:
        """절망의 힘 효과 실행"""
        from src.combat.status_effects import StatusEffect as CombatStatusEffect, StatusType
        
        # 현재 HP 비율 계산
        hp_ratio = user.current_hp / user.max_hp if user.max_hp > 0 else 1.0
        missing_hp_ratio = 1.0 - hp_ratio  # HP가 낮을수록 높아짐
        
        # 공격력 보너스 계산 (HP 0%일 때 +50%, 선형 비례)
        atk_bonus = self.max_atk_bonus * missing_hp_ratio
        
        # 버프 적용 (StatusManager 사용)
        if hasattr(user, 'status_manager'):
            # 절망의 힘 버프 생성
            desperate_buff = CombatStatusEffect(
                name="절망의 힘",
                status_type=StatusType.BUFF,
                duration=self.duration,
                intensity=atk_bonus
            )
            desperate_buff.metadata = {
                "desperate_strength": True,
                "base_atk_bonus": self.max_atk_bonus,
                "hp_drain_per_turn": self.hp_drain_per_turn
            }
            desperate_buff.stat_changes = {
                "physical_attack": atk_bonus,
                "magic_attack": atk_bonus
            }
            user.status_manager.add_status(desperate_buff)
        
        # active_buffs에도 추가 (레거시 호환성)
        if not hasattr(user, 'active_buffs'):
            user.active_buffs = {}
        user.active_buffs['desperate_strength'] = {
            'value': atk_bonus,
            'duration': self.duration,
            'max_bonus': self.max_atk_bonus,
            'hp_drain': self.hp_drain_per_turn
        }
        
        logger.info(f"[절망의 힘] {user.name}: 공격력 +{int(atk_bonus*100)}% ({self.duration}턴, 매턴 HP -{int(self.hp_drain_per_turn*100)}%)")
        
        return EffectResult(
            effect_type=EffectType.BUFF,
            success=True,
            gimmick_changes={"desperate_strength_bonus": atk_bonus},
            message=f"🗡️ 절망의 힘! 공격력 +{int(atk_bonus*100)}% ({self.duration}턴, 매턴 HP -{int(self.hp_drain_per_turn*100)}%)"
        )


def create_berserker_skills():
    """광전사 13개 스킬 생성 (광기 역치 시스템 - HP↓ → 광기↑)
    
    추가된 스킬:
    - 피의 방패: HP 75% 소비 → 소비량의 2배 보호막 생성 (5턴)
    - 분노 폭발: 보호막 전부 소비 → 0.3배 고정 피해 + 100% 회복 (최대 70% max HP)
    - 절망의 힘: HP 낮을수록 공격력 증가 (최대 +50%), 8턴 + 매턴 HP 8% 감소
    """

    # 1. 기본 BRV: 베기
    slash = Skill("berserker_slash", "베기", "BRV 피해를 주는 기본 공격")
    slash.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="physical")
    ]
    slash.costs = []
    slash.sfx = ("combat", "attack_physical")  # 베기
    slash.metadata = {}

    # 2. 기본 HP: 강타
    smash = Skill("berserker_smash", "강타", "HP 피해를 주는 강력한 일격")
    smash.effects = [
        DamageEffect(DamageType.HP, 1.3, stat_type="physical")
    ]
    smash.costs = []
    smash.sfx = ("combat", "damage_high")  # 강타
    smash.metadata = {}

    # 3. 무모한 일격 (HP 소모로 강력한 공격, 광기↑)
    reckless_strike = Skill("berserker_reckless_strike", "무모한 일격",
                           "HP 20% 소모, 광기↑로 강력한 공격")
    reckless_strike.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2, stat_type="physical",
                    conditional_bonus={"condition": "in_berserker_mode", "multiplier": 1.25}),
    ]
    reckless_strike.costs = [MPCost(4), HPCost(percentage=0.20)]
    reckless_strike.sfx = ("combat", "critical")  # 무모한 일격
    reckless_strike.metadata = {"hp_cost_percent": 0.20}

    # 4. 피의 방패 (HP 75% 소비 → 보호막 생성)
    blood_shield = Skill("berserker_blood_shield", "피의 방패",
                        "현재 HP의 75%를 소비하여 소비량의 2배만큼 보호막 생성 (5턴)")
    blood_shield.effects = [
        BloodShieldEffect(hp_consume_ratio=0.75, shield_multiplier=2.0, duration=5)
    ]
    blood_shield.costs = [MPCost(8)]
    blood_shield.target_type = "self"
    blood_shield.sfx = ("character", "status_buff")  # 방패 효과음
    blood_shield.metadata = {"shield_skill": True, "hp_sacrifice": True}

    # 5. 자해 (HP 20% 감소 → 광기 대폭 증가, 공격력 버프)
    self_harm = Skill("berserker_self_harm", "자해",
                     "HP 20% 감소, 3턴간 공격력 +50%")
    self_harm.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=3, target="self")
    ]
    self_harm.costs = [MPCost(3), HPCost(percentage=0.20)]
    self_harm.target_type = "self"
    self_harm.sfx = ("combat", "damage_high")  # 자해
    self_harm.metadata = {"hp_cost_percent": 0.20, "madness_gain": "high"}

    # 6. 전투의 함성 (광역 디버프 + 자신 버프)
    battle_cry = Skill("berserker_battle_cry", "전투의 함성",
                      "적 전체 위축, 자신 속도 +40%")
    battle_cry.effects = [
        DamageEffect(DamageType.BRV, 1.2, stat_type="physical"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.3, duration=2),
        BuffEffect(BuffType.SPEED_UP, 0.4, duration=3, target="self")
    ]
    battle_cry.costs = [MPCost(6)]
    battle_cry.target_type = "all_enemies"
    battle_cry.is_aoe = True
    battle_cry.sfx = ("character", "status_debuff")  # 전투의 함성
    battle_cry.metadata = {"aoe": True}

    # 7. 분노 폭발 (보호막 소비 → 전체 피해 + 회복)
    rage_eruption = Skill("berserker_rage_eruption", "분노 폭발",
                         "보호막을 모두 소비하여 0.3배 고정 피해를 적 전체에게, 피해량의 100% 회복 (최대 HP 70%)")
    rage_eruption.effects = [
        RageEruptionEffect(damage_multiplier=0.3, heal_ratio=1.0, max_heal_ratio=0.7)
    ]
    rage_eruption.costs = [MPCost(10)]
    rage_eruption.target_type = "all_enemies"
    rage_eruption.is_aoe = True
    rage_eruption.sfx = ("skill", "explosion")  # 폭발 효과음
    rage_eruption.metadata = {"aoe": True, "shield_consume": True, "fixed_damage": True}

    # 8. 피의 분노 (광기에 비례한 공격)
    blood_rage = Skill("berserker_blood_rage", "피의 분노",
                      "광기(HP 손실)에 비례한 강력한 공격")
    blood_rage.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="physical",
                    # HP 손실 비율에 비례 (HP 30%일 때 광기 70 → +140% 피해)
                    gimmick_bonus={"field": "madness", "multiplier": 0.02})
    ]
    blood_rage.costs = [MPCost(7)]
    blood_rage.sfx = ("combat", "critical")  # 피의 분노
    blood_rage.metadata = {"madness_scaling": True}

    # 9. 필사의 공격 (HP 30% 이하일 때 극대 피해)
    desperate_assault = Skill("berserker_desperate_assault", "필사의 공격",
                             "HP 30% 이하 시 극대 피해 (조건부 강화)")
    desperate_assault.effects = [
        DamageEffect(DamageType.BRV_HP, 3.5, stat_type="physical",
                    conditional_bonus={"condition": "hp_below_30", "multiplier": 1.8})
    ]
    desperate_assault.costs = [MPCost(9)]
    desperate_assault.sfx = ("combat", "damage_high")  # 필사의 공격
    desperate_assault.metadata = {"requires_low_hp": True}

    # 10. 절망의 힘 (HP 낮을수록 공격력 증가 + HP 감소)
    desperate_strength = Skill("berserker_desperate_strength", "절망의 힘",
                              "HP가 낮을수록 공격력 증가 (최대 +50%), 8턴 지속, 매턴 HP 8% 감소")
    desperate_strength.effects = [
        DesperateStrengthEffect(max_atk_bonus=0.5, duration=8, hp_drain_per_turn=0.08)
    ]
    desperate_strength.costs = [MPCost(8)]
    desperate_strength.target_type = "self"
    desperate_strength.sfx = ("character", "status_buff")  # 버프 효과음
    desperate_strength.metadata = {"hp_scaling": True, "hp_drain": True}

    # 11. 치유의 포효 (HP 30% 회복 + BRV 50% 회복)
    healing_roar = Skill("berserker_healing_roar", "치유의 포효",
                        "HP 30% 회복 + BRV 50% 회복 (광기↓)")
    healing_roar.effects = [
        HealEffect(percentage=0.56),  # 치유의 포효 (0.48 → 0.56 증가)
        # BRV 회복 효과 추가 필요 (구현 시)
    ]
    healing_roar.costs = [MPCost(9)]
    healing_roar.target_type = "self"
    healing_roar.sfx = ("character", "hp_heal")  # 치유의 포효
    healing_roar.metadata = {"hp_heal": 0.30, "brv_heal": 0.50}

    # 12. 통제된 광기 (HP를 50%로 조정 → 광기 50 유지)
    controlled_fury = Skill("berserker_controlled_fury", "통제된 광기",
                           "HP를 50%로 설정 (광기 최적 구간)")
    controlled_fury.effects = [
        # HP를 최대 HP의 50%로 설정하는 특수 효과
        HealEffect(set_percent=0.50)  # HP를 50%로 설정
    ]
    controlled_fury.costs = [MPCost(10)]
    controlled_fury.target_type = "self"
    controlled_fury.sfx = ("character", "status_buff")  # 통제된 광기
    controlled_fury.metadata = {"hp_set_percent": 0.50, "madness_control": True}

    # 13. 궁극기: 광란의 힘 (HP 1%로 강제 → 광기 100, 폭주)
    ultimate = Skill("berserker_ultimate", "광란의 힘",
                    "HP를 1%로 감소, 광기 100 폭주 상태 진입!")
    ultimate.effects = [
        # HP를 1%로 강제 감소
        DamageEffect(DamageType.BRV, 3.8, stat_type="physical"),
        DamageEffect(DamageType.HP, 3.3, stat_type="physical"),
        BuffEffect(BuffType.ATTACK_UP, 2.0, duration=3, target="self"),  # 공격력 +200%
        BuffEffect(BuffType.SPEED_UP, 1.0, duration=3, target="self")   # 속도 +100%
    ]
    ultimate.costs = [MPCost(30), HPCost(percentage=0.99)]  # HP 99% 소모 (1% 남김)
    ultimate.is_ultimate = True
    ultimate.cooldown = 15  # 궁극기 쿨타임 15턴
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.metadata = {"ultimate": True, "rampage": True, "hp_to_1_percent": True}

    skills = [slash, smash, reckless_strike, blood_shield, self_harm, battle_cry,
              rage_eruption, blood_rage, desperate_assault, desperate_strength,
              healing_roar, controlled_fury, ultimate]

    # 팀워크 스킬: 광란의 일격
    teamwork = TeamworkSkill(
        "berserker_teamwork",
        "광란의 일격",
        "단일 대상 BRV+HP (1.6x → HP 변환) + 광기 +20 + 자신 공격력 1.2배 (2턴)",
        gauge_cost=100)
    teamwork.effects = [
        DamageEffect(DamageType.BRV, 1.6),  # BRV 공격 1.6x
        DamageEffect(DamageType.HP, 1.0),  # HP 변환
        GimmickEffect(GimmickOperation.ADD, "madness", 20, max_value=100),  # 광기 +20
        BuffEffect(BuffType.ATTACK_UP, 0.2, duration=2, target="self"),  # 자신 공격력 1.2배 (2턴)
    ]
    teamwork.target_type = "enemy"
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {"teamwork": True, "chain": True, "berserker": True}
    skills.append(teamwork)

    return skills

def register_berserker_skills(skill_manager):
    """광전사 스킬 등록"""
    skills = create_berserker_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 광란의 일격
    return [s.skill_id for s in skills]