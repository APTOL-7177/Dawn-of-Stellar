"""전투 플레이 로그 수집 스크립트

Gym 환경에서 랜덤/휴리스틱 정책으로 전투를 자동 실행하여
BC(행동 복제) 학습용 플레이 로그를 수집합니다.

사용법:
    # 랜덤 정책으로 500판 수집
    python training/collect_play_logs.py --episodes 500

    # 휴리스틱 정책으로 1000판 수집
    python training/collect_play_logs.py --episodes 1000 --policy heuristic

    # OpenAI LLM으로 100판 수집 (고품질, API 비용 발생)
    python training/collect_play_logs.py --episodes 100 --policy llm
"""

import argparse
import sys
import os
import json
import time
import random
import numpy as np
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def collect_with_gym(n_episodes: int, policy: str, output_dir: str) -> dict:
    """Gym 환경에서 플레이 로그 수집

    Args:
        n_episodes: 수집할 에피소드 수
        policy: 정책 유형 ("random", "heuristic", "llm")
        output_dir: 로그 저장 디렉토리

    Returns:
        수집 통계 딕셔너리
    """
    from src.gym.combat_env import CombatEnv
    from src.gym.state_encoder import StateEncoder
    from src.gym.action_space import ActionSpaceEncoder

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path(output_dir) / f"play_log_{policy}_{timestamp}.jsonl"

    env = CombatEnv(max_turns=200)

    stats = {
        "episodes": 0,
        "wins": 0,
        "defeats": 0,
        "truncated": 0,
        "total_steps": 0,
        "total_reward": 0.0,
    }

    print(f"수집 시작: {n_episodes}판, 정책={policy}")
    print(f"로그 저장: {log_path}")

    start_time = time.time()

    with open(log_path, "w", encoding="utf-8") as f:
        for ep in range(n_episodes):
            obs, info = env.reset(seed=ep)
            episode_id = f"ep_{timestamp}_{ep:05d}"
            episode_reward = 0.0
            step_count = 0
            done = False

            while not done:
                mask = env.action_masks()
                valid_actions = np.where(mask)[0]

                if len(valid_actions) == 0:
                    break

                # 정책에 따른 행동 선택
                if policy == "heuristic":
                    action = _heuristic_select(valid_actions, obs, env)
                else:
                    action = int(np.random.choice(valid_actions))

                # 로그 기록
                record = {
                    "episode_id": episode_id,
                    "turn": step_count,
                    "state": obs.tolist(),
                    "action": int(action),
                    "valid_actions": valid_actions.tolist(),
                }

                new_obs, reward, terminated, truncated, step_info = env.step(action)

                record["reward"] = float(reward)
                record["done"] = terminated or truncated

                f.write(json.dumps(record, ensure_ascii=False) + "\n")

                obs = new_obs
                episode_reward += reward
                step_count += 1
                done = terminated or truncated

            # 에피소드 통계
            stats["episodes"] += 1
            stats["total_steps"] += step_count
            stats["total_reward"] += episode_reward

            result = step_info.get("result", "unknown") if step_info else "unknown"
            if result == "victory":
                stats["wins"] += 1
            elif result == "defeat":
                stats["defeats"] += 1
            else:
                stats["truncated"] += 1

            # 진행률 표시 (50판마다)
            if (ep + 1) % 50 == 0:
                elapsed = time.time() - start_time
                eps_per_sec = (ep + 1) / elapsed
                eta = (n_episodes - ep - 1) / eps_per_sec
                print(
                    f"  [{ep+1}/{n_episodes}] "
                    f"승리={stats['wins']} 패배={stats['defeats']} "
                    f"스텝={stats['total_steps']} "
                    f"({eps_per_sec:.1f}판/초, ETA {eta:.0f}초)"
                )

    env.close()

    elapsed = time.time() - start_time
    stats["elapsed_seconds"] = elapsed
    stats["log_path"] = str(log_path)

    return stats


