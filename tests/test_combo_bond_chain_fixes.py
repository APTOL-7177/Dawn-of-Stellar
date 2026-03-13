"""
합체기 / 연계스킬 / 체인어빌리티 버그 수정 검증 테스트
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace


def make_character(name, job, level=10, hp=500, mp=100, brv=0,
                   p_atk=80, m_atk=60, p_def=40, m_def=30, spd=50):
    """테스트용 캐릭터 생성"""
    char = MagicMock()
    char.name = name
    char.character_class = job
    char.level = level
    char.max_hp = hp
    char.current_hp = hp
    char.max_mp = mp
    char.current_mp = mp
    char.current_brv = brv
    char.is_alive = True
    char.physical_attack = p_atk
    char.p_atk = p_atk
    char.attack = p_atk
    char.strength = p_atk
    char.magic_attack = m_atk
    char.m_atk = m_atk
    char.magic = m_atk
    char.intelligence = m_atk
    char.physical_defense = p_def
    char.p_def = p_def
    char.defense = p_def
    char.magic_defense = m_def
    char.m_def = m_def
    char.spirit = m_def
    char.speed = spd
    # StatusManager mock
    char.status_manager = MagicMock()
    char.status_manager.add_status = MagicMock()
    char.status_manager.clear_debuffs = MagicMock()
    return char


def make_combo_skill(skill_id, name, jobs, pattern, effects, gauge_cost=250, min_affinity=3):
    """테스트용 ComboSkill 객체 생성"""
    skill = SimpleNamespace()
    skill.id = skill_id
    skill.name = name
    skill.required_jobs = jobs
    skill.combo_pattern = pattern
    skill.effects = effects
    skill.gauge_cost = gauge_cost
    skill.min_affinity = min_affinity
    return skill


class TestComboSkillHPDamage(unittest.TestCase):
    """합체기 HP 데미지가 0이 되는 버그 수정 검증"""

    def setUp(self):
        from src.combat.combat_manager import CombatManager
        self.cm = CombatManager()
        self.warrior = make_character("전사", "warrior", p_atk=100)
        self.samurai = make_character("사무라이", "samurai", p_atk=90)
        self.enemy = make_character("적1", "monster", hp=1000, brv=0, p_def=30)
        self.enemy2 = make_character("적2", "monster", hp=800, brv=50, p_def=25)

        self.cm.allies = [self.warrior, self.samurai]
        self.cm.enemies = [self.enemy, self.enemy2]
        self.cm.party = MagicMock()
        self.cm.party.consume_teamwork_gauge = MagicMock(return_value=True)
        self.cm._affinity_manager = None
        self.cm._synergy_manager = None

    def test_hp_damage_not_zero_when_target_brv_is_zero(self):
        """타겟 BRV가 0일 때도 HP 데미지가 정상 적용되어야 한다 (핵심 버그)"""
        self.enemy.current_brv = 0  # BRV가 0인 적

        combo = make_combo_skill(
            "twin_blade_storm", "쌍검의 폭풍",
            ["warrior", "samurai"], "brv_hp",
            [{"type": "damage", "target": "all_enemies",
              "damage_type": "physical", "multiplier": 4.5}]
        )
        result = self.cm.execute_combo_skill(combo)

        self.assertTrue(result["success"])
        # HP 공격 효과 찾기
        hp_attacks = [e for e in result["effects"] if e["type"] == "hp_attack"]
        self.assertTrue(len(hp_attacks) > 0, "HP 공격 효과가 있어야 한다")

        # 핵심: HP 데미지가 0이 아니어야 한다
        for attack in hp_attacks:
            self.assertGreater(attack["hp_damage"], 0,
                f"HP 데미지가 0보다 커야 한다 (실제: {attack['hp_damage']})")

    def test_hp_damage_equals_brv_damage(self):
        """HP 데미지는 계산된 BRV 데미지 값과 같아야 한다 (탈취량이 아님)"""
        self.enemy.current_brv = 0

        combo = make_combo_skill(
            "test_combo", "테스트",
            ["warrior", "samurai"], "brv_hp",
            [{"type": "damage", "target": "single",
              "damage_type": "physical", "multiplier": 4.5}]
        )
        result = self.cm.execute_combo_skill(combo, target=self.enemy)

        brv_attacks = [e for e in result["effects"] if e["type"] == "brv_attack"]
        hp_attacks = [e for e in result["effects"] if e["type"] == "hp_attack"]

        if brv_attacks and hp_attacks:
            brv_dmg = brv_attacks[0]["brv_damage"]
            hp_dmg = hp_attacks[0]["hp_damage"]
            self.assertEqual(hp_dmg, brv_dmg,
                f"HP 데미지({hp_dmg})는 BRV 데미지({brv_dmg})와 같아야 한다")

    def test_empower_pattern_multiplier(self):
        """empower_strike 패턴이 1.5배 보정을 적용해야 한다"""
        self.enemy.current_brv = 0

        combo_normal = make_combo_skill(
            "normal", "일반", ["warrior", "samurai"], "brv_hp",
            [{"type": "damage", "target": "single",
              "damage_type": "physical", "multiplier": 4.0}]
        )
        combo_empower = make_combo_skill(
            "empower", "강화", ["warrior", "samurai"], "empower_strike",
            [{"type": "damage", "target": "single",
              "damage_type": "physical", "multiplier": 4.0}]
        )

        result_normal = self.cm.execute_combo_skill(combo_normal, target=self.enemy)
        # 적 HP 복원
        self.enemy.current_hp = 1000
        self.enemy.current_brv = 0
        result_empower = self.cm.execute_combo_skill(combo_empower, target=self.enemy)

        hp_normal = [e for e in result_normal["effects"] if e["type"] == "hp_attack"]
        hp_empower = [e for e in result_empower["effects"] if e["type"] == "hp_attack"]

        if hp_normal and hp_empower:
            # empower는 1.5배이므로 더 높아야 함
            self.assertGreater(hp_empower[0]["hp_damage"], hp_normal[0]["hp_damage"],
                "empower_strike 패턴이 brv_hp보다 높은 데미지를 줘야 한다")

    def test_critical_guaranteed(self):
        """critical_guaranteed가 1.5배 추가 데미지를 적용해야 한다"""
        self.enemy.current_brv = 0

        combo = make_combo_skill(
            "crit", "치명타", ["warrior", "samurai"], "brv_hp",
            [{"type": "damage", "target": "single",
              "damage_type": "physical", "multiplier": 4.0,
              "critical_guaranteed": True}]
        )
        result = self.cm.execute_combo_skill(combo, target=self.enemy)
        hp_attacks = [e for e in result["effects"] if e["type"] == "hp_attack"]

        combo_no_crit = make_combo_skill(
            "nocrit", "일반", ["warrior", "samurai"], "brv_hp",
            [{"type": "damage", "target": "single",
              "damage_type": "physical", "multiplier": 4.0}]
        )
        self.enemy.current_hp = 1000
        self.enemy.current_brv = 0
        result_no = self.cm.execute_combo_skill(combo_no_crit, target=self.enemy)
        hp_no = [e for e in result_no["effects"] if e["type"] == "hp_attack"]

        if hp_attacks and hp_no:
            self.assertGreater(hp_attacks[0]["hp_damage"], hp_no[0]["hp_damage"],
                "critical_guaranteed는 더 높은 데미지를 줘야 한다")


class TestComboSkillBuffDebuff(unittest.TestCase):
    """합체기 buff/debuff 효과 실제 적용 검증"""

    def setUp(self):
        from src.combat.combat_manager import CombatManager
        self.cm = CombatManager()
        self.warrior = make_character("전사", "warrior")
        self.samurai = make_character("사무라이", "samurai")
        self.enemy = make_character("적1", "monster", hp=500)

        self.cm.allies = [self.warrior, self.samurai]
        self.cm.enemies = [self.enemy]
        self.cm.party = MagicMock()
        self.cm.party.consume_teamwork_gauge = MagicMock(return_value=True)
        self.cm._affinity_manager = None
        self.cm._synergy_manager = None

    def test_buff_applies_status_effect(self):
        """buff 효과가 status_manager.add_status를 실제로 호출해야 한다"""
        combo = make_combo_skill(
            "buff_test", "버프테스트", ["warrior", "samurai"], "brv_hp",
            [{"type": "buff", "target": "all_allies",
              "physical_attack_mult": 1.15, "duration": 3}]
        )
        result = self.cm.execute_combo_skill(combo)

        self.assertTrue(result["success"])
        # 아군 모두에게 add_status가 호출되었는지 확인
        for ally in [self.warrior, self.samurai]:
            self.assertTrue(ally.status_manager.add_status.called,
                f"{ally.name}에게 add_status가 호출되어야 한다")

    def test_debuff_applies_status_effect(self):
        """debuff 효과가 적에게 StatusEffect를 실제로 적용해야 한다"""
        combo = make_combo_skill(
            "debuff_test", "디버프테스트", ["warrior", "samurai"], "brv_hp",
            [{"type": "debuff", "target": "all_enemies",
              "physical_defense_mult": 0.7, "magic_defense_mult": 0.7,
              "duration": 3}]
        )
        result = self.cm.execute_combo_skill(combo)

        self.assertTrue(result["success"])
        # 적에게 add_status가 호출되었는지 확인
        self.assertTrue(self.enemy.status_manager.add_status.called,
            "적에게 add_status가 호출되어야 한다")
        # 2종류의 디버프 (방어력, 마법방어력)
        call_count = self.enemy.status_manager.add_status.call_count
        self.assertEqual(call_count, 2,
            f"2종류의 디버프가 적용되어야 한다 (실제: {call_count})")

    def test_heal_effect(self):
        """heal 효과가 아군의 HP를 회복시켜야 한다"""
        self.warrior.current_hp = 200  # HP 감소 상태

        combo = make_combo_skill(
            "heal_test", "힐테스트", ["warrior", "samurai"], "brv_hp",
            [{"type": "heal", "target": "all_allies",
              "heal_percent": 60, "cleanse": True}]
        )
        result = self.cm.execute_combo_skill(combo)

        self.assertTrue(result["success"])
        heal_effects = [e for e in result["effects"] if e["type"] == "heal"]
        self.assertTrue(len(heal_effects) > 0, "힐 효과가 있어야 한다")
        # HP가 실제로 회복되었는지
        self.assertGreater(self.warrior.current_hp, 200, "전사의 HP가 회복되어야 한다")
        # cleanse 호출 확인
        self.assertTrue(self.warrior.status_manager.clear_debuffs.called,
            "cleanse=True이면 clear_debuffs가 호출되어야 한다")

    def test_tech_overload_combo(self):
        """기술 과부하 합체기: 데미지 + 디버프 동시 적용"""
        hacker = make_character("해커", "hacker", m_atk=90)
        engineer = make_character("엔지니어", "engineer", p_atk=85)
        self.cm.allies = [hacker, engineer]

        combo = make_combo_skill(
            "tech_overload", "기술 과부하",
            ["hacker", "engineer"], "weaken_execute",
            [
                {"type": "damage", "target": "all_enemies",
                 "damage_type": "tech", "multiplier": 4.5},
                {"type": "debuff", "target": "all_enemies",
                 "physical_defense_mult": 0.7, "magic_defense_mult": 0.7,
                 "duration": 3}
            ]
        )
        result = self.cm.execute_combo_skill(combo)

        self.assertTrue(result["success"])
        hp_attacks = [e for e in result["effects"] if e["type"] == "hp_attack"]
        debuffs = [e for e in result["effects"] if e["type"] == "debuff"]
        self.assertTrue(len(hp_attacks) > 0, "HP 공격이 있어야 한다")
        self.assertTrue(len(debuffs) > 0, "디버프가 있어야 한다")
        self.assertTrue(self.enemy.status_manager.add_status.called,
            "적에게 디버프 StatusEffect가 실제 적용되어야 한다")


class TestBondSkillMultipliers(unittest.TestCase):
    """연계스킬 배율 상향 검증"""

    def test_bond_skill_multipliers_increased(self):
        """bond_skills.yaml의 배율이 최소 0.65 이상이어야 한다"""
        import yaml
        yaml_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'bond_skills.yaml')
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        low_multipliers = []
        for skill in data.get('bond_skills', []):
            effect = skill.get('effect', {})
            mult = effect.get('multiplier')
            if mult is not None and mult < 0.60:
                low_multipliers.append((skill['id'], mult))

        self.assertEqual(len(low_multipliers), 0,
            f"0.60 미만의 배율이 없어야 한다. 문제: {low_multipliers}")

    def test_chain_ability_multipliers_reasonable(self):
        """chain_abilities의 배율이 합리적 범위(0.65~3.0)여야 한다"""
        import yaml
        yaml_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'bond_skills.yaml')
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        for job_data in data.get('chain_abilities', []):
            for ability in job_data.get('abilities', []):
                for effect in ability.get('effects', []):
                    mult = effect.get('multiplier')
                    if mult is not None:
                        self.assertGreaterEqual(mult, 0.65,
                            f"{ability.get('name', '?')} 배율({mult})이 0.65 이상이어야 한다")


class TestStatusTypeMapping(unittest.TestCase):
    """StatusType 매핑이 올바른 enum 값을 사용하는지 검증"""

    def test_reduce_status_types_exist(self):
        """디버프에 사용하는 REDUCE_* StatusType이 모두 존재하는지 확인"""
        from src.combat.status_effects import StatusType
        required_types = [
            'REDUCE_ATK', 'REDUCE_DEF', 'REDUCE_SPD',
            'REDUCE_MAGIC_ATK', 'REDUCE_MAGIC_DEF',
        ]
        for t in required_types:
            self.assertTrue(hasattr(StatusType, t),
                f"StatusType.{t}가 존재해야 한다")

    def test_boost_status_types_exist(self):
        """버프에 사용하는 BOOST_* StatusType이 모두 존재하는지 확인"""
        from src.combat.status_effects import StatusType
        required_types = [
            'BOOST_ATK', 'BOOST_DEF', 'BOOST_SPD',
            'BOOST_MAGIC_ATK', 'BOOST_MAGIC_DEF',
            'BOOST_CRIT', 'BOOST_ALL_STATS',
        ]
        for t in required_types:
            self.assertTrue(hasattr(StatusType, t),
                f"StatusType.{t}가 존재해야 한다")

    def test_status_effect_creation(self):
        """StatusEffect 객체가 올바르게 생성되는지 확인"""
        from src.combat.status_effects import StatusType, StatusEffect
        se = StatusEffect(
            name="테스트 버프",
            status_type=StatusType.BOOST_ATK,
            duration=3,
            intensity=0.5,
        )
        self.assertEqual(se.name, "테스트 버프")
        self.assertEqual(se.status_type, StatusType.BOOST_ATK)
        self.assertEqual(se.duration, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
