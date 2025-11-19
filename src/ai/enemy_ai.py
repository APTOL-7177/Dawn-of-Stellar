"""
적 AI 시스템 - 스킬 선택 및 전략

적이 전투 중 어떤 행동을 할지 결정하는 AI
"""

from typing import List, Optional, Any
import random

from src.combat.enemy_skills import EnemySkill, SkillTargetType
from src.core.logger import get_logger


logger = get_logger("enemy_ai")


class EnemyAI:
    """
    적 AI

    전투 상황을 분석하여 최적의 행동 결정
    """

    def __init__(self, enemy: Any, difficulty: str = "hard"):
        """
        Args:
            enemy: 적 캐릭터
            difficulty: 난이도 ("easy", "normal", "hard", "insane")
        """
        self.enemy = enemy
        self.difficulty = difficulty

        # 난이도별 스킬 사용 확률 조정 (더욱 공격적으로 변경)
        self.skill_use_multiplier = {
            "easy": 1.0,     # 스킬 사용 기본
            "normal": 2.5,   # 스킬 사용 2.5배
            "hard": 4.0,     # 스킬 사용 4배 (훨씬 더 적극적)
            "insane": 6.0    # 스킬 사용 6배
        }.get(difficulty, 4.0)  # 기본값도 4.0으로

    def decide_action(
        self,
        allies: List[Any],
        enemies: List[Any]
    ) -> dict:
        """
        행동 결정

        Args:
            allies: 아군 목록 (적 입장에서)
            enemies: 적군 목록 (플레이어 파티)

        Returns:
            행동 정보 딕셔너리
            {
                "type": "attack" | "skill" | "defend",
                "skill": EnemySkill (if type == "skill"),
                "target": target_character
            }
        """
        # 스킬이 없으면 일반 공격
        if not hasattr(self.enemy, 'skills') or not self.enemy.skills:
            return self._decide_basic_attack(enemies)

        # 쿨다운 감소
        for skill in self.enemy.skills:
            skill.reduce_cooldown()

        # 사용 가능한 스킬 필터링
        available_skills = [
            skill for skill in self.enemy.skills
            if skill.can_use(self.enemy)
        ]

        if not available_skills:
            # 사용 가능한 스킬 없음 → 일반 공격
            return self._decide_basic_attack(enemies)

        # 상황 분석
        context = self._analyze_situation(allies, enemies)

        # 스킬 선택 (우선순위 기반)
        selected_skill = self._select_skill(available_skills, context)

        if selected_skill:
            # 스킬 사용 확률 체크 (난이도 반영)
            # 확률이 1.0을 초과할 수 있도록 처리 (항상 사용하거나 높은 확률)
            adjusted_probability = selected_skill.use_probability * self.skill_use_multiplier
            # 최소 확률 보장 (스킬이 있으면 최소 50% 확률로 사용)
            adjusted_probability = max(adjusted_probability, 0.5)
            if random.random() < min(adjusted_probability, 1.0):
                # 대상 선택
                target = self._select_target(selected_skill, allies, enemies)
                if target:
                    # 쿨다운 활성화
                    selected_skill.activate_cooldown()

                    # 대상 이름 결정 (리스트인 경우 처리)
                    if isinstance(target, list):
                        if len(target) == 1:
                            target_name = getattr(target[0], 'name', 'Unknown')
                        elif len(target) > 1:
                            target_name = f"전체 ({len(target)}명)"
                        else:
                            target_name = "없음"
                    else:
                        target_name = getattr(target, 'name', 'Unknown')
                    
                    logger.info(
                        f"{self.enemy.name}이(가) {selected_skill.name} 사용! "
                        f"(대상: {target_name})"
                    )

                    return {
                        "type": "skill",
                        "skill": selected_skill,
                        "target": target
                    }

        # 스킬 사용하지 않음 → 일반 공격
        return self._decide_basic_attack(enemies)

    def _estimate_hp_damage(self, target: Any, brv_points: int, hp_multiplier: float = 1.0) -> int:
        """
        예상 HP 데미지 계산
        
        Args:
            target: 타겟 캐릭터
            brv_points: 사용할 BRV 포인트
            hp_multiplier: HP 배율
            
        Returns:
            예상 데미지
        """
        if brv_points <= 0:
            return 0
        
        try:
            from src.combat.damage_calculator import get_damage_calculator
            damage_calc = get_damage_calculator()
            
            # 물리 데미지로 계산 (대략적인 추정)
            attacker_stat = getattr(self.enemy, 'strength', 50)
            defender_stat = getattr(target, 'defense', 50)
            
            # 스탯 보정
            stat_modifier = attacker_stat / (defender_stat + 1.0)
            
            # HP 데미지 배율 (config에서 가져옴, 기본값 0.15)
            hp_damage_multiplier = 0.15
            
            # 예상 데미지 계산
            estimated_damage = int(brv_points * hp_multiplier * stat_modifier * hp_damage_multiplier)
            
            # 최소 데미지 보장
            return max(5, estimated_damage)
        except Exception:
            # 계산 실패 시 대략적인 추정
            return max(5, int(brv_points * 0.15))

    def _analyze_situation(
        self,
        allies: List[Any],
        enemies: List[Any]
    ) -> dict:
        """
        전투 상황 분석

        Returns:
            상황 정보 딕셔너리
        """
        # 자신의 HP 비율
        self_hp_percent = self.enemy.current_hp / self.enemy.max_hp if self.enemy.max_hp > 0 else 0

        # 자신의 BRV 정보 (절대값만 사용)
        self_brv = getattr(self.enemy, 'current_brv', 0)

        # 아군 평균 HP
        ally_hp_total = sum(getattr(a, 'current_hp', 0) for a in allies if getattr(a, 'is_alive', True))
        ally_hp_avg = ally_hp_total / len(allies) if allies else 0

        # 적군 평균 HP
        enemy_hp_total = sum(getattr(e, 'current_hp', 0) for e in enemies if getattr(e, 'is_alive', True))
        enemy_hp_avg = enemy_hp_total / len(enemies) if enemies else 0

        # 적군 평균 BRV
        enemy_brv_total = sum(getattr(e, 'current_brv', 0) for e in enemies if getattr(e, 'is_alive', True))
        enemy_brv_avg = enemy_brv_total / len(enemies) if enemies else 0

        # 생존한 아군/적군 수
        alive_allies = sum(1 for a in allies if getattr(a, 'is_alive', True))
        alive_enemies = sum(1 for e in enemies if getattr(e, 'is_alive', True))

        # 가장 약한 적 (HP 기준)
        weakest_enemy = None
        lowest_hp = float('inf')
        for enemy in enemies:
            if getattr(enemy, 'is_alive', True):
                hp = getattr(enemy, 'current_hp', 0)
                if hp < lowest_hp:
                    lowest_hp = hp
                    weakest_enemy = enemy

        # 가장 강한 적 (HP 기준)
        strongest_enemy = None
        highest_hp = 0
        for enemy in enemies:
            if getattr(enemy, 'is_alive', True):
                hp = getattr(enemy, 'current_hp', 0)
                if hp > highest_hp:
                    highest_hp = hp
                    strongest_enemy = enemy

        # 현재 BRV로 각 적에게 줄 수 있는 예상 데미지 계산
        can_deal_meaningful_damage = False
        best_target_for_hp_attack = None
        max_estimated_damage = 0
        
        if self_brv > 0:
            for enemy in enemies:
                if getattr(enemy, 'is_alive', True):
                    enemy_hp = getattr(enemy, 'current_hp', 0)
                    if enemy_hp > 0:
                        estimated_damage = self._estimate_hp_damage(enemy, self_brv)
                        
                        # 의미있는 데미지인지 판단 (적 HP의 최소 5% 이상, 또는 최소 50 이상)
                        damage_threshold = max(50, enemy_hp * 0.05)
                        if estimated_damage >= damage_threshold:
                            can_deal_meaningful_damage = True
                            if estimated_damage > max_estimated_damage:
                                max_estimated_damage = estimated_damage
                                best_target_for_hp_attack = enemy

        return {
            "self_hp_percent": self_hp_percent,
            "self_brv": self_brv,
            "ally_hp_avg": ally_hp_avg,
            "enemy_hp_avg": enemy_hp_avg,
            "enemy_brv_avg": enemy_brv_avg,
            "alive_allies": alive_allies,
            "alive_enemies": alive_enemies,
            "weakest_enemy": weakest_enemy,
            "strongest_enemy": strongest_enemy,
            "is_desperate": self_hp_percent < 0.3,  # HP 30% 이하
            "is_low_hp": self_hp_percent < 0.5,     # HP 50% 이하
            "can_deal_meaningful_damage": can_deal_meaningful_damage,  # 현재 BRV로 의미있는 데미지 가능
            "best_target_for_hp_attack": best_target_for_hp_attack,  # HP 공격 최적 타겟
            "max_estimated_damage": max_estimated_damage,  # 최대 예상 데미지
            "outnumbered": alive_allies < alive_enemies,
            "winning": ally_hp_avg > enemy_hp_avg * 1.5
        }

    def _select_skill(
        self,
        available_skills: List[EnemySkill],
        context: dict
    ) -> Optional[EnemySkill]:
        """
        스킬 선택 (우선순위 기반)

        Args:
            available_skills: 사용 가능한 스킬 목록
            context: 상황 정보

        Returns:
            선택된 스킬 (또는 None)
        """
        # 우선순위 점수 계산
        skill_scores = []

        for skill in available_skills:
            score = skill.use_probability  # 기본 점수

            # 상황별 가중치 조정
            if context["is_desperate"]:
                # 절망적인 상황: 힐/버프 우선
                if skill.heal_amount > 0:
                    score *= 3.0
                if skill.buff_stats:
                    score *= 2.5
                # 필살기 우선
                if skill.damage > 100:
                    score *= 2.0

            elif context["is_low_hp"]:
                # HP 낮음: 힐 우선
                if skill.heal_amount > 0:
                    score *= 2.0

            if context["outnumbered"]:
                # 수적 열세: AoE 스킬 우선
                if skill.target_type == SkillTargetType.ALL_ENEMIES:
                    score *= 1.5

            if context["winning"]:
                # 우세: 더욱 공격적인 스킬 사용
                if skill.damage > 0:
                    score *= 2.0  # 1.3에서 2.0으로 증가
                # HP 공격 우선
                if skill.hp_attack:
                    score *= 2.5  # 1.8에서 2.5로 증가
            
            # HP 공격 스킬에 대한 일반적인 가중치 증가 (상황에 관계없이)
            if skill.hp_attack:
                score *= 2.5  # HP 공격 스킬은 기본적으로 2.5배 가중치
                
                # 현재 BRV로 의미있는 데미지를 줄 수 있으면 훨씬 더 우선
                if context.get("can_deal_meaningful_damage", False):
                    score *= 4.0  # 의미있는 데미지를 줄 수 있으면 4배 추가 가중치
                elif context.get("self_brv", 0) >= 100:
                    # BRV 100 이상이면 우선도 증가
                    score *= 2.0
                elif context.get("self_brv", 0) > 0:
                    # BRV가 조금이라도 있으면 기본 가중치
                    score *= 1.5

            # MP가 부족하면 낮은 코스트 스킬 우선
            if hasattr(self.enemy, 'current_mp'):
                mp_percent = self.enemy.current_mp / self.enemy.max_mp if self.enemy.max_mp > 0 else 0
                if mp_percent < 0.3:  # MP 30% 이하
                    if skill.mp_cost < 20:
                        score *= 1.5

            skill_scores.append((skill, score))

        if not skill_scores:
            return None

        # 가중치 기반 랜덤 선택
        skills, scores = zip(*skill_scores)
        selected = random.choices(skills, weights=scores, k=1)[0]

        return selected

    def _calculate_agro_weight(
        self,
        enemy: Any,
        skill: Optional[EnemySkill] = None
    ) -> int:
        """
        적의 어그로 가중치 계산 (난이도별 지능 적용)
        
        Args:
            enemy: 적 캐릭터
            skill: 사용할 스킬 (선택사항)
            
        Returns:
            어그로 가중치
        """
        # 어그로 수치 가져오기 (없으면 초기화)
        if not hasattr(enemy, '_agro_value'):
            base_agro = 50
            enemy._agro_value = base_agro
        
        agro = enemy._agro_value
        base_agro = agro
        
        # 난이도별 지능 적용
        if self.difficulty == "easy":
            # easy: 기본 어그로만 사용, 랜덤성 높음
            # 힐러/약한 적 약간 우선
            job_name = getattr(enemy, 'job_name', '').lower()
            if any(keyword in job_name for keyword in ['heal', '힐', 'support', '지원', 'white', '백']):
                agro += 10  # 힐러는 어그로 +10
            hp_percent = getattr(enemy, 'current_hp', 1000) / getattr(enemy, 'max_hp', 1000) if getattr(enemy, 'max_hp', 1000) > 0 else 1.0
            if hp_percent < 0.3:
                agro += 10  # HP 30% 이하면 어그로 +10
                
        elif self.difficulty == "normal":
            # normal: 기본 어그로 시스템
            job_name = getattr(enemy, 'job_name', '').lower()
            if any(keyword in job_name for keyword in ['heal', '힐', 'support', '지원', 'white', '백']):
                agro += 30  # 힐러는 어그로 +30
            hp_percent = getattr(enemy, 'current_hp', 1000) / getattr(enemy, 'max_hp', 1000) if getattr(enemy, 'max_hp', 1000) > 0 else 1.0
            if hp_percent < 0.3:
                agro += 40  # HP 30% 이하면 어그로 +40
            elif hp_percent < 0.5:
                agro += 20  # HP 50% 이하면 어그로 +20
                
        elif self.difficulty == "hard":
            # hard: 더 지능적으로 타겟팅
            job_name = getattr(enemy, 'job_name', '').lower()
            hp_percent = getattr(enemy, 'current_hp', 1000) / getattr(enemy, 'max_hp', 1000) if getattr(enemy, 'max_hp', 1000) > 0 else 1.0
            
            # 힐러/서포터 매우 우선 (어그로 +50)
            if any(keyword in job_name for keyword in ['heal', '힐', 'support', '지원', 'white', '백']):
                agro += 50
            
            # 약한 적 우선 (어그로 +30~70)
            if hp_percent < 0.2:
                agro += 70  # HP 20% 이하면 어그로 +70 (마무리 우선)
            elif hp_percent < 0.3:
                agro += 50  # HP 30% 이하면 어그로 +50
            elif hp_percent < 0.5:
                agro += 30  # HP 50% 이하면 어그로 +30
            
            # 강력한 공격일 때 약한 적 더욱 우선
            if skill and skill.damage > 100:
                if hp_percent < 0.3:
                    agro += 40  # 강력한 공격 + 약한 적 = 추가 어그로 +40
                elif hp_percent < 0.5:
                    agro += 25  # 강력한 공격 + 중간 HP = 추가 어그로 +25
            
        elif self.difficulty == "insane":
            # insane: 매우 지능적으로 타겟팅 (최적화된 선택)
            job_name = getattr(enemy, 'job_name', '').lower()
            hp_percent = getattr(enemy, 'current_hp', 1000) / getattr(enemy, 'max_hp', 1000) if getattr(enemy, 'max_hp', 1000) > 0 else 1.0
            
            # 힐러/서포터 최우선 (어그로 +80)
            if any(keyword in job_name for keyword in ['heal', '힐', 'support', '지원', 'white', '백']):
                agro += 80
            
            # 약한 적 매우 우선 (어그로 +50~100)
            if hp_percent < 0.2:
                agro += 100  # HP 20% 이하면 어그로 +100 (즉시 마무리)
            elif hp_percent < 0.3:
                agro += 70  # HP 30% 이하면 어그로 +70
            elif hp_percent < 0.5:
                agro += 50  # HP 50% 이하면 어그로 +50
            
            # 강력한 공격일 때 약한 적 최우선
            if skill and skill.damage > 100:
                if hp_percent < 0.3:
                    agro += 60  # 강력한 공격 + 약한 적 = 추가 어그로 +60
                elif hp_percent < 0.5:
                    agro += 40  # 강력한 공격 + 중간 HP = 추가 어그로 +40
            
            # BRV가 낮은 적도 우선 (BREAK 가능성)
            enemy_brv = getattr(enemy, 'current_brv', 1000)
            if enemy_brv < 200:
                agro += 30  # BRV 낮으면 어그로 +30
        
        else:
            # 기본값: normal과 동일
            job_name = getattr(enemy, 'job_name', '').lower()
            if any(keyword in job_name for keyword in ['heal', '힐', 'support', '지원', 'white', '백']):
                agro += 30
            hp_percent = getattr(enemy, 'current_hp', 1000) / getattr(enemy, 'max_hp', 1000) if getattr(enemy, 'max_hp', 1000) > 0 else 1.0
            if hp_percent < 0.3:
                agro += 40
            elif hp_percent < 0.5:
                agro += 20
        
        return max(10, agro)  # 최소 가중치 보장

    def _select_target(
        self,
        skill: EnemySkill,
        allies: List[Any],
        enemies: List[Any]
    ) -> Optional[Any]:
        """
        대상 선택

        Args:
            skill: 사용할 스킬
            allies: 아군 목록
            enemies: 적군 목록

        Returns:
            선택된 대상
        """
        if skill.target_type == SkillTargetType.SELF:
            return self.enemy

        elif skill.target_type == SkillTargetType.ALL_ALLIES:
            return allies  # 전체 대상

        elif skill.target_type == SkillTargetType.ALL_ENEMIES:
            return enemies  # 전체 대상

        elif skill.target_type == SkillTargetType.SINGLE_ENEMY:
            # 단일 적 선택 (난이도별 어그로 시스템 사용)
            alive_enemies = [e for e in enemies if getattr(e, 'is_alive', True)]
            if not alive_enemies:
                return None

            # 난이도별 타겟 선택 전략
            if self.difficulty == "insane":
                # insane: 항상 최적 타겟 선택 (랜덤 없음)
                best_target = None
                best_score = -1
                
                for enemy in alive_enemies:
                    agro_weight = self._calculate_agro_weight(enemy, skill)
                    if agro_weight > best_score:
                        best_score = agro_weight
                        best_target = enemy
                
                if best_target:
                    # 선택된 타겟의 어그로 증가
                    best_target._agro_value = getattr(best_target, '_agro_value', 50) + random.randint(15, 25)
                    return best_target
                return random.choice(alive_enemies)
            
            elif self.difficulty == "easy":
                # easy: 높은 랜덤성 (50% 확률로 랜덤, 50% 확률로 어그로 기반)
                if random.random() < 0.5:
                    selected = random.choice(alive_enemies)
                else:
                    # 어그로 기반 선택
                    enemy_weights = [self._calculate_agro_weight(e, skill) for e in alive_enemies]
                    min_weight = max(10, min(enemy_weights) * 0.7)  # 더 균등하게
                    enemy_weights = [max(w, min_weight) for w in enemy_weights]
                    selected = random.choices(alive_enemies, weights=enemy_weights, k=1)[0]
                
                # 선택된 타겟의 어그로 증가 (적게 증가)
                selected._agro_value = getattr(selected, '_agro_value', 50) + random.randint(5, 15)
                return selected
            
            else:
                # normal, hard: 어그로 가중치 기반 랜덤 선택
                enemy_weights = []
                for enemy in alive_enemies:
                    agro_weight = self._calculate_agro_weight(enemy, skill)
                    enemy_weights.append(agro_weight)
                
                # 가중치 기반 랜덤 선택
                # hard는 더 편중되게, normal은 더 균등하게
                if self.difficulty == "hard":
                    min_weight = max(10, min(enemy_weights) * 0.4)  # hard: 더 편중
                else:
                    min_weight = max(10, min(enemy_weights) * 0.6)  # normal: 더 균등
                
                enemy_weights = [max(w, min_weight) for w in enemy_weights]
                selected = random.choices(alive_enemies, weights=enemy_weights, k=1)[0]
                
                # 선택된 타겟의 어그로 증가
                if self.difficulty == "hard":
                    selected._agro_value = getattr(selected, '_agro_value', 50) + random.randint(15, 25)
                else:
                    selected._agro_value = getattr(selected, '_agro_value', 50) + random.randint(10, 20)
                
                return selected

        elif skill.target_type == SkillTargetType.RANDOM_ENEMY:
            alive_enemies = [e for e in enemies if getattr(e, 'is_alive', True)]
            return random.choice(alive_enemies) if alive_enemies else None

        return None

    def _decide_basic_attack(self, enemies: List[Any]) -> dict:
        """
        일반 공격 결정 (BRV 공격 또는 HP 공격)

        현재 BRV 절대값으로 적에게 의미있는 데미지를 줄 수 있는지 판단하여 HP 공격 결정
        자신이 죽더라도 최대한 큰 피해를 입히는 것을 우선

        Args:
            enemies: 적군 목록

        Returns:
            공격 행동 정보
        """
        alive_enemies = [e for e in enemies if getattr(e, 'is_alive', True)]

        if not alive_enemies:
            return {"type": "defend", "target": None}

        # BRV 확인 (절대값만 사용)
        current_brv = getattr(self.enemy, 'current_brv', 0)
        
        # 타겟 선택 (안전장치 포함)
        target = None
        
        try:
            # 난이도별 타겟 선택 전략
            if self.difficulty == "insane":
                # insane: 항상 최적 타겟 선택 (랜덤 없음)
                best_target = None
                best_score = -1
                
                for enemy in alive_enemies:
                    try:
                        agro_weight = self._calculate_agro_weight(enemy, None)
                        if agro_weight > best_score:
                            best_score = agro_weight
                            best_target = enemy
                    except Exception as e:
                        logger.warning(f"어그로 계산 오류: {e}")
                        continue
                
                if best_target:
                    target = best_target
                    target._agro_value = getattr(target, '_agro_value', 50) + random.randint(15, 25)
                else:
                    target = random.choice(alive_enemies)
                    
            elif self.difficulty == "easy":
                # easy: 높은 랜덤성 (50% 확률로 랜덤, 50% 확률로 어그로 기반)
                if random.random() < 0.5:
                    target = random.choice(alive_enemies)
                else:
                    try:
                        enemy_weights = [self._calculate_agro_weight(e, None) for e in alive_enemies]
                        if enemy_weights and min(enemy_weights) > 0:
                            min_weight = max(10, min(enemy_weights) * 0.7)
                            enemy_weights = [max(w, min_weight) for w in enemy_weights]
                            target = random.choices(alive_enemies, weights=enemy_weights, k=1)[0]
                        else:
                            target = random.choice(alive_enemies)
                    except Exception as e:
                        logger.warning(f"어그로 기반 선택 오류: {e}")
                        target = random.choice(alive_enemies)
                
                if target:
                    target._agro_value = getattr(target, '_agro_value', 50) + random.randint(5, 15)
                
            else:
                # normal, hard: 어그로 가중치 기반 랜덤 선택
                try:
                    enemy_weights = [self._calculate_agro_weight(e, None) for e in alive_enemies]
                    
                    if enemy_weights and min(enemy_weights) > 0:
                        # hard는 더 편중되게, normal은 더 균등하게
                        if self.difficulty == "hard":
                            min_weight = max(10, min(enemy_weights) * 0.4)
                        else:
                            min_weight = max(10, min(enemy_weights) * 0.6)
                        
                        enemy_weights = [max(w, min_weight) for w in enemy_weights]
                        target = random.choices(alive_enemies, weights=enemy_weights, k=1)[0]
                    else:
                        target = random.choice(alive_enemies)
                    
                    # 선택된 타겟의 어그로 증가
                    if target:
                        if self.difficulty == "hard":
                            target._agro_value = getattr(target, '_agro_value', 50) + random.randint(15, 25)
                        else:
                            target._agro_value = getattr(target, '_agro_value', 50) + random.randint(10, 20)
                except Exception as e:
                    logger.warning(f"어그로 기반 선택 오류: {e}")
                    target = random.choice(alive_enemies)
        except Exception as e:
            logger.error(f"타겟 선택 오류: {e}")
            target = random.choice(alive_enemies) if alive_enemies else None
        
        # 타겟이 선택되지 않았으면 안전장치
        if not target:
            target = random.choice(alive_enemies) if alive_enemies else None
            if not target:
                return {"type": "defend", "target": None}

        # HP 공격 판단: 현재 BRV로 타겟에게 의미있는 데미지를 줄 수 있는지 계산
        if current_brv > 0:
            target_hp = getattr(target, 'current_hp', 0)
            if target_hp > 0:
                # 예상 데미지 계산
                estimated_damage = self._estimate_hp_damage(target, current_brv)
                
                # 의미있는 데미지인지 판단 (적 HP의 최소 3% 이상, 또는 최소 30 이상)
                damage_threshold = max(30, target_hp * 0.03)
                
                if estimated_damage >= damage_threshold:
                    # 의미있는 데미지를 줄 수 있으면 HP 공격
                    # 자신이 죽더라도 피해를 입히는 것을 우선하므로, BRV가 있으면 매우 높은 확률로 HP 공격
                    hp_attack_probability = 0.85  # 기본 85% 확률
                    
                    # 자신의 HP가 낮으면 더욱 적극적으로 HP 공격 (죽더라도 피해를 입히겠다는 의지)
                    self_hp_percent = self.enemy.current_hp / self.enemy.max_hp if self.enemy.max_hp > 0 else 1.0
                    if self_hp_percent < 0.3:
                        hp_attack_probability = 0.95  # HP 30% 이하면 95% 확률
                    elif self_hp_percent < 0.5:
                        hp_attack_probability = 0.90  # HP 50% 이하면 90% 확률
                    
                    # 예상 데미지가 타겟 HP의 10% 이상이면 더욱 적극적으로
                    if estimated_damage >= target_hp * 0.1:
                        hp_attack_probability = min(0.95, hp_attack_probability + 0.1)
                    
                    if random.random() < hp_attack_probability:
                        return {
                            "type": "hp_attack",
                            "target": target
                        }
                
                # 데미지가 작더라도 BRV가 충분히 쌓였으면 (200 이상) 일정 확률로 HP 공격
                elif current_brv >= 200:
                    if random.random() < 0.4:  # 40% 확률
                        return {
                            "type": "hp_attack",
                            "target": target
                        }

        # BRV 공격 (기본)
        return {
            "type": "attack",  # "attack"은 BRV 공격을 의미
            "target": target
        }


