"""
스킬 시뮬레이션 테스트 - 모든 직업 스킬의 실제 동작 검증
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from colorama import init, Fore, Style
init()

# 설정 초기화
from src.core.config import initialize_config
initialize_config()

from src.character.skills.skill_manager import get_skill_manager
from src.character.character import Character
from src.character.gimmick_updater import GimmickUpdater


def print_header(text):
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f" {text}")
    print(f"{'='*60}{Style.RESET_ALL}")

def print_ok(text):
    print(f"  {Fore.GREEN}[OK]{Style.RESET_ALL} {text}")

def print_error(text):
    print(f"  {Fore.RED}[ERR]{Style.RESET_ALL} {text}")

def print_info(text):
    print(f"  {Fore.BLUE}[INFO]{Style.RESET_ALL} {text}")


class MockTarget:
    """테스트용 가짜 대상"""
    def __init__(self, name="Target"):
        self.name = name
        self.current_hp = 100
        self.max_hp = 100
        self.current_brv = 50
        self.max_brv = 200
        self.active_buffs = {}
        self.is_alive = True


class SkillSimulationTester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def test_rogue_ambush(self):
        """도적 기습: 자신에게 크리티컬 버프"""
        print_info("도적 기습 테스트...")
        
        from src.character.skills.job_skills.rogue_skills import create_rogue_skills
        skills = create_rogue_skills()
        ambush = skills[0]
        
        user = MockTarget("도적")
        user.active_buffs = {}
        target = MockTarget("적")
        target.active_buffs = {}
        
        # 스킬 실행
        context = {}
        for effect in ambush.effects:
            if hasattr(effect, 'execute'):
                effect.execute(user, target, context)
        
        # 검증: 자신에게 크리티컬 버프
        if user.active_buffs.get('critical_up'):
            print_ok("자신에게 크리티컬 버프 적용됨")
            self.passed += 1
        else:
            print_error("자신에게 크리티컬 버프 미적용!")
            self.failed += 1
            self.errors.append("도적 기습: 자신에게 버프 미적용")
        
        if target.active_buffs.get('critical_up'):
            print_error("적에게 크리티컬 버프가 잘못 적용됨!")
            self.failed += 1
            self.errors.append("도적 기습: 적에게 버프 잘못 적용")
        else:
            print_ok("적에게 버프 미적용 (정상)")
            self.passed += 1
    
    def test_bard_note_generation(self):
        """바드 음표 생성"""
        print_info("바드 음표 생성 테스트...")
        
        from src.character.skills.job_skills.bard_skills import create_bard_skills
        skills = create_bard_skills()
        note_strike = skills[0]  # 음표 타격
        
        # 바드 캐릭터 시뮬레이션
        user = MockTarget("바드")
        user.gimmick_type = "score_composition"
        user.music_notes = []
        user.max_notes = 5
        
        # GimmickUpdater 호출
        GimmickUpdater.on_skill_use(user, note_strike)
        
        if user.music_notes and 'A' in user.music_notes:
            print_ok(f"음표 생성됨: {user.music_notes}")
            self.passed += 1
        else:
            print_error(f"음표 미생성! (현재: {user.music_notes})")
            self.failed += 1
            self.errors.append("바드: 음표 생성 실패")
    
    def test_magician_card_draw(self):
        """마술사 카드 드로우"""
        print_info("마술사 카드 드로우 테스트...")
        
        from src.character.skills.job_skills.magician_skills import create_magician_skills, initialize_trick_deck
        skills = create_magician_skills()
        card_slash = skills[0]  # 카드 슬래시
        
        # 마술사 캐릭터 시뮬레이션
        user = MockTarget("마술사")
        user.gimmick_type = "trick_deck"
        initialize_trick_deck(user)
        
        initial_hand = len(user.card_hand)
        
        # GimmickUpdater 호출
        GimmickUpdater.on_skill_use(user, card_slash)
        
        if len(user.card_hand) > initial_hand:
            print_ok(f"카드 드로우 성공: {initial_hand} -> {len(user.card_hand)}장")
            self.passed += 1
        else:
            print_error(f"카드 드로우 실패! (손패: {len(user.card_hand)}장)")
            self.failed += 1
            self.errors.append("마술사: 카드 드로우 실패")
    
    def test_warrior_buff_target(self):
        """전사 격노의 일격: 자신에게 버프"""
        print_info("전사 격노의 일격 테스트...")
        
        from src.character.skills.job_skills.warrior_skills import create_warrior_skills
        skills = create_warrior_skills()
        
        # 격노의 일격 찾기
        furious = None
        for s in skills:
            if s.skill_id == "warrior_furious_strike":
                furious = s
                break
        
        if not furious:
            print_error("격노의 일격 스킬을 찾을 수 없음!")
            self.failed += 1
            return
        
        user = MockTarget("전사")
        user.active_buffs = {}
        target = MockTarget("적")
        target.active_buffs = {}
        
        context = {}
        for effect in furious.effects:
            if hasattr(effect, 'execute'):
                try:
                    effect.execute(user, target, context)
                except:
                    pass  # DamageEffect는 실제 전투 시스템 필요
        
        if user.active_buffs.get('attack_up'):
            print_ok("자신에게 공격력 버프 적용됨")
            self.passed += 1
        else:
            print_error("자신에게 공격력 버프 미적용!")
            self.failed += 1
            self.errors.append("전사 격노의 일격: 자신에게 버프 미적용")
    
    def test_sfx_coverage(self):
        """모든 스킬 SFX 설정 확인"""
        print_info("SFX 설정 검사...")
        
        import os
        import re
        
        skill_dir = 'src/character/skills/job_skills'
        files = [f for f in os.listdir(skill_dir) 
                if f.endswith('_skills.py') and not f.startswith('__')]
        
        missing_sfx = []
        
        for filename in files:
            filepath = os.path.join(skill_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skill 정의 찾기
            skill_pattern = r'(\w+)\s*=\s*Skill\(\s*["\']([^"\']+)["\']'
            for match in re.finditer(skill_pattern, content):
                var_name = match.group(1)
                skill_id = match.group(2)
                
                # .sfx 설정 확인
                sfx_pattern = rf'{var_name}\.sfx\s*='
                if not re.search(sfx_pattern, content):
                    job = filename.replace('_skills.py', '')
                    missing_sfx.append(f"{job}: {skill_id}")
        
        if missing_sfx:
            print_error(f"SFX 미설정 스킬 {len(missing_sfx)}개:")
            for m in missing_sfx[:10]:
                print(f"    - {m}")
            if len(missing_sfx) > 10:
                print(f"    ... 외 {len(missing_sfx) - 10}개")
            self.failed += 1
            self.errors.extend(missing_sfx)
        else:
            print_ok("모든 스킬에 SFX 설정됨")
            self.passed += 1
    
    def test_buff_targets(self):
        """공격 스킬의 버프 타겟 확인"""
        print_info("버프 타겟 검사...")
        
        import os
        import re
        
        skill_dir = 'src/character/skills/job_skills'
        files = [f for f in os.listdir(skill_dir) 
                if f.endswith('_skills.py') and not f.startswith('__')]
        
        issues = []
        
        for filename in files:
            filepath = os.path.join(skill_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skill 정의 찾기
            skill_pattern = r'(\w+)\s*=\s*Skill\(\s*["\']([^"\']+)["\']'
            for match in re.finditer(skill_pattern, content):
                var_name = match.group(1)
                skill_id = match.group(2)
                
                # 스킬 블록 추출
                start_idx = match.start()
                end_match = re.search(rf'(?:skills\.append\({var_name}\)|return\s*\[)', content[start_idx:])
                if end_match:
                    end_idx = start_idx + end_match.start()
                else:
                    end_idx = start_idx + 1500
                
                block = content[start_idx:end_idx]
                
                # DamageEffect가 있는지 (공격 스킬)
                has_damage = 'DamageEffect' in block
                if not has_damage:
                    continue
                
                # target_type = "self"인지
                is_self_target = 'target_type = "self"' in block
                if is_self_target:
                    continue
                
                # BuffEffect 검사
                buff_types = ['ATTACK_UP', 'MAGIC_UP', 'DEFENSE_UP', 'SPEED_UP', 
                            'EVASION_UP', 'CRITICAL_UP', 'SPIRIT_UP', 'ACCURACY_UP']
                
                for bt in buff_types:
                    pattern = rf'BuffEffect\(BuffType\.{bt}[^)]*\)'
                    for buff_match in re.finditer(pattern, block):
                        buff_line = buff_match.group(0)
                        if 'target="self"' not in buff_line and 'is_party_wide=True' not in buff_line:
                            job = filename.replace('_skills.py', '')
                            issues.append(f"{job}: {skill_id} - {bt}")
        
        if issues:
            print_error(f"버프 타겟 오류 {len(issues)}개:")
            for i in issues[:5]:
                print(f"    - {i}")
            if len(issues) > 5:
                print(f"    ... 외 {len(issues) - 5}개")
            self.failed += len(issues)
            self.errors.extend(issues)
        else:
            print_ok("모든 버프 타겟 정상")
            self.passed += 1
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print_header("스킬 시뮬레이션 테스트")
        
        try:
            self.test_rogue_ambush()
        except Exception as e:
            print_error(f"도적 테스트 실패: {e}")
            self.failed += 1
        
        try:
            self.test_bard_note_generation()
        except Exception as e:
            print_error(f"바드 테스트 실패: {e}")
            self.failed += 1
        
        try:
            self.test_magician_card_draw()
        except Exception as e:
            print_error(f"마술사 테스트 실패: {e}")
            self.failed += 1
        
        try:
            self.test_warrior_buff_target()
        except Exception as e:
            print_error(f"전사 테스트 실패: {e}")
            self.failed += 1
        
        try:
            self.test_sfx_coverage()
        except Exception as e:
            print_error(f"SFX 테스트 실패: {e}")
            self.failed += 1
        
        try:
            self.test_buff_targets()
        except Exception as e:
            print_error(f"버프 타겟 테스트 실패: {e}")
            self.failed += 1
        
        # 결과 출력
        print_header("테스트 결과")
        
        total = self.passed + self.failed
        
        if self.failed == 0:
            print(f"\n{Fore.GREEN}{'='*60}")
            print(f"  [PASS] 모든 테스트 통과! ({self.passed}/{total})")
            print(f"{'='*60}{Style.RESET_ALL}")
            return True
        else:
            print(f"\n{Fore.RED}{'='*60}")
            print(f"  [FAIL] 테스트 실패")
            print(f"  - 성공: {self.passed}")
            print(f"  - 실패: {self.failed}")
            print(f"{'='*60}{Style.RESET_ALL}")
            
            if self.errors:
                print(f"\n{Fore.RED}오류 목록:{Style.RESET_ALL}")
                for err in self.errors[:20]:
                    print(f"  - {err}")
            
            return False


def main():
    print(f"\n{Fore.MAGENTA}{'#'*60}")
    print(f"#  스킬 시뮬레이션 테스트")
    print(f"#  Dawn of Stellar")
    print(f"{'#'*60}{Style.RESET_ALL}")
    
    tester = SkillSimulationTester()
    success = tester.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