def _heuristic_select(valid_actions: np.ndarray, obs: np.ndarray, env) -> int:
    """휴리스틱 정책: 규칙 기반 행동 선택

    - BRV가 높으면 HP_ATTACK (BRV 소진 공격)
    - 아군 HP가 낮으면 DEFEND
    - 스킬이 유효하면 스킬 우선 사용
    - 기본: BRV_ATTACK
    """
    # 현재 캐릭터 정보 (첫 번째 아군 슬롯 기준)
    hp_ratio = obs[0]    # HP 비율
    brv_ratio = obs[2]   # BRV 비율

    # 행동 분류
    brv_attacks = [a for a in valid_actions if 0 <= a <= 3]
    hp_attacks = [a for a in valid_actions if 4 <= a <= 7]
    defend = [a for a in valid_actions if a == 8]
    skills = [a for a in valid_actions if 10 <= a <= 41]

    # 결정 로직
    # BRV가 충분하면 (>50%) HP 공격으로 데미지
    if brv_ratio > 0.5 and hp_attacks:
        return int(random.choice(hp_attacks))

    # HP가 낮으면 (<30%) 방어
    if hp_ratio < 0.3 and defend:
        return int(defend[0])

    # 스킬 사용 (40% 확률)
    if skills and random.random() < 0.4:
        return int(random.choice(skills))

    # 기본: BRV 공격
    if brv_attacks:
        return int(random.choice(brv_attacks))

    # 폴백: 유효한 아무 행동
    return int(random.choice(valid_actions))


def collect_with_llm(n_episodes: int, output_dir: str) -> dict:
    """LLM 봇으로 고품질 플레이 로그 수집

    Args:
        n_episodes: 수집할 에피소드 수
        output_dir: 로그 저장 디렉토리

    Returns:
        수집 통계 딕셔너리
    """
    from src.gym.combat_env import CombatEnv
    from src.gym.action_space import ActionSpaceEncoder

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("오류: OPENAI_API_KEY 환경변수를 설정하세요.")
        sys.exit(1)

    from src.ai.openai_client import OpenAIClientSync, OpenAIConfig
    from src.ai.job_prompts import get_combat_system_prompt

    client = OpenAIClientSync(OpenAIConfig(api_key=api_key))

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path(output_dir) / f"play_log_llm_{timestamp}.jsonl"

    env = CombatEnv(max_turns=200)

    stats = {
        "episodes": 0, "wins": 0, "defeats": 0,
        "truncated": 0, "total_steps": 0, "total_reward": 0.0,
    }

    print(f"LLM 수집 시작: {n_episodes}판")
    print(f"모델: {client.config.model}")
    print(f"로그 저장: {log_path}")

    start_time = time.time()

    with open(log_path, "w", encoding="utf-8") as f:
        for ep in range(n_episodes):
            obs, info = env.reset(seed=ep)
            episode_id = f"ep_llm_{timestamp}_{ep:05d}"
            episode_reward = 0.0
            step_count = 0
            done = False

            # 현재 캐릭터의 직업 정보로 시스템 프롬프트 생성
            cm = env.headless_combat.combat_manager
            current_job = "warrior"
            if env.current_char and hasattr(env.current_char, "job_id"):
                current_job = env.current_char.job_id

            system_prompt = get_combat_system_prompt(current_job)

            while not done:
                mask = env.action_masks()
                valid_actions = np.where(mask)[0]

                if len(valid_actions) == 0:
                    break

                # LLM에게 행동 요청
                action = _llm_select_action(
                    client, system_prompt, obs, valid_actions, env
                )

                record = {
                    "episode_id": episode_id,
                    "turn": step_count,
                    "state": obs.tolist(),
                    "action": int(action),
                    "valid_actions": valid_actions.tolist(),
                }

                new_obs, reward, terminated, truncated, step_info = env.step(action)
                record["reward"] = float(reward)
                record["done"] = terminated or truncated
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

                obs = new_obs
                episode_reward += reward
                step_count += 1
                done = terminated or truncated

            stats["episodes"] += 1
            stats["total_steps"] += step_count
            stats["total_reward"] += episode_reward

            result = step_info.get("result", "unknown") if step_info else "unknown"
            if result == "victory":
                stats["wins"] += 1
            elif result == "defeat":
                stats["defeats"] += 1
            else:
                stats["truncated"] += 1

            if (ep + 1) % 10 == 0:
                elapsed = time.time() - start_time
                print(
                    f"  [{ep+1}/{n_episodes}] "
                    f"승리={stats['wins']} 패배={stats['defeats']} "
                    f"비용=${client.usage.total_cost:.4f}"
                )

    env.close()

    elapsed = time.time() - start_time
    stats["elapsed_seconds"] = elapsed
    stats["log_path"] = str(log_path)
    stats["api_cost"] = client.usage.total_cost

    return stats


