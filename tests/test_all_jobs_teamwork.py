"""
모든 직업의 팀워크 스킬 테스트

33개 직업 모두의 팀워크 스킬이 올바르게 생성되었는지 검증합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 설정 초기화
try:
    from src.core.config import Config
    Config()  # 설정 로드
except Exception as e:
    print(f"[경고] 설정 로드 실패: {e}")
    pass  # 설정이 없어도 스킬 생성은 가능

from src.character.skills.job_skills.warrior_skills import create_warrior_skills
from src.character.skills.job_skills.paladin_skills import create_paladin_skills
from src.character.skills.job_skills.knight_skills import create_knight_skills
from src.character.skills.job_skills.dark_knight_skills import create_dark_knight_skills
from src.character.skills.job_skills.archer_skills import create_archer_skills
from src.character.skills.job_skills.sniper_skills import create_sniper_skills
from src.character.skills.job_skills.monk_skills import create_monk_skills
from src.character.skills.job_skills.berserker_skills import create_berserker_skills
from src.character.skills.job_skills.gladiator_skills import create_gladiator_skills
from src.character.skills.job_skills.samurai_skills import create_samurai_skills
from src.character.skills.job_skills.dragon_knight_skills import create_dragon_knight_skills
from src.character.skills.job_skills.battle_mage_skills import create_battle_mage_skills
from src.character.skills.job_skills.spellblade_skills import create_spellblade_skills
from src.character.skills.job_skills.time_mage_skills import create_time_mage_skills
from src.character.skills.job_skills.elementalist_skills import create_elementalist_skills
from src.character.skills.job_skills.philosopher_skills import create_philosopher_skills
from src.character.skills.job_skills.dimensionist_skills import create_dimensionist_skills
from src.character.skills.job_skills.cleric_skills import create_cleric_skills
from src.character.skills.job_skills.priest_skills import create_priest_skills
from src.character.skills.job_skills.shaman_skills import create_shaman_skills
from src.character.skills.job_skills.druid_skills import create_druid_skills
from src.character.skills.job_skills.bard_skills import create_bard_skills
from src.character.skills.job_skills.engineer_skills import create_engineer_skills
from src.character.skills.job_skills.alchemist_skills import create_alchemist_skills
from src.character.skills.job_skills.archmage_skills import create_archmage_skills
from src.character.skills.job_skills.breaker_skills import create_breaker_skills
from src.character.skills.job_skills.vampire_skills import create_vampire_skills
from src.character.skills.job_skills.necromancer_skills import create_necromancer_skills
from src.character.skills.job_skills.assassin_skills import create_assassin_skills
from src.character.skills.job_skills.rogue_skills import create_rogue_skills
from src.character.skills.job_skills.pirate_skills import create_pirate_skills
from src.character.skills.job_skills.hacker_skills import create_hacker_skills
from src.character.skills.job_skills.sword_saint_skills import create_sword_saint_skills


# 직업 목록
JOBS = [
    ("전사", "warrior", create_warrior_skills),
    ("성기사", "paladin", create_paladin_skills),
    ("기사", "knight", create_knight_skills),
    ("암흑기사", "dark_knight", create_dark_knight_skills),
    ("궁수", "archer", create_archer_skills),
    ("저격수", "sniper", create_sniper_skills),
    ("monk", "monk", create_monk_skills),
    ("버서커", "berserker", create_berserker_skills),
    ("검투사", "gladiator", create_gladiator_skills),
    ("사무라이", "samurai", create_samurai_skills),
    ("용기사", "dragon_knight", create_dragon_knight_skills),
    ("배틀메이지", "battle_mage", create_battle_mage_skills),
    ("마검사", "spellblade", create_spellblade_skills),
    ("시간술사", "time_mage", create_time_mage_skills),
    ("원소술사", "elementalist", create_elementalist_skills),
    ("철학자", "philosopher", create_philosopher_skills),
    ("차원술사", "dimensionist", create_dimensionist_skills),
    ("성직자", "cleric", create_cleric_skills),
    ("사제", "priest", create_priest_skills),
    ("주술사", "shaman", create_shaman_skills),
    ("드루이드", "druid", create_druid_skills),
    ("음유시인", "bard", create_bard_skills),
    ("기계공학자", "engineer", create_engineer_skills),
    ("연금술사", "alchemist", create_alchemist_skills),
    ("대마법사", "archmage", create_archmage_skills),
    ("파괴자", "breaker", create_breaker_skills),
    ("뱀파이어", "vampire", create_vampire_skills),
    ("죽음의 군주", "necromancer", create_necromancer_skills),
    ("암살자", "assassin", create_assassin_skills),
    ("로그", "rogue", create_rogue_skills),
    ("해적", "pirate", create_pirate_skills),
    ("해커", "hacker", create_hacker_skills),
    ("검성", "sword_saint", create_sword_saint_skills),
]


class JobTeamworkTester:
    """직업별 팀워크 스킬 테스터"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def test_job(self, job_name: str, job_id: str, create_func) -> bool:
        """직업의 팀워크 스킬 테스트"""
        try:
            skills = create_func()

            # 팀워크 스킬 찾기
            teamwork = None
            for skill in skills:
                if hasattr(skill, 'is_teamwork_skill') and skill.is_teamwork_skill:
                    teamwork = skill
                    break

            if not teamwork:
                self.failed += 1
                self.results.append(("FAIL", f"{job_name}: 팀워크 스킬 없음"))
                return False

            # 팀워크 스킬 검증
            checks = [
                (teamwork.skill_id, f"스킬 ID 정의"),
                (teamwork.name, f"스킬 이름 정의"),
                (hasattr(teamwork, 'teamwork_cost'), f"팀워크 비용 정의"),
                (teamwork.teamwork_cost.gauge > 0, f"팀워크 비용 > 0"),
                (teamwork.teamwork_cost.gauge <= 300, f"팀워크 비용 <= 300"),
            ]

            for condition, desc in checks:
                if not condition:
                    self.failed += 1
                    self.results.append(("FAIL", f"{job_name}: {desc}"))
                    return False

            self.passed += 1
            self.results.append(("PASS", f"{job_name}: {teamwork.name} (비용: {teamwork.teamwork_cost.gauge})"))
            return True

        except Exception as e:
            self.failed += 1
            self.results.append(("FAIL", f"{job_name}: 예외 발생 - {str(e)}"))
            return False

    def run_all_tests(self) -> bool:
        """모든 직업 테스트"""
        print("\n" + "=" * 70)
        print("모든 직업의 팀워크 스킬 테스트")
        print("=" * 70)

        for job_name, job_id, create_func in JOBS:
            self.test_job(job_name, job_id, create_func)

        # 결과 출력
        self.print_results()
        return self.failed == 0

    def print_results(self):
        """결과 출력"""
        print("\n" + "=" * 70)
        print("[테스트 결과]")
        print("=" * 70)

        for status, message in self.results:
            symbol = "[OK]" if status == "PASS" else "[FAIL]"
            print(f"{symbol} {message}")

        print("\n" + "=" * 70)
        print(f"총 {self.passed + self.failed}개 직업")
        print(f"성공: {self.passed}")
        print(f"실패: {self.failed}")
        print("=" * 70)

        if self.failed == 0:
            print("\n[SUCCESS] 모든 직업의 팀워크 스킬 정의 완료!")
        else:
            print(f"\n[FAILED] {self.failed}개 직업에서 오류 발생")


def main():
    """메인 테스트 실행"""
    tester = JobTeamworkTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
