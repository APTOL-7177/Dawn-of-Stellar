"""
Status Effects 테스트

상태 효과 시스템의 주요 기능을 테스트합니다.
"""

import pytest
from src.combat.status_effects import (
    StatusEffect,
    StatusManager,
    StatusType,
    create_status_effect,
    get_status_category,
    get_status_icon
)


class TestStatusEffect:
    """StatusEffect 클래스 테스트"""

    def test_create_basic_status_effect(self):
        """기본 상태 효과 생성"""
        effect = StatusEffect(
            name="독",
            status_type=StatusType.POISON,
            duration=5,
            intensity=1.0
        )

        assert effect.name == "독"
        assert effect.status_type == StatusType.POISON
        assert effect.duration == 5
        assert effect.max_duration == 5
        assert effect.intensity == 1.0
        assert effect.stack_count == 1
        assert effect.max_stacks == 1
        assert not effect.is_stackable

    def test_stackable_status_effect(self):
        """스택 가능 상태 효과 생성"""
        effect = StatusEffect(
            name="재생",
            status_type=StatusType.REGENERATION,
            duration=5,
            intensity=1.5,
            is_stackable=True,
            max_stacks=3
        )

        assert effect.is_stackable
        assert effect.max_stacks == 3
        assert effect.stack_count == 1

    def test_status_effect_string_representation(self):
        """상태 효과 문자열 표현"""
        effect = StatusEffect(
            name="화상",
            status_type=StatusType.BURN,
            duration=3
        )

        assert "화상(3턴)" in str(effect)

    def test_stackable_effect_string(self):
        """스택 가능 효과의 문자열 표현"""
        effect = StatusEffect(
            name="공격력 강화",
            status_type=StatusType.BOOST_ATK,
            duration=5,
            is_stackable=True,
            max_stacks=3
        )
        effect.stack_count = 2

        assert "x2" in str(effect)
        assert "5턴" in str(effect)


