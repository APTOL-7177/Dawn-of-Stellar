"""기사 스킬 MP 조정 스크립트"""

import yaml
from pathlib import Path

SKILLS_DIR = Path("data/skills")

def adjust_knight_mp():
    """기사 YAML 스킬 MP 20% 감소"""
    knight_skills = sorted(SKILLS_DIR.glob("knight_*.yaml"))

    print("=" * 60)
    print("기사 스킬 MP 조정 (20% 감소)")
    print("=" * 60)

    adjusted_count = 0

    for skill_file in knight_skills:
        with skill_file.open('r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        costs = data.get('costs', {})
        mp_cost = costs.get('mp', 0)

        if mp_cost > 0:
            # MP 20% 감소 (반올림)
            new_mp = max(1, int(mp_cost * 0.8))

            if new_mp != mp_cost:
                costs['mp'] = new_mp
                data['costs'] = costs

                # 파일 저장
                with skill_file.open('w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

                print(f"[OK] {data.get('name', 'Unknown'):25} | {mp_cost} → {new_mp} MP")
                adjusted_count += 1

    print("=" * 60)
    print(f"총 {adjusted_count}개 스킬 조정 완료")


if __name__ == "__main__":
    adjust_knight_mp()
