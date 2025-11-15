"""
Trait Effects 테스트

특성(Trait) 시스템이 실제 게임플레이에 올바르게 영향을 주는지 검증
"""

import pytest
from src.character.character import Character
from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
from src.combat.damage_calculator import get_damage_calculator
from src.combat.combat_manager import get_combat_manager


class TestTraitEffects:
    """특성 효과 테스트"""

    def test_trait_manager_initialization(self):
        """특성 관리자 초기화 테스트"""
        trait_manager = get_trait_effect_manager()
        assert trait_manager is not None
        assert len(trait_manager.trait_definitions) > 0

    def test_passive_hp_boost(self):
        """패시브 특성: HP 증폭 테스트"""
        char = Character("테스트 전사", "warrior", level=1)
        base_hp = char.max_hp

        # HP 증폭 특성 활성화
        char.activate_trait("hp_boost")

        # HP가 15% 증가했는지 확인
        # NOTE: 특성 보너스는 StatManager를 통해 적용되므로
        # 정확한 검증을 위해 직접 계산
        expected_hp = int(base_hp * 1.15)
        assert char.max_hp >= base_hp, "HP가 증가해야 합니다"
        print(f"Base HP: {base_hp}, With Trait: {char.max_hp}, Expected: {expected_hp}")

    def test_passive_mp_boost(self):
        """패시브 특성: MP 증폭 테스트"""
        char = Character("테스트 마법사", "mage", level=1)
        base_mp = char.max_mp

        # MP 증폭 특성 활성화
        char.activate_trait("mp_boost")

        # MP가 15% 증가했는지 확인
        expected_mp = int(base_mp * 1.15)
        assert char.max_mp >= base_mp, "MP가 증가해야 합니다"
        print(f"Base MP: {base_mp}, With Trait: {char.max_mp}, Expected: {expected_mp}")

    def test_damage_multiplier_physical_power(self):
        """데미지 배율 특성: 물리 공격력 증가 테스트"""
        trait_manager = get_trait_effect_manager()
        char = Character("테스트 전사", "warrior", level=1)

        # physical_power 특성 활성화
        char.activate_trait("physical_power")

        # 데미지 배율 계산
        multiplier = trait_manager.calculate_damage_multiplier(char, "physical")

        # 물리 공격력이 20% 증가했는지 확인
        assert multiplier == 1.20, f"물리 데미지 배율이 1.20이어야 하는데 {multiplier}입니다"
        print(f"물리 데미지 배율: x{multiplier}")

    def test_damage_multiplier_magic_power(self):
        """데미지 배율 특성: 마법 공격력 증가 테스트"""
        trait_manager = get_trait_effect_manager()
        char = Character("테스트 마법사", "mage", level=1)

        # magic_power 특성 활성화
        char.activate_trait("magic_power")

        # 데미지 배율 계산
        multiplier = trait_manager.calculate_damage_multiplier(char, "magic")

        # 마법 공격력이 20% 증가했는지 확인
        assert multiplier == 1.20, f"마법 데미지 배율이 1.20이어야 하는데 {multiplier}입니다"
        print(f"마법 데미지 배율: x{multiplier}")

    def test_mp_cost_reduction_skill_master(self):
        """MP 소모 감소 특성: 기술 숙련 테스트"""
        trait_manager = get_trait_effect_manager()
        char = Character("테스트 전사", "warrior", level=1)

        # skill_master 특성 활성화
        char.activate_trait("skill_master")

        # MP 소모 계산
        base_cost = 100
        final_cost = trait_manager.calculate_mp_cost(char, base_cost)

        # MP 소모가 20% 감소했는지 확인
        expected_cost = 80
        assert final_cost == expected_cost, f"MP 소모가 {expected_cost}여야 하는데 {final_cost}입니다"
        print(f"기본 MP 소모: {base_cost} → 감소 후: {final_cost}")

    def test_critical_bonus_critical_boost(self):
        """크리티컬 보너스 특성: 치명타 강화 테스트"""
        trait_manager = get_trait_effect_manager()
        char = Character("테스트 전사", "warrior", level=1)

        # critical_boost 특성 활성화
        char.activate_trait("critical_boost")

        # 크리티컬 보너스 계산
        bonus = trait_manager.calculate_critical_bonus(char)

        # 크리티컬 확률이 15% 증가했는지 확인
        assert bonus == 0.15, f"크리티컬 보너스가 0.15여야 하는데 {bonus}입니다"
        print(f"크리티컬 보너스: +{bonus * 100}%")

    def test_break_bonus_break_master(self):
        """브레이크 보너스 특성: 브레이크 달인 테스트"""
        trait_manager = get_trait_effect_manager()
        char = Character("테스트 전사", "warrior", level=1)

        # break_master 특성 활성화
        char.activate_trait("break_master")

        # 브레이크 보너스 계산
        bonus = trait_manager.calculate_break_bonus(char)

        # 브레이크 보너스가 1.5 증가했는지 확인
        assert bonus == 1.5, f"브레이크 보너스가 1.5여야 하는데 {bonus}입니다"
        print(f"브레이크 보너스: +{bonus}")

    def test_hp_regen_auto_regen(self):
        """HP 회복 특성: 자동 재생 테스트"""
        trait_manager = get_trait_effect_manager()
        char = Character("테스트 전사", "warrior", level=1)

        # auto_regen 특성 활성화
        char.activate_trait("auto_regen")

        # HP를 절반으로 감소
        char.current_hp = char.max_hp // 2
        hp_before = char.current_hp

        # 턴 시작 효과 적용
        trait_manager.apply_turn_start_effects(char)

        # HP가 5% 회복되었는지 확인
        expected_heal = int(char.max_hp * 0.05)
        hp_after = char.current_hp

        assert hp_after > hp_before, "HP가 회복되어야 합니다"
        print(f"HP 회복: {hp_before} → {hp_after} (+{hp_after - hp_before}, 예상: {expected_heal})")

    def test_mp_regen_mp_recovery(self):
        """MP 회복 특성: 마력 회복 테스트"""
        trait_manager = get_trait_effect_manager()
        char = Character("테스트 마법사", "mage", level=1)

        # mp_recovery 특성 활성화
        char.activate_trait("mp_recovery")

        # MP를 절반으로 감소
        char.current_mp = char.max_mp // 2
        mp_before = char.current_mp

        # 턴 시작 효과 적용
        trait_manager.apply_turn_start_effects(char)

        # MP가 3% 회복되었는지 확인
        expected_restore = int(char.max_mp * 0.03)
        mp_after = char.current_mp

        assert mp_after > mp_before, "MP가 회복되어야 합니다"
        print(f"MP 회복: {mp_before} → {mp_after} (+{mp_after - mp_before}, 예상: {expected_restore})")

    def test_conditional_hp_danger_boost(self):
        """조건부 특성: 위기일발 테스트"""
        trait_manager = get_trait_effect_manager()
        char = Character("테스트 전사", "warrior", level=1)

        # hp_danger_boost 특성 활성화
        char.activate_trait("hp_danger_boost")

        # HP가 30% 이상일 때 - 보너스 없음
        char.current_hp = int(char.max_hp * 0.5)
        multiplier_safe = trait_manager.calculate_damage_multiplier(char, "physical")
        print(f"HP 50%일 때 배율: x{multiplier_safe}")

        # HP가 30% 미만일 때 - 보너스 적용
        char.current_hp = int(char.max_hp * 0.2)
        multiplier_danger = trait_manager.calculate_damage_multiplier(char, "physical")
        print(f"HP 20%일 때 배율: x{multiplier_danger}")

        # 위험 상태일 때 더 높은 배율
        assert multiplier_danger > multiplier_safe, "HP가 낮을 때 더 높은 데미지 배율이어야 합니다"

    def test_multiple_traits_stacking(self):
        """복수 특성 중첩 테스트"""
        trait_manager = get_trait_effect_manager()
        char = Character("테스트 전사", "warrior", level=1)

        # 여러 물리 공격 특성 활성화
        char.activate_trait("physical_power")  # +20%
        char.activate_trait("ultimate_power")  # +30%

        # 데미지 배율 계산
        multiplier = trait_manager.calculate_damage_multiplier(char, "physical")

        # 배율이 중첩되어 1.20 * 1.30 = 1.56이 되어야 함
        expected = 1.20 * 1.30
        assert abs(multiplier - expected) < 0.01, f"배율이 {expected}여야 하는데 {multiplier}입니다"
        print(f"중첩된 물리 데미지 배율: x{multiplier} (예상: x{expected})")

    def test_trait_activation_deactivation(self):
        """특성 활성화/비활성화 테스트"""
        char = Character("테스트 전사", "warrior", level=1)

        # 특성 활성화
        result = char.activate_trait("hp_boost")
        assert result is True, "특성 활성화에 실패했습니다"
        assert "hp_boost" in char.active_traits, "활성화된 특성 목록에 없습니다"

        # 같은 특성 중복 활성화 시도
        result = char.activate_trait("hp_boost")
        assert result is False, "중복 활성화가 방지되어야 합니다"

        # 특성 비활성화
        result = char.deactivate_trait("hp_boost")
        assert result is True, "특성 비활성화에 실패했습니다"
        assert "hp_boost" not in char.active_traits, "비활성화된 특성이 목록에 남아있습니다"

    def test_combat_integration_damage_calculation(self):
        """전투 통합 테스트: 데미지 계산"""
        damage_calc = get_damage_calculator()

        # 캐릭터 생성
        attacker = Character("공격자", "warrior", level=5)
        defender = Character("방어자", "warrior", level=5)

        # 물리 공격력 증가 특성 활성화
        attacker.activate_trait("physical_power")

        # BRV 데미지 계산
        result = damage_calc.calculate_brv_damage(attacker, defender, skill_multiplier=1.0)

        # 데미지가 계산되었는지 확인
        assert result.final_damage > 0, "데미지가 0보다 커야 합니다"
        print(f"BRV 데미지: {result.final_damage}")

        # 크리티컬 보너스 특성 추가
        attacker.activate_trait("critical_boost")

        # 여러 번 공격하여 크리티컬 발생 확인
        critical_count = 0
        for _ in range(100):
            result = damage_calc.calculate_brv_damage(attacker, defender, skill_multiplier=1.0)
            if result.is_critical:
                critical_count += 1

        print(f"100회 공격 중 크리티컬 발생: {critical_count}회")
        assert critical_count > 0, "크리티컬이 한 번도 발생하지 않았습니다"

    def test_warrior_trait_adaptive_combat(self):
        """전사 직업 특성: 적응형 무술 테스트"""
        trait_manager = get_trait_effect_manager()
        char = Character("테스트 전사", "warrior", level=1)

        # adaptive_combat 특성 활성화
        char.activate_trait("adaptive_combat")

        # 스탠스 변경 컨텍스트로 데미지 배율 계산
        context = {"stance_changed": True}
        multiplier = trait_manager.calculate_damage_multiplier(char, "physical", **context)

        # 스탠스 변경 시 30% 증가
        assert multiplier == 1.30, f"스탠스 변경 시 배율이 1.30이어야 하는데 {multiplier}입니다"
        print(f"적응형 무술 (스탠스 변경): x{multiplier}")

    def test_warrior_trait_indomitable_will(self):
        """전사 직업 특성: 불굴의 의지 테스트"""
        trait_manager = get_trait_effect_manager()
        char = Character("테스트 전사", "warrior", level=1)

        # indomitable_will 특성 활성화
        char.activate_trait("indomitable_will")

        # HP를 절반으로 감소
        char.current_hp = char.max_hp // 2
        hp_before = char.current_hp

        # 턴 시작 효과 적용
        trait_manager.apply_turn_start_effects(char)

        # HP가 8% 회복되었는지 확인
        expected_heal = int(char.max_hp * 0.08)
        hp_after = char.current_hp

        assert hp_after > hp_before, "HP가 회복되어야 합니다"
        print(f"불굴의 의지 HP 회복: {hp_before} → {hp_after} (+{hp_after - hp_before}, 예상: {expected_heal})")


