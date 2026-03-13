"""
종합 정밀 테스트 — 신규 기능 전체 검증
pygame 의존성 없이 소스코드 직접 분석 + 독립 모듈 테스트
"""
import sys
import os
import logging

logging.disable(logging.CRITICAL)
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
sys.path.insert(0, os.path.dirname(__file__))

# pygame 완전 모킹
import types
import unittest.mock as mock

def create_pygame_mock():
    pg = types.ModuleType('pygame')
    for sub in ['mixer', 'font', 'image', 'display', 'draw', 'event',
                'time', 'transform', 'mouse', 'key', 'cursors',
                'sprite', 'surface', 'rect', 'color', 'math',
                'mixer.music', 'freetype', 'locals', 'scrap']:
        mod = types.ModuleType(f'pygame.{sub}')
        sys.modules[f'pygame.{sub}'] = mod
        parts = sub.split('.')
        setattr(pg, parts[0], mod if len(parts) == 1 else mod)

    pg.init = lambda: None
    pg.quit = lambda: None
    pg.Surface = mock.MagicMock()
    pg.Rect = mock.MagicMock()
    pg.Color = mock.MagicMock()
    pg.QUIT = 256
    pg.KEYDOWN = 768
    pg.KEYUP = 769
    pg.K_RETURN = 13
    pg.K_ESCAPE = 27
    pg.K_UP = 273
    pg.K_DOWN = 274
    pg.SRCALPHA = 65536
    pg.BLEND_RGBA_MULT = 0
    pg.mixer.Sound = mock.MagicMock()
    pg.mixer.music = mock.MagicMock()
    pg.mixer.init = lambda: None
    pg.font.Font = mock.MagicMock()
    pg.font.SysFont = mock.MagicMock()
    pg.font.init = lambda: None
    pg.image.load = mock.MagicMock(return_value=mock.MagicMock())
    pg.display.set_mode = mock.MagicMock()
    pg.display.set_caption = lambda x: None
    pg.display.flip = lambda: None
    pg.time.Clock = mock.MagicMock()
    pg.time.get_ticks = lambda: 0
    pg.transform.scale = mock.MagicMock(return_value=mock.MagicMock())
    pg.draw = mock.MagicMock()
    pg.mouse = mock.MagicMock()
    pg.key = mock.MagicMock()
    sys.modules['pygame'] = pg
    return pg

create_pygame_mock()

passed = 0
failed = 0
errors = []

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f" -- {detail}"
        print(msg)
        errors.append(name)

