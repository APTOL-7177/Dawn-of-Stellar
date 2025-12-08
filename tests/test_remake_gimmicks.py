import types

import pytest

from src.character.gimmick_updater import GimmickUpdater
from src.character.skills.skill import Skill, SkillResult
from src.character.skills.skill_manager import SkillManager
from src.character.skills.custom_handlers import execute_custom_handler
from src.character.skills.effects.status_effect import StatusEffect as SkillStatusEffect
from src.core.event_bus import event_bus, Events
from src.combat.status_effects import StatusManager, StatusEffect as CombatStatusEffect, StatusType
from src.character.skills.skill_manager import get_skill_manager


class DummyChar:
    def __init__(self, name="dummy"):
        self.name = name
        self.is_alive = True
        self.current_hp = 100
        self.max_hp = 100
        self.current_mp = 50
        self.max_mp = 50
        self.gimmick_type = None
        self.spirit_slots = []
        self.status_manager = StatusManager(owner_name=name, owner=self)
        self.max_cheer = 100

    def __repr__(self):
        return f"<Char {self.name}>"


def test_intrusion_require_and_consume():
    sm = SkillManager()
    user = DummyChar("hacker")
    target = DummyChar("enemy")
    target.intrusion_gauge = 50

    # requires_intrusion 미충족 -> 실패
    skill = Skill("test_intrusion_fail", "fail", "")
    skill.metadata = {"requires_intrusion": 75}
    skill.execute = types.MethodType(lambda self, u, t, c: SkillResult(True, "ok"), skill)

    sm._skills[skill.skill_id] = skill
    result = sm.execute_skill(skill.skill_id, user, target)
    assert not result.success

    # 충족 + consumes_intrusion -> 성공 후 침투 0
    target.intrusion_gauge = 100
    skill2 = Skill("test_intrusion_consume", "consume", "")
    skill2.metadata = {"requires_intrusion": 50, "consumes_intrusion": True}
    skill2.execute = types.MethodType(lambda self, u, t, c: SkillResult(True, "ok"), skill2)

    sm._skills[skill2.skill_id] = skill2
    result = sm.execute_skill(skill2.skill_id, user, target)
    assert result.success
    assert getattr(target, "intrusion_gauge", 0) == 0


def test_oath_faith_gain_on_purify():
    pal = DummyChar("paladin")
    pal.gimmick_type = "oath_system"
    pal.gimmick_data = {}
    pal.oaths = {
        "purity": {
            "reward_actions": [],
            "reward_action": "purify",
            "faith_per_purify": 15,
            "violation_penalty": {},
        }
    }
    pal.current_oath = "purity"
    pal.faith = 0
    pal.max_faith = 100

    skill = Skill("purify_skill", "purify", "")
    skill.metadata = {"purify": True}
    skill.execute = types.MethodType(lambda self, u, t, c: SkillResult(True, "ok"), skill)

    event_bus.publish(Events.SKILL_EXECUTE, {"skill": skill, "user": pal, "target": None, "result": SkillResult(True, "")})
    assert pal.faith >= 15


def test_mockery_gain_on_skill():
    rogue = DummyChar("rogue")
    rogue.gimmick_type = "mockery_system"
    rogue.max_mockery = 10
    rogue.mockery_effects = {}

    target = DummyChar("target")
    target.mockery_gauge = 0

    skill = Skill("mockery_skill", "mock", "")
    skill.metadata = {"mockery_gain": 2}
    skill.execute = types.MethodType(lambda self, u, t, c: SkillResult(True, "ok"), skill)

    event_bus.publish(Events.SKILL_EXECUTE, {"skill": skill, "user": rogue, "target": target, "result": SkillResult(True, "")})
    assert getattr(target, "mockery_gauge", 0) >= 2


def test_elementalist_requires_and_consumes_spirits():
    sm = SkillManager()
    elem = DummyChar("elementalist")
    elem.gimmick_type = "elemental_spirits"
    elem.spirit_fire = 1
    elem.spirit_water = 0

    skill = Skill("fusion_check", "fusion", "")
    skill.metadata = {"requires_spirits": 2, "consumes_all_spirits": True}
    skill.execute = types.MethodType(lambda self, u, t, c: SkillResult(True, "ok"), skill)
    sm._skills[skill.skill_id] = skill

    fail = sm.execute_skill(skill.skill_id, elem, None)
    assert not fail.success

    elem.spirit_water = 1
    ok = sm.execute_skill(skill.skill_id, elem, None)
    assert ok.success
    assert GimmickUpdater.get_active_spirits_count(elem) == 0


def test_elementalist_resonance_status_bonus():
    user = DummyChar("elem")
    user.gimmick_type = "elemental_spirits"
    user.active_resonance = "fire_wind"
    target = DummyChar("mob")

    effect = SkillStatusEffect(
        status_type="burn",
        duration=2,
        chance=0.0,  # 기본 확률 0이지만
        resonance_chance=1.0,  # 공명 시 100%
        resonance_duration_bonus=1,
    )
    applied = effect.execute(user, target, {})
    assert applied.success
    burn = target.status_manager.get_status(StatusType.BURN)
    assert burn is not None
    assert burn.duration >= 3