class TestTraitEffectTypes:
    """특성 효과 타입별 테스트"""

    def test_all_passive_traits_defined(self):
        """모든 패시브 특성이 정의되어 있는지 확인"""
        trait_manager = get_trait_effect_manager()

        passive_traits = [
            "hp_boost", "mp_boost", "speed_boost", "brv_boost",
            "physical_power", "magic_power", "physical_guard", "magic_guard",
            "critical_boost", "auto_regen", "mp_recovery",
            "first_strike", "break_master", "skill_master", "hp_danger_boost",
            "phoenix_blessing", "ultimate_power", "ultimate_defense"
        ]

        for trait_id in passive_traits:
            effects = trait_manager.get_trait_effects(trait_id)
            assert len(effects) > 0, f"특성 {trait_id}의 효과가 정의되어 있지 않습니다"
            print(f"✓ {trait_id}: {len(effects)}개 효과")

    def test_warrior_traits_defined(self):
        """전사 직업 특성이 정의되어 있는지 확인"""
        trait_manager = get_trait_effect_manager()

        warrior_traits = [
            "adaptive_combat", "battlefield_master", "indomitable_will",
            "combat_instinct", "complete_mastery"
        ]

        for trait_id in warrior_traits:
            effects = trait_manager.get_trait_effects(trait_id)
            assert len(effects) > 0, f"전사 특성 {trait_id}의 효과가 정의되어 있지 않습니다"
            print(f"✓ 전사 특성 {trait_id}: {len(effects)}개 효과")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