def _llm_select_action(client, system_prompt, obs, valid_actions, env) -> int:
    """LLM으로 행동 선택"""
    # 간단한 상태 요약 생성
    cm = env.headless_combat.combat_manager

    allies_info = []
    for a in cm.allies:
        if getattr(a, "is_alive", False):
            hp_pct = getattr(a, "current_hp", 0) / max(getattr(a, "max_hp", 1), 1) * 100
            brv = getattr(a, "current_brv", 0)
            allies_info.append(f"{a.name}(HP:{hp_pct:.0f}% BRV:{brv})")

    enemies_info = []
    for e in cm.enemies:
        if getattr(e, "is_alive", False):
            hp_pct = getattr(e, "current_hp", 0) / max(getattr(e, "max_hp", 1), 1) * 100
            brv = getattr(e, "current_brv", 0)
            enemies_info.append(f"{getattr(e, 'name', '적')}(HP:{hp_pct:.0f}% BRV:{brv})")

    # 행동 설명 (인라인)
    action_desc = []
    for a_id in valid_actions[:15]:
        a = int(a_id)
        if 0 <= a <= 3:
            desc = f"BRV공격→적{a}"
        elif 4 <= a <= 7:
            desc = f"HP공격→적{a-4}"
        elif a == 8:
            desc = "방어"
        elif a == 9:
            desc = "도주"
        elif 10 <= a <= 41:
            skill_idx = (a - 10) // 4
            target_idx = (a - 10) % 4
            desc = f"스킬{skill_idx}→대상{target_idx}"
        elif 42 <= a <= 45:
            desc = f"아이템{a-42}"
        else:
            desc = f"행동{a}"
        action_desc.append(f"{a}: {desc}")

    prompt = f"""전투 상황:
아군: {', '.join(allies_info)}
적: {', '.join(enemies_info)}

가능한 행동:
{chr(10).join(action_desc)}

최적의 행동 번호만 JSON으로 답하세요: {{"action": 숫자}}"""

    try:
        response = client.generate(prompt, system_prompt)
        data = json.loads(response)
        chosen = int(data.get("action", valid_actions[0]))
        if chosen in valid_actions:
            return chosen
    except Exception:
        pass

    # 폴백: 휴리스틱
    return _heuristic_select(valid_actions, obs, env)


def main():
    parser = argparse.ArgumentParser(
        description="Dawn of Stellar 전투 플레이 로그 수집",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--episodes", type=int, default=500, help="수집할 에피소드 수")
    parser.add_argument(
        "--policy", choices=["random", "heuristic", "llm"],
        default="heuristic", help="행동 선택 정책"
    )
    parser.add_argument("--output-dir", type=str, default="data/play_logs", help="로그 저장 디렉토리")
    args = parser.parse_args()

    print("=" * 55)
    print("Dawn of Stellar - 전투 플레이 로그 수집")
    print("=" * 55)

    if args.policy == "llm":
        stats = collect_with_llm(args.episodes, args.output_dir)
    else:
        stats = collect_with_gym(args.episodes, args.policy, args.output_dir)

    # 결과 출력
    print()
    print("=" * 55)
    print("수집 결과")
    print("=" * 55)
    print(f"  에피소드:   {stats['episodes']}판")
    print(f"  승리:       {stats['wins']}판 ({stats['wins']/max(stats['episodes'],1)*100:.1f}%)")
    print(f"  패배:       {stats['defeats']}판")
    print(f"  시간초과:   {stats['truncated']}판")
    print(f"  총 스텝:    {stats['total_steps']:,}")
    print(f"  평균 보상:  {stats['total_reward']/max(stats['episodes'],1):.2f}")
    print(f"  소요 시간:  {stats['elapsed_seconds']:.1f}초")
    print(f"  로그 파일:  {stats['log_path']}")
    if "api_cost" in stats:
        print(f"  API 비용:   ${stats['api_cost']:.4f}")

    # 다음 단계 안내
    print()
    print("다음 단계:")
    print(f"  BC 학습:  python training/train.py --phase bc")
    print(f"  PPO 훈련: python training/train.py --phase ppo --timesteps 5000000")


if __name__ == "__main__":
    main()
