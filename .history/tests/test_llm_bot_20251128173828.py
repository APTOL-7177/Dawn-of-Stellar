"""
LLM 플레이어 봇 테스트
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.multiplayer.llm_player_bot import (
    LLMPlayerBot,
    LLMConfig,
    CombatState,
    CombatantState,
    SkillInfo,
    ItemInfo,
    ActionType,
    test_ollama_connection_sync,
    create_llm_bot,
    SYSTEM_PROMPT,
    create_combat_prompt,
    JOB_DATABASE
)


def create_mock_combat_state() -> CombatState:
    """테스트용 전투 상태 생성"""
    
    # 아군 파티
    allies = [
        CombatantState(
            name="전사봇",
            job="전사",
            hp=800,
            max_hp=1000,
            mp=50,
            max_mp=100,
            brv=450,
            max_brv=2000,
            atb_percent=100,
            is_alive=True,
            is_broken=False,
            status_effects=[],
            gimmick_value=3,
            gimmick_name="스탠스(공격)"
        ),
        CombatantState(
            name="힐러",
            job="성직자",
            hp=300,
            max_hp=600,
            mp=80,
            max_mp=150,
            brv=200,
            max_brv=1500,
            atb_percent=75,
            is_alive=True,
            is_broken=False,
            status_effects=[],
            gimmick_value=4,
            gimmick_name="신앙"
        ),
        CombatantState(
            name="마법사",
            job="아크메이지",
            hp=450,
            max_hp=500,
            mp=120,
            max_mp=200,
            brv=800,
            max_brv=2500,
            atb_percent=50,
            is_alive=True,
            is_broken=False,
            status_effects=["화염 부여"],
            gimmick_value=2,
            gimmick_name="원소(화염x2)"
        ),
        CombatantState(
            name="탱커",
            job="기사",
            hp=1200,
            max_hp=1500,
            mp=30,
            max_mp=80,
            brv=100,
            max_brv=1800,
            atb_percent=90,
            is_alive=True,
            is_broken=False,
            status_effects=["도발"],
            gimmick_value=5,
            gimmick_name="의무"
        ),
    ]
    
    # 적
    enemies = [
        CombatantState(
            name="고블린 전사",
            job="적",
            hp=400,
            max_hp=500,
            mp=0,
            max_mp=0,
            brv=150,
            max_brv=800,
            atb_percent=60,
            is_alive=True,
            is_broken=False,
            status_effects=[]
        ),
        CombatantState(
            name="고블린 주술사",
            job="적",
            hp=200,
            max_hp=300,
            mp=50,
            max_mp=100,
            brv=50,  # BRV 낮음 -> BREAK 가능
            max_brv=600,
            atb_percent=80,
            is_alive=True,
            is_broken=False,
            status_effects=[]
        ),
        CombatantState(
            name="고블린 대장",
            job="보스",
            hp=1500,
            max_hp=2000,
            mp=100,
            max_mp=100,
            brv=0,  # BREAK 상태!
            max_brv=1500,
            atb_percent=30,
            is_alive=True,
            is_broken=True,  # BREAK!
            status_effects=["방어력 하락"]
        ),
    ]
    
    # 스킬
    skills = [
        SkillInfo(
            id="power_slash",
            name="파워 슬래시",
            mp_cost=15,
            skill_type="brv",
            element="none",
            target_type="single",
            description="강력한 BRV 공격"
        ),
        SkillInfo(
            id="cross_slash",
            name="크로스 슬래시",
            mp_cost=25,
            skill_type="brv_hp",
            element="none",
            target_type="single",
            description="BRV+HP 연속 공격"
        ),
        SkillInfo(
            id="war_cry",
            name="전투 함성",
            mp_cost=20,
            skill_type="buff",
            element="none",
            target_type="all_allies",
            description="파티 공격력 증가"
        ),
    ]
    
    # 아이템
    items = [
        ItemInfo(
            id="potion",
            name="포션",
            quantity=5,
            effect="HP 200 회복"
        ),
        ItemInfo(
            id="ether",
            name="에테르",
            quantity=3,
            effect="MP 50 회복"
        ),
        ItemInfo(
            id="phoenix_down",
            name="피닉스의 깃털",
            quantity=1,
            effect="부활 + HP 50% 회복"
        ),
    ]
    
    return CombatState(
        turn_count=5,
        current_actor="전사봇",
        allies=allies,
        enemies=enemies,
        available_skills=skills,
        available_items=items,
        can_flee=True,
        environment="고블린 동굴"
    )


def test_prompt_generation():
    """프롬프트 생성 테스트"""
    print("=" * 60)
    print("프롬프트 생성 테스트")
    print("=" * 60)
    
    state = create_mock_combat_state()
    job_info = JOB_DATABASE.get("warrior", {})
    
    prompt = create_combat_prompt(state, job_info)
    
    print("\n[시스템 프롬프트]")
    print(SYSTEM_PROMPT[:500] + "...")
    print("\n[전투 상황 프롬프트]")
    print(prompt)
    print("\n✅ 프롬프트 생성 성공!")
    
    return True


def test_ollama_connection():
    """Ollama 연결 테스트"""
    print("\n" + "=" * 60)
    print("Ollama 연결 테스트")
    print("=" * 60)
    
    connected = test_ollama_connection_sync()
    
    if connected:
        print("✅ Ollama 연결 성공!")
    else:
        print("❌ Ollama 연결 실패 - Ollama가 실행 중인지 확인하세요")
        print("   설치: https://ollama.ai")
        print("   실행: ollama serve")
        print("   모델 다운로드: ollama pull llama3.2")
    
    return connected


def test_llm_bot_decision():
    """LLM 봇 의사결정 테스트"""
    print("\n" + "=" * 60)
    print("LLM 봇 의사결정 테스트")
    print("=" * 60)
    
    # Ollama 연결 확인
    if not test_ollama_connection_sync():
        print("⚠️ Ollama 연결 없음 - 폴백 테스트만 수행")
        
        # 폴백 테스트
        bot = create_llm_bot("테스트봇", "warrior", "qwen3:4b")
        state = create_mock_combat_state()
        
        # 강제로 LLM 실패 시뮬레이션
        action = bot._fallback_action(state)
        print(f"\n[폴백 행동]")
        print(f"  행동: {action.action_type.value}")
        print(f"  타겟: {action.target_name}")
        print(f"  이유: {action.reasoning}")
        print("✅ 폴백 로직 정상 동작!")
        return True
    
    # LLM 봇 생성
    bot = create_llm_bot("전사봇", "warrior", "qwen3:4b")
    
    # 전투 상태 생성
    state = create_mock_combat_state()
    
    print("\n[전투 상황]")
    print(f"  턴: {state.turn_count}")
    print(f"  현재 행동자: {state.current_actor}")
    print(f"  아군: {[a.name for a in state.allies]}")
    print(f"  적: {[e.name + (' (BREAK!)' if e.is_broken else '') for e in state.enemies]}")
    
    # 의사결정
    print("\n[LLM 의사결정 중...]")
    import time
    start = time.time()
    
    action = bot.decide_combat_action(state)
    
    elapsed = time.time() - start
    
    print(f"\n[결정된 행동] (소요시간: {elapsed:.2f}초)")
    print(f"  행동: {action.action_type.value}")
    print(f"  타겟: {action.target_name}")
    if action.skill_id:
        print(f"  스킬: {action.skill_id}")
    if action.item_id:
        print(f"  아이템: {action.item_id}")
    print(f"  이유: {action.reasoning}")
    
    # 통계
    stats = bot.get_stats()
    print(f"\n[봇 통계]")
    print(f"  총 행동: {stats['total_actions']}")
    print(f"  성공률: {stats['success_rate']}")
    
    print("\n✅ LLM 봇 의사결정 테스트 완료!")
    return True


def test_multiple_scenarios():
    """다양한 시나리오 테스트"""
    print("\n" + "=" * 60)
    print("다양한 시나리오 테스트")
    print("=" * 60)
    
    if not test_ollama_connection_sync():
        print("⚠️ Ollama 연결 없음 - 스킵")
        return True
    
    bot = create_llm_bot("테스트봇", "warrior", "qwen3:4b")
    
    scenarios = [
        {
            "name": "위험 상황 (HP 낮음)",
            "modify": lambda s: setattr(s.allies[0], 'hp', 100) or s
        },
        {
            "name": "BREAK 기회 (적 BRV 낮음)", 
            "modify": lambda s: setattr(s.enemies[0], 'brv', 30) or s
        },
        {
            "name": "HP 공격 기회 (BRV 높음)",
            "modify": lambda s: setattr(s.allies[0], 'brv', 1500) or s
        },
    ]
    
    for scenario in scenarios:
        print(f"\n[시나리오: {scenario['name']}]")
        state = create_mock_combat_state()
        scenario["modify"](state)
        
        action = bot.decide_combat_action(state)
        print(f"  결정: {action.action_type.value} -> {action.target_name}")
        print(f"  이유: {action.reasoning[:80]}...")
    
    print("\n✅ 다양한 시나리오 테스트 완료!")
    return True


def main():
    """메인 테스트"""
    print("\n" + "=" * 60)
    print("🎮 LLM 플레이어 봇 테스트 시작")
    print("=" * 60)
    
    tests = [
        ("프롬프트 생성", test_prompt_generation),
        ("Ollama 연결", test_ollama_connection),
        ("LLM 봇 의사결정", test_llm_bot_decision),
        ("다양한 시나리오", test_multiple_scenarios),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"  {name}: {status}")
    
    all_passed = all(r for _, r in results)
    print("\n" + ("🎉 모든 테스트 통과!" if all_passed else "⚠️ 일부 테스트 실패"))
    
    return all_passed


if __name__ == "__main__":
    main()
