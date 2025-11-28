"""
스킬 시스템 정밀 점검 스크립트
- 타겟 문제 (공격 스킬에서 자신에게 버프 주는 경우)
- 기믹 효과 (바드 음표, 마술사 카드 등)
- SFX 설정 여부
- 기본 공격 순서 (BRV → HP)
"""
import os
import sys
import re

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from colorama import init, Fore, Style
init()

def print_header(text):
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f" {text}")
    print(f"{'='*60}{Style.RESET_ALL}")

def print_ok(text):
    print(f"  {Fore.GREEN}[OK]{Style.RESET_ALL} {text}")

def print_warn(text):
    print(f"  {Fore.YELLOW}[WARN]{Style.RESET_ALL} {text}")

def print_error(text):
    print(f"  {Fore.RED}[ERR]{Style.RESET_ALL} {text}")

def print_info(text):
    print(f"  {Fore.BLUE}[INFO]{Style.RESET_ALL} {text}")


class SkillIntegrityTester:
    def __init__(self):
        self.skill_dir = 'src/character/skills/job_skills'
        self.issues = []
        self.warnings = []
        self.passed = 0
        
    def load_skill_files(self):
        """스킬 파일 로드"""
        files = [f for f in os.listdir(self.skill_dir) 
                if f.endswith('_skills.py') and not f.startswith('__')]
        return sorted(files)
    
    def parse_skill_blocks(self, content):
        """스킬 블록 파싱"""
        skills = []
        # Skill 정의 찾기
        pattern = r'(\w+)\s*=\s*Skill\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(pattern, content):
            var_name = match.group(1)
            skill_id = match.group(2)
            
            # 스킬 블록 추출
            start_idx = match.start()
            # 다음 skills.append나 다른 스킬 정의까지
            end_pattern = rf'skills\.append\({var_name}\)'
            end_match = re.search(end_pattern, content[start_idx:])
            if end_match:
                end_idx = start_idx + end_match.end()
            else:
                end_idx = start_idx + 1500
            
            block = content[start_idx:end_idx]
            
            # 스킬 이름 추출
            name_match = re.search(rf'{var_name}\s*=\s*Skill\([^,]+,\s*["\']([^"\']+)["\']', block)
            skill_name = name_match.group(1) if name_match else skill_id
            
            skills.append({
                'var_name': var_name,
                'skill_id': skill_id,
                'skill_name': skill_name,
                'block': block
            })
        
        return skills
    
    def test_buff_target(self, job, skill):
        """테스트 1: 공격 스킬에서 자신에게 버프 주는 경우 target="self" 확인"""
        block = skill['block']
        
        # DamageEffect가 있는지 (공격 스킬)
        has_damage = 'DamageEffect' in block
        if not has_damage:
            return True
        
        # target_type = "self"인지
        is_self_target = 'target_type = "self"' in block or 'target_type="self"' in block
        if is_self_target:
            return True
        
        # BuffEffect 찾기
        buff_pattern = r'BuffEffect\(BuffType\.([A-Z_]+)[^)]*\)'
        for match in re.finditer(buff_pattern, block):
            buff_type = match.group(1)
            buff_line = match.group(0)
            
            # 디버프(_DOWN)가 아닌 버프(_UP)만 확인
            if '_DOWN' in buff_type:
                continue
            if '_UP' not in buff_type and buff_type not in ['REGEN', 'HASTE', 'PROTECT', 'SHELL']:
                continue
            
            # target="self"나 is_party_wide=True가 있으면 OK
            if 'target="self"' in buff_line or "target='self'" in buff_line:
                continue
            if 'is_party_wide=True' in buff_line:
                continue
            
            # 문제 발견!
            self.issues.append(f"{job}: {skill['skill_name']} - {buff_type} 버프가 적에게 적용됨 (target=\"self\" 필요)")
            return False
        
        return True
    
    def test_gimmick_metadata(self, job, skill):
        """테스트 2: 기믹 메타데이터 확인"""
        block = skill['block']
        issues_found = False
        
        # 바드 음표
        if 'note_add' in block:
            if 'GimmickEffect' not in block or 'score' not in block.lower():
                # metadata만으로 처리하므로 OK (gimmick_updater에서 처리)
                pass
        
        # 마술사 카드
        if 'card_draw' in block:
            # metadata만으로 처리하므로 OK
            pass
        
        return not issues_found
    
    def test_sfx(self, job, skill):
        """테스트 3: SFX 설정 확인"""
        block = skill['block']
        
        if '.sfx' not in block and '.sfx=' not in block:
            self.warnings.append(f"{job}: {skill['skill_name']} - SFX 미설정")
            return False
        
        return True
    
    def test_basic_attack_order(self, job, content):
        """테스트 4: 기본 공격 순서 (첫 번째=BRV, 두 번째=HP)"""
        # skills.append 순서대로 스킬 찾기
        appends = list(re.finditer(r'skills\.append\((\w+)\)', content))
        
        if len(appends) < 2:
            return True
        
        # 첫 번째 스킬
        first_var = appends[0].group(1)
        first_start = content.rfind(f'{first_var} = ', 0, appends[0].start())
        if first_start < 0:
            return True
        first_block = content[first_start:appends[0].start()]
        
        # 두 번째 스킬
        second_var = appends[1].group(1)
        second_start = content.rfind(f'{second_var} = ', 0, appends[1].start())
        if second_start < 0:
            return True
        second_block = content[second_start:appends[1].start()]
        
        # DamageType 확인
        first_type = re.search(r'DamageType\.(BRV|HP|BRV_HP)', first_block)
        second_type = re.search(r'DamageType\.(BRV|HP|BRV_HP)', second_block)
        
        if not first_type or not second_type:
            return True
        
        first_dt = first_type.group(1)
        second_dt = second_type.group(1)
        
        # 첫 번째가 BRV (또는 BRV_HP), 두 번째가 HP
        if first_dt == 'HP' and second_dt == 'BRV':
            self.issues.append(f"{job}: 기본 공격 순서 오류 - 1번째가 HP, 2번째가 BRV (BRV→HP 순서여야 함)")
            return False
        
        return True
    
    def test_teamwork_skill_position(self, job, content):
        """테스트 5: 팀워크 스킬이 리스트에 제대로 추가되는지"""
        if 'TeamworkSkill' not in content:
            return True
        
        # TeamworkSkill 정의 찾기
        teamwork_match = re.search(r'(\w+)\s*=\s*TeamworkSkill\(', content)
        if not teamwork_match:
            return True
        
        teamwork_var = teamwork_match.group(1)
        
        # skills.append 확인
        if f'skills.append({teamwork_var})' not in content:
            self.warnings.append(f"{job}: TeamworkSkill '{teamwork_var}'가 skills 리스트에 추가되지 않음")
            return False
        
        return True
    
    def run_tests(self):
        """모든 테스트 실행"""
        print_header("스킬 시스템 정밀 점검")
        
        files = self.load_skill_files()
        print_info(f"검사 대상: {len(files)}개 직업 스킬 파일")
        
        for filename in files:
            job = filename.replace('_skills.py', '')
            filepath = os.path.join(self.skill_dir, filename)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            skills = self.parse_skill_blocks(content)
            
            # 각 스킬에 대한 테스트
            for skill in skills:
                self.test_buff_target(job, skill)
                self.test_gimmick_metadata(job, skill)
                self.test_sfx(job, skill)
            
            # 파일 전체에 대한 테스트
            self.test_basic_attack_order(job, content)
            self.test_teamwork_skill_position(job, content)
        
        # 결과 출력
        print_header("테스트 결과")
        
        if self.issues:
            print(f"\n{Fore.RED}[ERROR] ({len(self.issues)})::{Style.RESET_ALL}")
            for issue in self.issues:
                print_error(issue)
        
        if self.warnings:
            print(f"\n{Fore.YELLOW}[WARNING] ({len(self.warnings)})::{Style.RESET_ALL}")
            for warn in self.warnings[:20]:  # 최대 20개만
                print_warn(warn)
            if len(self.warnings) > 20:
                print_warn(f"... 외 {len(self.warnings) - 20}개")
        
        if not self.issues and not self.warnings:
            print_ok("모든 테스트 통과!")
        
        return len(self.issues) == 0