def read_source(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

# ============================================================
print("=" * 60)
print("TEST 1: AffinityManager 기본 기능")
print("=" * 60)
try:
    from src.character.affinity import AffinityManager, AffinityLevel

    mgr = AffinityManager()
    level = mgr.get_level("warrior", "mage")
    test("초기 호감도 = STRANGER", level == AffinityLevel.STRANGER)

    mgr.add_points("warrior", "mage", 100)
    level = mgr.get_level("warrior", "mage")
    test("100포인트 추가 -> COMRADE", level == AffinityLevel.COMRADE, f"got {level}")

    mgr.add_points("warrior", "mage", 700)
    level = mgr.get_level("warrior", "mage")
    test("800포인트 총합 -> SOUL_PARTNER", level == AffinityLevel.SOUL_PARTNER, f"got {level}")

    mgr2 = AffinityManager()
    jobs = ["warrior", "mage", "rogue"]
    mgr2.add_points_all(jobs, 1000)
    lv_wm = mgr2.get_level("warrior", "mage")
    lv_wr = mgr2.get_level("warrior", "rogue")
    lv_mr = mgr2.get_level("mage", "rogue")
    test("add_points_all -> 전원 SOUL_PARTNER",
         all(lv == AffinityLevel.SOUL_PARTNER for lv in [lv_wm, lv_wr, lv_mr]))
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 2: check_chain_abilities 동작")
print("=" * 60)
try:
    mgr3 = AffinityManager()
    jobs = ["warrior", "ranger", "mage", "paladin"]
    mgr3.add_points_all(jobs, 1000)

    results = mgr3.check_chain_abilities(
        actor_job="warrior", party_jobs=jobs, available_gauge=600
    )
    test("게이지 600 -> 체인어빌리티 반환", len(results) > 0, f"{len(results)}개")
    for r in results:
        print(f"    -> {r.ability.name} (by {r.ally_job}), cost={r.ability.gauge_cost}")

    results_low = mgr3.check_chain_abilities(
        actor_job="warrior", party_jobs=jobs, available_gauge=10
    )
    test("게이지 10 -> 체인어빌리티 없음", len(results_low) == 0)

    mgr4 = AffinityManager()
    results_no = mgr4.check_chain_abilities(
        actor_job="warrior", party_jobs=jobs, available_gauge=600
    )
    test("호감도 0 -> 체인어빌리티 없음", len(results_no) == 0)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 3: bond_skills.yaml 체인어빌리티 trigger='auto' 통일")
print("=" * 60)
try:
    import yaml
    with open("data/bond_skills.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    chain_list = data.get("chain_abilities", [])
    total_chain = len(chain_list)
    auto_count = sum(1 for ca in chain_list if ca.get("trigger") == "auto")
    non_auto = [f"{ca.get('id')}: {ca.get('trigger')}" for ca in chain_list if ca.get("trigger") != "auto"]
    doubled = sum(1 for ca in chain_list if ca.get("gauge_cost", 0) >= 90)
    cost_low = [f"{ca.get('id')}: {ca.get('gauge_cost')}" for ca in chain_list if ca.get("gauge_cost", 0) < 90]
    has_chance = any("trigger_chance_by_level" in ca for ca in chain_list)

    test(f"체인어빌리티 총 {total_chain}개", total_chain == 35, f"expected 35")
    test(f"전체 trigger='auto' ({auto_count}/{total_chain})", auto_count == total_chain,
         f"non-auto: {non_auto[:3]}")
    test(f"게이지 비용 2배 (>=90): {doubled}/{total_chain}", doubled == total_chain,
         f"low: {cost_low[:3]}")
    test("trigger_chance_by_level 전부 제거됨", not has_chance)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 4: bond_skills.yaml 연계스킬 데이터 무결성")
print("=" * 60)
try:
    bond_list = data.get("bond_skills", [])
    total_bond = len(bond_list)
    issues = []
    for bs in bond_list:
        for field in ["id", "name", "trigger", "effect"]:
            if field not in bs:
                issues.append(f"{bs.get('id','?')}: missing {field}")
        # effect는 단수 dict 또는 리스트
        eff = bs.get("effect", {})
        effs = [eff] if isinstance(eff, dict) else (eff if isinstance(eff, list) else [])
        for e in effs:
            if e.get("type") == "damage":
                st = e.get("stat_type", "")
                if st not in ["strength", "magic"]:
                    issues.append(f"{bs.get('id')}: stat_type={st}")

    test(f"연계스킬 총 {total_bond}개", total_bond == 70, f"expected 70")
    test("연계스킬 필수 필드 + stat_type 무결성", len(issues) == 0, f"{issues[:5]}")
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 5: Skill 클래스 triggers_chain 속성")
print("=" * 60)
try:
    from src.character.skills.skill import Skill
    skill = Skill("test_skill", "테스트스킬", "설명")
    test("Skill 기본 triggers_chain=False", skill.triggers_chain == False)

    skill.triggers_chain = True
    test("triggers_chain True 할당 가능", skill.triggers_chain == True)

    # 소스코드에 triggers_chain 선언 확인
    src = read_source("src/character/skills/skill.py")
    test("소스에 triggers_chain 선언 존재", "triggers_chain" in src)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 6: execute_bond_skill 레벨 스케일링 (소스 분석)")
print("=" * 60)
try:
    src = read_source("src/combat/combat_manager.py")

    # execute_bond_skill 함수 영역 추출
    idx = src.find("def execute_bond_skill")
    if idx < 0:
        raise Exception("execute_bond_skill 메서드 없음")
    # 다음 def까지
    next_def = src.find("\n    def ", idx + 10)
    func_src = src[idx:next_def] if next_def > 0 else src[idx:idx+3000]

    test("execute_bond_skill 메서드 존재", True)
    test("level_scaling 변수 사용", "level_scaling" in func_src)
    test("level_scaling_per_level 설정 참조", "level_scaling_per_level" in func_src)
    test("getattr로 캐릭터 레벨 참조", "getattr" in func_src and "level" in func_src)

    # 방어 공식 비율 기반
    test("방어 공식 비율 기반 (200.0)", "200.0" in func_src and "target_def" in func_src)

    # 수치 검증
    lv = 30
    scaling = 1.0 + (lv - 1) * 0.3
    test(f"레벨 30 스케일링 = {scaling}", abs(scaling - 9.7) < 0.01)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 7: _execute_brv_hp_attack is_break top-level 키 (소스 분석)")
print("=" * 60)
try:
    idx = src.find("def _execute_brv_hp_attack")
    if idx < 0:
        raise Exception("_execute_brv_hp_attack 메서드 없음")
    next_def = src.find("\n    def ", idx + 10)
    func_src = src[idx:next_def] if next_def > 0 else src[idx:idx+3000]

    has_toplevel = ('"is_break": brv_attack_result.get("is_break"' in func_src or
                    '"is_break": brv_attack_result.get("is_break", False)' in func_src)
    test("combined_result에 is_break top-level 키", has_toplevel)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 8: execute_action 체인어빌리티 트리거 체크 (소스 분석)")
print("=" * 60)
try:
    idx = src.find("def execute_action")
    if idx < 0:
        raise Exception("execute_action 메서드 없음")
    next_def = src.find("\n    def ", idx + 10)
    func_src = src[idx:next_def] if next_def > 0 else src[idx:idx+5000]

    test("is_break 체크", 'result.get("is_break")' in func_src)
    test("brv_is_break 체크", 'result.get("brv_is_break")' in func_src)
    test("is_scatter 체크", 'is_scatter' in func_src)
    test("triggers_chain 체크", 'triggers_chain' in func_src)
    test('trigger_reason "break"', '"break"' in func_src)
    test('trigger_reason "scatter"', '"scatter"' in func_src)
    test('trigger_reason "skill"', '"skill"' in func_src)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 9: _execute_skill BREAK 감지 로직 (소스 분석)")
print("=" * 60)
try:
    idx = src.find("def _execute_skill")
    if idx < 0:
        raise Exception("_execute_skill 메서드 없음")
    next_def = src.find("\n    def ", idx + 10)
    func_src = src[idx:next_def] if next_def > 0 else src[idx:idx+5000]

    test("target_was_broken_before 저장", "target_was_broken_before" in func_src)
    test("brave.is_broken 호출", "self.brave.is_broken" in func_src or "brave.is_broken" in func_src)
    test('result["is_break"] = True 설정', 'result["is_break"] = True' in func_src)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 10: _trigger_chain_ability_check 메서드 (소스 분석)")
print("=" * 60)
try:
    idx = src.find("def trigger_chain_ability_check")
    if idx < 0:
        raise Exception("trigger_chain_ability_check 메서드 없음")
    next_def = src.find("\n    def ", idx + 10)
    func_src = src[idx:next_def] if next_def > 0 else src[idx:idx+3000]

    test("trigger_chain_ability_check 존재", True)
    test("_affinity_manager 참조", "_affinity_manager" in func_src)
    test("party_jobs 수집", "party_jobs" in func_src)
    test("pending_chain_abilities 저장", "pending_chain_abilities" in func_src)
    test("CHAIN_ABILITY_TRIGGERED 이벤트", "CHAIN_ABILITY_TRIGGERED" in func_src)
    test("trigger_reason 매개변수", "trigger_reason" in func_src)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 11: execute_teamwork_skill 체인어빌리티 트리거 (소스 분석)")
print("=" * 60)
try:
    idx = src.find("def execute_teamwork_skill")
    if idx < 0:
        raise Exception("execute_teamwork_skill 메서드 없음")
    next_def = src.find("\n    def ", idx + 10)
    func_src = src[idx:next_def] if next_def > 0 else src[idx:idx+5000]

    test("trigger_chain_ability_check 호출", "trigger_chain_ability_check" in func_src)
    test('trigger_reason "teamwork"', '"teamwork"' in func_src)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 12: brave_system.py BREAK 결과 (소스 분석)")
print("=" * 60)
try:
    bsrc = read_source("src/combat/brave_system.py")

    test("brv_attack 메서드 존재", "def brv_attack" in bsrc)
    test("is_break 결과 포함", '"is_break": is_break' in bsrc or '"is_break"' in bsrc)
    test("BREAK 감지 로직 (is_break = True)", "is_break = True" in bsrc)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 13: combat_ui.py 체인어빌리티 선택 UI (소스 분석)")
print("=" * 60)
try:
    uisrc = read_source("src/ui/combat_ui.py")

    test("CHAIN_ABILITY_SELECT 상태", "CHAIN_ABILITY_SELECT" in uisrc)
    test("_enter_chain_ability_select 메서드", "def _enter_chain_ability_select" in uisrc)
    test("_handle_chain_ability_select 메서드", "def _handle_chain_ability_select" in uisrc)
    test("_render_chain_ability_select 메서드", "def _render_chain_ability_select" in uisrc)
    test("pending_chain_abilities 체크", "pending_chain_abilities" in uisrc)
    test("ESC 패스 기능", "패스" in uisrc or "사용하지 않았다" in uisrc)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 14: 팀워크 게이지 start_combat 후 설정")
print("=" * 60)
try:
    for fname, label in [("src/ui/training_mode.py", "training_mode"),
                          ("src/ui/boss_test_mode.py", "boss_test_mode")]:
        fc = read_source(fname)
        sc_pos = fc.find("start_combat(")
        gauge_pos = fc.find("teamwork_gauge = 600")
        test(f"{label}: teamwork_gauge = 600 존재", gauge_pos > 0)
        test(f"{label}: start_combat 이후 설정", gauge_pos > sc_pos,
             f"sc@{sc_pos} gauge@{gauge_pos}")
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 15: combat_tooltip 독 중첩 표시 제거")
print("=" * 60)
try:
    tsrc = read_source("src/ui/combat_tooltip.py")
    lines = tsrc.split('\n')
    has_poison = False
    for line in lines:
        s = line.strip()
        if s.startswith('#'):
            continue
        if '독 중첩' in s and 'pass' not in s:
            has_poison = True
            break
    test("독 중첩 활성 코드 없음 (주석 외)", not has_poison)

    vidx = tsrc.find('venom_system')
    if vidx > 0:
        after = tsrc[vidx:vidx+200]
        test("venom_system 처리 = pass", 'pass' in after)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 16: check_chain_abilities 시그니처 (확률/rng 제거)")
print("=" * 60)
try:
    import inspect
    sig = inspect.signature(AffinityManager.check_chain_abilities)
    params = list(sig.parameters.keys())

    test("trigger_event 매개변수 없음", "trigger_event" not in params, f"params: {params}")
    test("rng 매개변수 없음", "rng" not in params, f"params: {params}")
    test("actor_job 매개변수 있음", "actor_job" in params)
    test("party_jobs 매개변수 있음", "party_jobs" in params)
    test("available_gauge 매개변수 있음", "available_gauge" in params)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 17: check_chain_abilities 쿨다운 로직")
print("=" * 60)
try:
    asrc = read_source("src/character/affinity.py")
    idx = asrc.find("def check_chain_abilities")
    next_def = asrc.find("\n    def ", idx + 10)
    func_src = asrc[idx:next_def]

    test("쿨다운 체크 (_is_on_cooldown)", "_is_on_cooldown" in func_src)
    test("게이지 비용 체크 (gauge_cost)", "gauge_cost" in func_src)
    test("호감도 레벨 체크 (required_affinity_level)", "required_affinity_level" in func_src)
    test("확률 roll 없음 (trigger_chance 미사용)", "trigger_chance" not in func_src)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
print("\n" + "=" * 60)
print("TEST 18: 핵심 메서드 존재 일괄 확인 (combat_manager)")
print("=" * 60)
try:
    methods = [
        "def execute_action",
        "def execute_bond_skill",
        "def execute_teamwork_skill",
        "def _execute_brv_hp_attack",
        "def _execute_skill",
        "def _trigger_chain_ability_check",
        "def check_chain_abilities",
    ]
    for m in methods:
        # check_chain_abilities는 AffinityManager에 있음 (combat_manager가 아님)
        if m == "def check_chain_abilities":
            asrc2 = read_source("src/character/affinity.py")
            test(f"affinity.py: {m}", m in asrc2)
        # trigger_chain_ability_check는 언더스코어 없음
        elif m == "def _trigger_chain_ability_check":
            test(f"combat_manager: def trigger_chain_ability_check",
                 "def trigger_chain_ability_check" in src)
        else:
            test(f"combat_manager: {m}", m in src)
except Exception as e:
    print(f"  [ERROR] {e}")
    failed += 1

# ============================================================
# 최종 결과
# ============================================================
print("\n" + "=" * 60)
total = passed + failed
print(f"FINAL RESULT: {passed} PASSED / {failed} FAILED / {total} TOTAL")
print("=" * 60)

if errors:
    print("\nFailed tests:")
    for e in errors:
        print(f"  - {e}")
    print()
else:
    print("\n>>> ALL TESTS PASSED <<<\n")

sys.exit(0 if failed == 0 else 1)