def test_elementalist_fusion_resonance_chance_and_duration():
    user = DummyChar("elem")
    user.gimmick_type = "elemental_spirits"
    user.active_resonance = "water_earth"
    target = DummyChar("mob")
    effect = SkillStatusEffect(
        status_type="slow",
        duration=2,
        chance=0.0,  # 기본 0%
        resonance_chance=1.0,  # 공명 시 100%
        resonance_duration_bonus=1,
    )
    applied = effect.execute(user, target, {})
    assert applied.success
    trap = target.status_manager.get_status(StatusType.REDUCE_SPD) or target.status_manager.status_effects
    # 최소한 적용 여부/지속 증가 확인
    assert target.status_manager.status_effects
    assert any(getattr(e, "duration", 0) >= 3 for e in target.status_manager.status_effects)


def test_copy_random_buff_handler():
    user = DummyChar("hacker")
    target = DummyChar("enemy")
    buff = CombatStatusEffect(name="Test Buff", status_type=StatusType.BUFF, duration=2, intensity=1.0)
    target.status_manager.add_status(buff)

    result = execute_custom_handler("copy_random_buff", {}, user, target, {})
    assert result.success
    copied = any(e.name == "Test Buff" for e in user.status_manager.status_effects)
    assert copied


def test_copy_enemy_skill_handler():
    user = DummyChar("hacker")
    enemy = DummyChar("enemy")
    enemy.skill_ids = ["evil_skill_1", "evil_skill_2"]

    res = execute_custom_handler("copy_enemy_skill", {}, user, enemy, {})
    assert res.success
    assert hasattr(user, "copied_skills")
    assert any(s in enemy.skill_ids for s in user.copied_skills)
    # skill_ids에 추가되어 바로 사용 가능
    sm = get_skill_manager()
    copied_id = user.copied_skills[0]
    dummy_skill = Skill(copied_id, "copied", "")
    dummy_skill.execute = types.MethodType(lambda self, u, t, c: SkillResult(True, "ok"), dummy_skill)
    sm.register_skill(dummy_skill)
    result = sm.execute_skill(copied_id, user, None)
    assert result.success


def test_dimensionist_requires_refraction_and_shield_convert():
    sm = SkillManager()
    dim = DummyChar("dimensionist")
    dim.gimmick_type = "dimension_refraction"
    dim.refraction_stacks = 0

    skill = Skill("refraction_skill", "refraction", "")
    skill.metadata = {"requires_refraction_check": True}
    skill.execute = types.MethodType(lambda self, u, t, c: SkillResult(True, "ok"), skill)
    sm._skills[skill.skill_id] = skill
    fail = sm.execute_skill(skill.skill_id, dim, None)
    assert not fail.success

    dim.refraction_stacks = 100
    ok = sm.execute_skill(skill.skill_id, dim, None)
    assert ok.success

    res = execute_custom_handler("refraction_to_shield", {"convert_percent": 0.3, "duration": 2}, dim, dim, {})
    assert res.success
    assert getattr(dim, "refraction_stacks", 0) <= 70
    shield = dim.status_manager.get_status(StatusType.SHIELD)
    assert shield is not None


def test_dimension_refraction_decay_applies_damage_and_reduces_stacks():
    dim = DummyChar("dimensionist")
    dim.gimmick_type = "dimension_refraction"
    dim.refraction_stacks = 100
    dim.current_hp = 200
    # 간단한 take_fixed_damage 구현
    dim.take_fixed_damage = lambda dmg: setattr(dim, "current_hp", dim.current_hp - dmg) or dmg

    GimmickUpdater._update_dimension_refraction(dim)
    # 기본 감소율 35% -> 35 소모, 65 남음, HP 35 감소
    assert dim.refraction_stacks == 65
    assert dim.current_hp == 165


def test_dimension_refraction_chain_accumulate_and_spend():
    from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation

    dim = DummyChar("dimensionist")
    dim.gimmick_type = "dimension_refraction"
    dim.refraction_stacks = 0
    dim.current_hp = 100

    # 피격 시 굴절 축적 (간단히 수동 적용)
    incoming = 50
    reduction = 0.85
    refracted = int(incoming * reduction)
    dim.refraction_stacks += refracted
    dim.current_hp -= (incoming - refracted)
    assert getattr(dim, "refraction_stacks", 0) == refracted

    # 굴절 소모 스킬 흉내: multiply 0.5
    reduce_effect = GimmickEffect(GimmickOperation.MULTIPLY, "refraction_stacks", 0.5, min_value=0)
    skill = Skill("refraction_spend", "spend", "")
    skill.effects = [reduce_effect]
    skill.metadata = {"requires_refraction_check": True}
    sm = SkillManager()
    sm._skills[skill.skill_id] = skill

    result = sm.execute_skill(skill.skill_id, dim, None)
    assert result.success
    # 소모 후 절반 이하로 줄어야 함
    assert getattr(dim, "refraction_stacks", 0) <= 25


def test_crowd_demand_fulfill_on_kill():
    glad = DummyChar("glad")
    glad.gimmick_type = "crowd_cheer"
    glad.current_demand = {
        "id": "kill",
        "name": "마무리 일격",
        "condition": "kill_enemy",
        "cheer_reward": 15,
        "fulfilled": False,
    }
    glad.demand_progress = {}
    glad.cheer = 0
    victim = DummyChar("mob")

    GimmickUpdater.check_demand_fulfillment(glad, "kill", {"target_id": id(victim)})
    assert glad.current_demand.get("fulfilled")
    assert glad.cheer >= 15