class BossAI(EnemyAI):
    """
    보스 AI

    일반 적보다 더 똑똑하고 전략적
    """

    def __init__(self, enemy: Any):
        # 보스는 항상 "hard" 난이도
        super().__init__(enemy, difficulty="hard")

    def _select_skill(
        self,
        available_skills: List[EnemySkill],
        context: dict
    ) -> Optional[EnemySkill]:
        """
        보스 스킬 선택 (더 전략적)
        """
        # 페이즈별 전략
        hp_percent = context["self_hp_percent"]

        # HP 단계별 우선 스킬
        phase_skills = {
            # HP 0-30%: 필살기 우선
            "desperate": lambda s: s.damage > 100 or s.heal_amount > 50,
            # HP 30-70%: 균형잡힌 전략
            "balanced": lambda s: True,
            # HP 70-100%: 공격적 전략
            "aggressive": lambda s: s.damage > 0 or s.debuff_stats
        }

        if hp_percent < 0.3:
            phase = "desperate"
        elif hp_percent < 0.7:
            phase = "balanced"
        else:
            phase = "aggressive"

        # 페이즈에 맞는 스킬 필터링
        phase_filter = phase_skills[phase]
        filtered_skills = [s for s in available_skills if phase_filter(s)]

        if not filtered_skills:
            filtered_skills = available_skills

        # 부모 클래스의 선택 로직 사용
        return super()._select_skill(filtered_skills, context)