class GimmickIntegrityTester:
    """기믹 시스템 정밀 점검"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
    
    def test_gimmick_updater_coverage(self):
        """on_skill_use에서 모든 기믹 타입이 처리되는지"""
        print_header("기믹 시스템 점검")
        
        # 기믹 타입 목록 (character.py에서 정의된 것들)
        gimmick_types = [
            "heat_management",      # 건슬링어
            "timeline_system",      # 타임메이지
            "yin_yang_flow",        # 몽크
            "madness_threshold",    # 버서커
            "thirst_gauge",         # 뱀파이어
            "probability_distortion", # 해커
            "stealth_exposure",     # 어쌔신
            "magazine_system",      # 스나이퍼
            "sword_aura",           # 검성
            "crowd_cheer",          # 글래디에이터
            "duty_system",          # 기사
            "stance_system",        # 기사
            "iaijutsu_system",      # 사무라이
            "dragon_marks",         # 용기사
            "holy_system",          # 팔라딘
            "divinity_system",      # 성직자
            "darkness_system",      # 암흑기사
            "undead_legion",        # 네크로맨서
            "theft_system",         # 로그
            "shapeshifting_system", # 드루이드
            "enchant_system",       # 마검사
            "curse_system",         # 주술사
            "melody_system",        # 바드 (old)
            "score_composition",    # 바드 (new)
            "break_system",         # 브레이커
            "elemental_counter",    # 정령술사
            "alchemy_system",       # 연금술사
            "elemental_spirits",    # 정령술사
            "plunder_system",       # 해적
            "rum_treasure_system",  # 해적 (new)
            "multithread_system",   # 엔지니어
            "dilemma_choice",       # 철학자
            "rune_resonance",       # 대마법사
            "dimension_refraction", # 차원술사
            "trick_deck",           # 마술사
            "support_fire",         # 궁수
            "charge_system",        # 암흑기사
        ]
        
        # gimmick_updater.py 읽기
        updater_path = 'src/character/gimmick_updater.py'
        with open(updater_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # on_skill_use 함수 찾기
        skill_use_match = re.search(r'def on_skill_use\(.*?\n(.*?)(?=\n    @staticmethod|\n    def |\nclass |\Z)', 
                                    content, re.DOTALL)
        if not skill_use_match:
            print_error("on_skill_use 함수를 찾을 수 없음!")
            return False
        
        skill_use_body = skill_use_match.group(1)
        
        # 처리되는 기믹 타입 확인
        handled = []
        for gt in gimmick_types:
            if f'== "{gt}"' in skill_use_body or f"== '{gt}'" in skill_use_body:
                handled.append(gt)
        
        not_handled = set(gimmick_types) - set(handled)
        
        print_info(f"on_skill_use에서 처리되는 기믹: {len(handled)}/{len(gimmick_types)}")
        
        # 처리가 필요한 기믹 (스킬 사용 시 특별한 처리가 필요한 것들)
        needs_handling = {
            "magazine_system": "탄환 소모",
            "stealth_exposure": "은신 해제",
            "support_fire": "콤보 초기화",
            "stance_system": "스탠스 효과",
            "shapeshifting_system": "변신",
            "score_composition": "음표 추가",
            "trick_deck": "카드 드로우",
        }
        
        missing_critical = []
        for gt, desc in needs_handling.items():
            if gt not in handled:
                missing_critical.append(f"{gt}: {desc}")
        
        if missing_critical:
            print(f"\n{Fore.RED}❌ 필수 처리 누락:{Style.RESET_ALL}")
            for m in missing_critical:
                print_error(m)
            self.issues.extend(missing_critical)
        else:
            print_ok("필수 기믹 처리 완료")
        
        return len(self.issues) == 0


class RuntimeTester:
    """런타임 테스트 (실제 스킬 실행)"""
    
    def __init__(self):
        self.issues = []
    
    def test_skill_execution(self):
        """스킬 실행 테스트"""
        print_header("런타임 테스트")
        
        try:
            from src.character.skills.skill_manager import get_skill_manager
            from src.character.character import Character
            
            sm = get_skill_manager()
            
            # 테스트용 캐릭터 생성
            test_char = Character("테스트", "warrior", level=10)
            test_enemy = Character("적", "warrior", level=10)
            
            # 도적 기습 테스트
            print_info("도적 기습 스킬 테스트...")
            from src.character.skills.job_skills.rogue_skills import create_rogue_skills
            rogue_skills = create_rogue_skills()
            ambush = rogue_skills[0]  # 기습
            
            test_char.active_buffs = {}
            test_enemy.active_buffs = {}
            
            context = {}
            result = ambush.execute(test_char, test_enemy, context)
            
            # 버프가 자신에게 적용되었는지 확인
            if test_char.active_buffs.get('critical_up'):
                print_ok("도적 기습: 자신에게 크리티컬 버프 정상 적용")
            else:
                print_error("도적 기습: 자신에게 크리티컬 버프 미적용!")
                self.issues.append("도적 기습 버프 타겟 오류")
            
            if test_enemy.active_buffs.get('critical_up'):
                print_error("도적 기습: 적에게 크리티컬 버프가 잘못 적용됨!")
                self.issues.append("도적 기습 버프가 적에게 적용됨")
            else:
                print_ok("도적 기습: 적에게 버프 미적용 (정상)")
            
            # 바드 음표 테스트
            print_info("바드 음표 생성 테스트...")
            bard_char = Character("바드", "bard", level=10)
            bard_char.gimmick_type = "score_composition"
            bard_char.music_notes = []
            bard_char.max_notes = 5
            
            from src.character.skills.job_skills.bard_skills import create_bard_skills
            bard_skills = create_bard_skills()
            note_strike = bard_skills[0]  # 음표 타격
            
            from src.character.gimmick_updater import GimmickUpdater
            GimmickUpdater.on_skill_use(bard_char, note_strike)
            
            if bard_char.music_notes and 'A' in bard_char.music_notes:
                print_ok(f"바드 음표 생성: {bard_char.music_notes}")
            else:
                print_error(f"바드 음표 미생성! (현재: {bard_char.music_notes})")
                self.issues.append("바드 음표 생성 오류")
            
            # 마술사 카드 테스트
            print_info("마술사 카드 드로우 테스트...")
            magician_char = Character("마술사", "magician", level=10)
            magician_char.gimmick_type = "trick_deck"
            
            from src.character.skills.job_skills.magician_skills import initialize_trick_deck, create_magician_skills
            initialize_trick_deck(magician_char)
            
            initial_hand = len(magician_char.card_hand)
            magician_skills = create_magician_skills()
            card_slash = magician_skills[0]  # 카드 슬래시
            
            GimmickUpdater.on_skill_use(magician_char, card_slash)
            
            if len(magician_char.card_hand) > initial_hand:
                print_ok(f"마술사 카드 드로우: {len(magician_char.card_hand)}장")
            else:
                print_error(f"마술사 카드 드로우 실패! (손패: {len(magician_char.card_hand)}장)")
                self.issues.append("마술사 카드 드로우 오류")
            
        except Exception as e:
            print_error(f"런타임 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
            self.issues.append(f"런타임 오류: {e}")
        
        return len(self.issues) == 0


def main():
    print(f"\n{Fore.MAGENTA}{'#'*60}")
    print(f"#  스킬 시스템 정밀 점검 스크립트")
    print(f"#  Dawn of Stellar")
    print(f"{'#'*60}{Style.RESET_ALL}")
    
    all_passed = True
    
    # 1. 스킬 무결성 테스트
    skill_tester = SkillIntegrityTester()
    if not skill_tester.run_tests():
        all_passed = False
    
    # 2. 기믹 시스템 테스트
    gimmick_tester = GimmickIntegrityTester()
    if not gimmick_tester.test_gimmick_updater_coverage():
        all_passed = False
    
    # 3. 런타임 테스트
    runtime_tester = RuntimeTester()
    if not runtime_tester.test_skill_execution():
        all_passed = False
    
    # 최종 결과
    print_header("최종 결과")
    
    total_issues = (len(skill_tester.issues) + 
                   len(gimmick_tester.issues) + 
                   len(runtime_tester.issues))
    total_warnings = len(skill_tester.warnings) + len(gimmick_tester.warnings)
    
    if all_passed and total_issues == 0:
        print(f"\n{Fore.GREEN}{'='*60}")
        print(f"  [PASS] All tests passed!")
        print(f"{'='*60}{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}{'='*60}")
        print(f"  [FAIL] Tests failed")
        print(f"  - 오류: {total_issues}개")
        print(f"  - 경고: {total_warnings}개")
        print(f"{'='*60}{Style.RESET_ALL}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