class TestStatusManager:
    """StatusManager 클래스 테스트"""

    def test_add_status_new(self):
        """새로운 상태 효과 추가"""
        manager = StatusManager("TestChar")
        effect = create_status_effect("독", StatusType.POISON, 5)

        result = manager.add_status(effect)

        assert result is True  # 새로운 효과 추가
        assert len(manager.status_effects) == 1
        assert manager.has_status(StatusType.POISON)

    def test_add_status_refresh(self):
        """기존 상태 효과 갱신"""
        manager = StatusManager("TestChar")

        effect1 = create_status_effect("독", StatusType.POISON, 3, intensity=1.0)
        manager.add_status(effect1)

        effect2 = create_status_effect("독", StatusType.POISON, 5, intensity=1.5)
        result = manager.add_status(effect2)

        assert result is False  # 갱신됨
        assert len(manager.status_effects) == 1
        assert manager.get_status(StatusType.POISON).duration == 5
        assert manager.get_status(StatusType.POISON).intensity == 1.5

    def test_add_stackable_status(self):
        """스택 가능 상태 효과 추가"""
        manager = StatusManager("TestChar")

        effect1 = create_status_effect(
            "재생", StatusType.REGENERATION, 5,
            is_stackable=True, max_stacks=3
        )
        manager.add_status(effect1)

        effect2 = create_status_effect(
            "재생", StatusType.REGENERATION, 3,
            is_stackable=True, max_stacks=3
        )
        manager.add_status(effect2)

        status = manager.get_status(StatusType.REGENERATION)
        assert status.stack_count == 2
        assert status.duration == 5  # 더 긴 지속시간 유지

    def test_remove_status(self):
        """상태 효과 제거"""
        manager = StatusManager("TestChar")
        effect = create_status_effect("독", StatusType.POISON, 5)
        manager.add_status(effect)

        result = manager.remove_status(StatusType.POISON)

        assert result is True
        assert len(manager.status_effects) == 0
        assert not manager.has_status(StatusType.POISON)

    def test_remove_nonexistent_status(self):
        """존재하지 않는 상태 효과 제거 시도"""
        manager = StatusManager("TestChar")

        result = manager.remove_status(StatusType.POISON)

        assert result is False

    def test_get_status(self):
        """상태 효과 조회"""
        manager = StatusManager("TestChar")
        effect = create_status_effect("화상", StatusType.BURN, 4, intensity=2.0)
        manager.add_status(effect)

        status = manager.get_status(StatusType.BURN)

        assert status is not None
        assert status.name == "화상"
        assert status.duration == 4
        assert status.intensity == 2.0

    def test_has_status(self):
        """상태 효과 보유 확인"""
        manager = StatusManager("TestChar")
        effect = create_status_effect("기절", StatusType.STUN, 2)
        manager.add_status(effect)

        assert manager.has_status(StatusType.STUN)
        assert not manager.has_status(StatusType.POISON)

    def test_update_duration(self):
        """지속시간 갱신 및 만료"""
        manager = StatusManager("TestChar")

        effect1 = create_status_effect("독", StatusType.POISON, 2)
        effect2 = create_status_effect("화상", StatusType.BURN, 1)
        manager.add_status(effect1)
        manager.add_status(effect2)

        # 1턴 경과
        expired = manager.update_duration()

        assert len(expired) == 1  # 화상 만료
        assert expired[0].status_type == StatusType.BURN
        assert len(manager.status_effects) == 1  # 독만 남음
        assert manager.get_status(StatusType.POISON).duration == 1

        # 1턴 더 경과
        expired = manager.update_duration()

        assert len(expired) == 1  # 독 만료
        assert len(manager.status_effects) == 0

    def test_clear_all_effects(self):
        """모든 상태 효과 제거"""
        manager = StatusManager("TestChar")

        manager.add_status(create_status_effect("독", StatusType.POISON, 5))
        manager.add_status(create_status_effect("화상", StatusType.BURN, 3))
        manager.add_status(create_status_effect("재생", StatusType.REGENERATION, 4))

        assert len(manager.status_effects) == 3

        manager.clear_all_effects()

        assert len(manager.status_effects) == 0

    def test_can_act_when_stunned(self):
        """기절 상태에서 행동 불가"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("기절", StatusType.STUN, 2))

        assert not manager.can_act()

    def test_can_act_when_sleeping(self):
        """수면 상태에서 행동 불가"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("수면", StatusType.SLEEP, 2))

        assert not manager.can_act()

    def test_can_act_when_frozen(self):
        """빙결 상태에서 행동 불가"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("빙결", StatusType.FREEZE, 2))

        assert not manager.can_act()

    def test_can_act_with_dot(self):
        """DOT 효과는 행동 가능"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("독", StatusType.POISON, 5))
        manager.add_status(create_status_effect("화상", StatusType.BURN, 3))

        assert manager.can_act()

    def test_can_use_skills_when_silenced(self):
        """침묵 상태에서 스킬 사용 불가"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("침묵", StatusType.SILENCE, 3))

        assert not manager.can_use_skills()
        assert manager.can_act()  # 행동은 가능

    def test_can_use_skills_normal(self):
        """정상 상태에서 스킬 사용 가능"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("독", StatusType.POISON, 5))

        assert manager.can_use_skills()

    def test_is_controlled_charm(self):
        """매혹 상태에서 제어 불가"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("매혹", StatusType.CHARM, 2))

        assert manager.is_controlled()

    def test_is_controlled_dominate(self):
        """지배 상태에서 제어 불가"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("지배", StatusType.DOMINATE, 3))

        assert manager.is_controlled()

    def test_is_controlled_confusion(self):
        """혼란 상태에서 제어 불가"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("혼란", StatusType.CONFUSION, 2))

        assert manager.is_controlled()

    def test_not_controlled(self):
        """정상 상태에서 제어 가능"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("독", StatusType.POISON, 5))

        assert not manager.is_controlled()

    def test_has_stealth(self):
        """은신 상태 확인"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("은신", StatusType.STEALTH, 3))

        assert manager.has_stealth()

    def test_has_invincibility(self):
        """무적 상태 확인"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("무적", StatusType.INVINCIBLE, 2))

        assert manager.has_invincibility()

    def test_get_stat_modifiers_boost_atk(self):
        """공격력 강화 효과"""
        manager = StatusManager("TestChar")
        effect = create_status_effect("공격력 강화", StatusType.BOOST_ATK, 5, intensity=1.0)
        manager.add_status(effect)

        modifiers = manager.get_stat_modifiers()

        assert modifiers['physical_attack'] == 1.2
        assert modifiers['magic_attack'] == 1.2

    def test_get_stat_modifiers_reduce_def(self):
        """방어력 감소 효과"""
        manager = StatusManager("TestChar")
        effect = create_status_effect("방어력 감소", StatusType.REDUCE_DEF, 3, intensity=1.0)
        manager.add_status(effect)

        modifiers = manager.get_stat_modifiers()

        assert modifiers['physical_defense'] == 0.8
        assert modifiers['magic_defense'] == 0.8

    def test_get_stat_modifiers_haste(self):
        """가속 효과"""
        manager = StatusManager("TestChar")
        effect = create_status_effect("가속", StatusType.HASTE, 3)
        manager.add_status(effect)

        modifiers = manager.get_stat_modifiers()

        assert modifiers['speed'] == 1.5

    def test_get_stat_modifiers_slow(self):
        """둔화 효과"""
        manager = StatusManager("TestChar")
        effect = create_status_effect("둔화", StatusType.SLOW, 3)
        manager.add_status(effect)

        modifiers = manager.get_stat_modifiers()

        assert modifiers['speed'] == 0.6

    def test_get_stat_modifiers_stacked(self):
        """스택된 효과의 배율"""
        manager = StatusManager("TestChar")
        effect = create_status_effect(
            "공격력 강화", StatusType.BOOST_ATK, 5,
            intensity=1.0, is_stackable=True, max_stacks=3
        )
        manager.add_status(effect)
        effect.stack_count = 3

        modifiers = manager.get_stat_modifiers()

        # intensity=1.0, stack=3 -> 3.0 * 0.2 = 0.6 -> 1.6배
        assert modifiers['physical_attack'] == pytest.approx(1.6)

    def test_get_stat_modifiers_multiple_effects(self):
        """여러 효과의 곱셈 적용"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("공격력 강화", StatusType.BOOST_ATK, 5, intensity=1.0))
        manager.add_status(create_status_effect("가속", StatusType.HASTE, 3))

        modifiers = manager.get_stat_modifiers()

        assert modifiers['physical_attack'] == 1.2
        assert modifiers['magic_attack'] == 1.2
        assert modifiers['speed'] == 1.5

    def test_get_stat_modifiers_vulnerable(self):
        """취약 상태 (방어력 0.5배)"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("취약", StatusType.VULNERABLE, 3))

        modifiers = manager.get_stat_modifiers()

        assert modifiers['physical_defense'] == 0.5
        assert modifiers['magic_defense'] == 0.5

    def test_get_stat_modifiers_berserk(self):
        """광폭화 (공격력 증가, 방어력 감소)"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("광폭화", StatusType.BERSERK, 5))

        modifiers = manager.get_stat_modifiers()

        assert modifiers['physical_attack'] == 1.6
        assert modifiers['magic_attack'] == 1.6
        assert modifiers['physical_defense'] == 0.6
        assert modifiers['magic_defense'] == 0.6
        assert modifiers['accuracy'] == 0.8

    def test_get_active_effects(self):
        """활성 효과 목록"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("독", StatusType.POISON, 5))
        manager.add_status(create_status_effect("재생", StatusType.REGENERATION, 3))

        active = manager.get_active_effects()

        assert "독" in active
        assert "재생" in active
        assert len(active) == 2

    def test_get_status_display_empty(self):
        """상태 효과 없음"""
        manager = StatusManager("TestChar")

        display = manager.get_status_display()

        assert display == "상태 효과 없음"

    def test_get_status_display_with_effects(self):
        """상태 효과 표시 문자열"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("독", StatusType.POISON, 5))
        manager.add_status(create_status_effect("재생", StatusType.REGENERATION, 3))

        display = manager.get_status_display()

        assert "독(5)" in display
        assert "재생(3)" in display


class TestUtilityFunctions:
    """유틸리티 함수 테스트"""

    def test_create_status_effect_helper(self):
        """create_status_effect 헬퍼 함수"""
        effect = create_status_effect(
            name="화상",
            status_type=StatusType.BURN,
            duration=4,
            intensity=1.5,
            is_stackable=True,
            max_stacks=5,
            source_id="player1",
            damage_type="fire"
        )

        assert effect.name == "화상"
        assert effect.status_type == StatusType.BURN
        assert effect.duration == 4
        assert effect.intensity == 1.5
        assert effect.is_stackable
        assert effect.max_stacks == 5
        assert effect.source_id == "player1"
        assert effect.metadata["damage_type"] == "fire"

    def test_get_status_category_buff(self):
        """버프 카테고리"""
        assert get_status_category(StatusType.BOOST_ATK) == "BUFF"
        assert get_status_category(StatusType.BLESSING) == "BUFF"
        assert get_status_category(StatusType.HASTE) == "BUFF"

    def test_get_status_category_debuff(self):
        """디버프 카테고리"""
        assert get_status_category(StatusType.REDUCE_DEF) == "DEBUFF"
        assert get_status_category(StatusType.VULNERABLE) == "DEBUFF"
        assert get_status_category(StatusType.WEAKNESS) == "DEBUFF"

    def test_get_status_category_dot(self):
        """DOT 카테고리"""
        assert get_status_category(StatusType.POISON) == "DOT"
        assert get_status_category(StatusType.BURN) == "DOT"
        assert get_status_category(StatusType.BLEED) == "DOT"

    def test_get_status_category_hot(self):
        """HOT 카테고리"""
        assert get_status_category(StatusType.REGENERATION) == "HOT"
        assert get_status_category(StatusType.MP_REGEN) == "HOT"

    def test_get_status_category_cc(self):
        """CC 카테고리"""
        assert get_status_category(StatusType.STUN) == "CC"
        assert get_status_category(StatusType.SILENCE) == "CC"
        assert get_status_category(StatusType.FREEZE) == "CC"

    def test_get_status_category_special(self):
        """특수 카테고리"""
        assert get_status_category(StatusType.STEALTH) == "SPECIAL"
        assert get_status_category(StatusType.TIME_STOP) == "SPECIAL"

    def test_get_status_icon(self):
        """상태 효과 아이콘"""
        assert get_status_icon(StatusType.POISON) == "☠️"
        assert get_status_icon(StatusType.BURN) == "🔥"
        assert get_status_icon(StatusType.STUN) == "😵"
        assert get_status_icon(StatusType.REGENERATION) == "💚"


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_add_status_max_stacks(self):
        """최대 스택 도달 시 더 이상 증가 안 함"""
        manager = StatusManager("TestChar")
        effect = create_status_effect(
            "재생", StatusType.REGENERATION, 5,
            is_stackable=True, max_stacks=3
        )
        manager.add_status(effect)

        # 최대 스택까지 추가
        for _ in range(5):
            manager.add_status(create_status_effect(
                "재생", StatusType.REGENERATION, 3,
                is_stackable=True, max_stacks=3
            ))

        status = manager.get_status(StatusType.REGENERATION)
        assert status.stack_count == 3  # 최대 3스택

    def test_multiple_cc_effects(self):
        """여러 CC 효과 동시 적용"""
        manager = StatusManager("TestChar")
        manager.add_status(create_status_effect("기절", StatusType.STUN, 1))
        manager.add_status(create_status_effect("침묵", StatusType.SILENCE, 3))
        manager.add_status(create_status_effect("실명", StatusType.BLIND, 2))

        assert not manager.can_act()  # 기절 때문에
        assert not manager.can_use_skills()  # 침묵 때문에

    def test_duration_zero_not_expired(self):
        """지속시간 0은 만료되지 않음 (영구 효과)"""
        manager = StatusManager("TestChar")
        effect = create_status_effect("영구 버프", StatusType.BOOST_ATK, 0)
        manager.add_status(effect)

        # update_duration 호출
        expired = manager.update_duration()

        # duration이 음수가 되어 만료됨
        assert len(expired) == 1
        assert len(manager.status_effects) == 0