class SephirothAI(BossAI):
    """
    세피로스 전용 AI

    가장 강력하고 전략적인 AI
    """

    def __init__(self, enemy: Any):
        super().__init__(enemy)
        self.skill_use_multiplier = 5.0  # 스킬 사용 확률 5배 (2.5 -> 5.0)
        self.phase = 1

    def decide_action(
        self,
        allies: List[Any],
        enemies: List[Any]
    ) -> dict:
        """
        세피로스의 행동 결정

        HP 단계별로 다른 전략 사용
        """
        hp_percent = self.enemy.current_hp / self.enemy.max_hp if self.enemy.max_hp > 0 else 0

        # 페이즈 전환
        if hp_percent < 0.3 and self.phase < 3:
            self.phase = 3
            logger.warning(f"⚠️ {self.enemy.name}의 광기가 폭발한다!")
        elif hp_percent < 0.6 and self.phase < 2:
            self.phase = 2
            logger.warning(f"⚠️ {self.enemy.name}이(가) 진지해진다...")

        # 페이즈별 강제 스킬 사용
        if self.phase == 3:
            # 페이즈 3: 절망 사용 시도
            for skill in self.enemy.skills:
                if skill.skill_id == "despair" and skill.can_use(self.enemy):
                    skill.activate_cooldown()
                    return {
                        "type": "skill",
                        "skill": skill,
                        "target": enemies
                    }

        # 일반 결정 로직
        return super().decide_action(allies, enemies)


def create_ai_for_enemy(enemy: Any) -> EnemyAI:
    """
    적에 맞는 AI 생성

    Args:
        enemy: 적 캐릭터

    Returns:
        적절한 AI 인스턴스
    """
    enemy_name = getattr(enemy, 'name', '').lower()

    # 세피로스
    if 'sephiroth' in enemy_name or '세피로스' in enemy_name:
        return SephirothAI(enemy)

    # 보스
    if 'boss' in enemy_name or '보스' in enemy_name or 'dragon' in enemy_name or '드래곤' in enemy_name:
        return BossAI(enemy)

    # 일반 적도 hard 난이도로 (더 공격적으로)
    return EnemyAI(enemy, difficulty="hard")
