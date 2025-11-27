"""Magician Skills - 마술사 (트릭 덱 시스템)

트럼프 카드를 활용한 트릭스터 유틸리티 직업.
카드의 숫자/무늬에 따라 다양한 특수 효과 발동.
포커 조합으로 강력한 스킬 사용.
"""
import random
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.costs.mp_cost import MPCost
from src.core.logger import get_logger

logger = get_logger("magician_skills")


# ============================================================
# 카드 특수 효과 정의
# ============================================================

# 숫자별 특수 효과
RANK_EFFECTS = {
    "A": {"name": "에이스", "effect": "first_strike", "desc": "선제공격 - 다음 공격이 먼저 발동"},
    "2": {"name": "듀얼리티", "effect": "double_edge", "desc": "양날검 - 피해 2배, 자해 50%"},
    "3": {"name": "트리플", "effect": "triple_hit", "desc": "3연타 - 0.4배 피해 3회"},
    "4": {"name": "안정", "effect": "stability", "desc": "안정 - 다음 공격 필중 100%"},
    "5": {"name": "변화", "effect": "change", "desc": "변환 - 적 버프 1개 디버프로 전환"},
    "6": {"name": "저주", "effect": "curse", "desc": "저주 - 적에게 3턴 저주 (HP회복 불가)"},
    "7": {"name": "행운", "effect": "lucky_seven", "desc": "행운 - 크리티컬 확정, 드롭 확률 +50%"},
    "8": {"name": "무한", "effect": "infinity", "desc": "무한 - MP 소모 없음 (1회)"},
    "9": {"name": "극한", "effect": "max_power", "desc": "극한 - 다음 스킬 효과 +50%"},
    "10": {"name": "완성", "effect": "completion", "desc": "완성 - 손패 최대값까지 즉시 드로우"},
    "J": {"name": "나이트", "effect": "knight", "desc": "기사 - 아군 1명 보호 (1회 피해 대신 받음)"},
    "Q": {"name": "퀸", "effect": "queen", "desc": "여왕 - 아군 전체 HP 15% 회복"},
    "K": {"name": "킹", "effect": "king", "desc": "왕 - 적 전체에게 명령 (행동 불가 1턴)"},
}

# 무늬별 특수 효과
SUIT_EFFECTS = {
    "spade": {"name": "스페이드", "element": "dark", "effect": "pierce", "desc": "관통 - 방어력 30% 무시"},
    "heart": {"name": "하트", "element": "light", "effect": "lifesteal", "desc": "흡혈 - 피해량의 30% HP 회복"},
    "diamond": {"name": "다이아", "element": "earth", "effect": "wealth", "desc": "부 - 추가 경험치/골드 +30%"},
    "club": {"name": "클로버", "element": "poison", "effect": "toxic", "desc": "독 - 3턴간 독 상태 (매턴 5% HP 감소)"},
}

# 조커 특수 효과
JOKER_EFFECTS = {
    "joker_black": {"name": "블랙 조커", "effect": "copy_enemy", "desc": "적의 마지막 스킬 복사"},
    "joker_red": {"name": "레드 조커", "effect": "chaos", "desc": "혼돈 - 모든 확률 재계산 (운빠따라)"},
}


# ============================================================
# 트럼프 카드 시스템 헬퍼 함수들
# ============================================================

def create_deck():
    """실54장의 트럼프 덱 생성"""
    suits = ["spade", "heart", "diamond", "club"]
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    deck = []
    
    for suit in suits:
        for rank in ranks:
            deck.append({
                "suit": suit, 
                "rank": rank, 
                "is_joker": False,
                "rank_effect": RANK_EFFECTS.get(rank, {}),
                "suit_effect": SUIT_EFFECTS.get(suit, {})
            })
    
    # 조커 2장 추가
    deck.append({
        "suit": "joker", 
        "rank": "joker_black", 
        "is_joker": True,
        "joker_effect": JOKER_EFFECTS["joker_black"]
    })
    deck.append({
        "suit": "joker", 
        "rank": "joker_red", 
        "is_joker": True,
        "joker_effect": JOKER_EFFECTS["joker_red"]
    })
    
    return deck


def shuffle_deck(deck):
    """덱 셔플"""
    shuffled = deck.copy()
    random.shuffle(shuffled)
    return shuffled


def draw_cards(character, count=1):
    """카드 드로우"""
    drawn = []
    
    # 손패 확인
    hand = getattr(character, 'card_hand', [])
    max_hand = getattr(character, 'max_hand_size', 8)
    
    # 덱 확인
    deck = getattr(character, 'card_deck', [])
    discard = getattr(character, 'card_discard', [])
    
    for _ in range(count):
        # 손패가 가득 찼으면 중단
        if len(hand) >= max_hand:
            logger.info(f"{character.name} 손패 가득참 ({len(hand)}/{max_hand})")
            break
        
        # 덱이 비었으면 버린 카드 셔플
        if not deck:
            if discard:
                deck = shuffle_deck(discard)
                character.card_discard = []
                logger.info(f"{character.name} 덱 셔플 (버린 카드 {len(deck)}장)")
            else:
                # 완전히 새로운 덱 생성 (모든 카드 소진 시)
                deck = shuffle_deck(create_deck())
                logger.info(f"{character.name} 새 덱 생성 (54장)")
        
        # 카드 드로우
        if deck:
            card = deck.pop(0)
            hand.append(card)
            drawn.append(card)
            
            card_name = get_card_name(card)
            logger.debug(f"{character.name} 드로우: {card_name}")
    
    # 상태 저장
    character.card_hand = hand
    character.card_deck = deck
    
    return drawn


def discard_cards(character, cards):
    """카드 폐기"""
    hand = getattr(character, 'card_hand', [])
    discard = getattr(character, 'card_discard', [])
    
    for card in cards:
        if card in hand:
            hand.remove(card)
            discard.append(card)
    
    character.card_hand = hand
    character.card_discard = discard


def get_card_name(card):
    """카드 이름 반환"""
    if card.get('is_joker'):
        return "🃏 조커"
    
    suit_symbols = {
        "spade": "♠",
        "heart": "♥",
        "diamond": "♦",
        "club": "♣"
    }
    
    suit = suit_symbols.get(card.get('suit', ''), '?')
    rank = card.get('rank', '?')
    
    return f"{suit}{rank}"


def get_rank_value(rank):
    """카드 숫자 값 반환 (스트레이트 계산용)"""
    rank_values = {
        "A": 1, "2": 2, "3": 3, "4": 4, "5": 5,
        "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
        "J": 11, "Q": 12, "K": 13
    }
    return rank_values.get(rank, 0)


def check_poker_combination(hand):
    """
    손패에서 가능한 포커 조합 확인
    Returns: (조합 이름, 사용할 카드들, 조합 점수)
    """
    if not hand or len(hand) < 2:
        return None, [], 0
    
    # 조커 분리
    jokers = [c for c in hand if c.get('is_joker')]
    normal_cards = [c for c in hand if not c.get('is_joker')]
    
    # 숫자별, 무늬별 그룹화
    rank_groups = {}
    suit_groups = {}
    
    for card in normal_cards:
        rank = card.get('rank')
        suit = card.get('suit')
        
        if rank not in rank_groups:
            rank_groups[rank] = []
        rank_groups[rank].append(card)
        
        if suit not in suit_groups:
            suit_groups[suit] = []
        suit_groups[suit].append(card)
    
    # 각 조합 체크 (높은 조합부터)
    
    # 1. 로얄 스트레이트 플러시 체크
    for suit, cards in suit_groups.items():
        royal_ranks = {"10", "J", "Q", "K", "A"}
        card_ranks = {c.get('rank') for c in cards}
        missing = royal_ranks - card_ranks
        
        if len(missing) <= len(jokers):
            royal_cards = [c for c in cards if c.get('rank') in royal_ranks]
            return "royal_straight_flush", royal_cards + jokers[:len(missing)], 1000
    
    # 2. 스트레이트 플러시 체크
    for suit, cards in suit_groups.items():
        if len(cards) + len(jokers) >= 5:
            straight_cards = check_straight_in_cards(cards, jokers)
            if straight_cards:
                return "straight_flush", straight_cards, 900
    
    # 3. 포카드 체크
    for rank, cards in rank_groups.items():
        if len(cards) >= 4:
            return "four_of_kind", cards[:4], 800
        elif len(cards) == 3 and len(jokers) >= 1:
            return "four_of_kind", cards + jokers[:1], 800
        elif len(cards) == 2 and len(jokers) >= 2:
            return "four_of_kind", cards + jokers[:2], 800
    
    # 4. 풀하우스 체크
    triples = [r for r, c in rank_groups.items() if len(c) >= 3]
    pairs = [r for r, c in rank_groups.items() if len(c) >= 2]
    
    if triples and len(pairs) >= 2:
        triple_cards = rank_groups[triples[0]][:3]
        pair_rank = [p for p in pairs if p != triples[0]][0]
        pair_cards = rank_groups[pair_rank][:2]
        return "full_house", triple_cards + pair_cards, 700
    elif triples and pairs and len(jokers) >= 1:
        # 조커로 페어 완성
        triple_cards = rank_groups[triples[0]][:3]
        single_rank = [r for r, c in rank_groups.items() if len(c) >= 1 and r != triples[0]]
        if single_rank:
            return "full_house", triple_cards + rank_groups[single_rank[0]][:1] + jokers[:1], 700
    
    # 5. 플러시 체크
    for suit, cards in suit_groups.items():
        if len(cards) >= 5:
            return "flush", cards[:5], 600
        elif len(cards) + len(jokers) >= 5:
            return "flush", cards + jokers[:5-len(cards)], 600
    
    # 6. 스트레이트 체크
    straight_cards = check_straight_in_cards(normal_cards, jokers)
    if straight_cards:
        return "straight", straight_cards, 500
    
    # 7. 트리플 체크
    for rank, cards in rank_groups.items():
        if len(cards) >= 3:
            return "triple", cards[:3], 400
        elif len(cards) == 2 and len(jokers) >= 1:
            return "triple", cards + jokers[:1], 400
    
    # 8. 투페어 체크
    if len(pairs) >= 2:
        pair1_cards = rank_groups[pairs[0]][:2]
        pair2_cards = rank_groups[pairs[1]][:2]
        return "two_pair", pair1_cards + pair2_cards, 300
    elif len(pairs) == 1 and len(jokers) >= 1:
        # 조커로 투페어 완성
        pair_cards = rank_groups[pairs[0]][:2]
        other_ranks = [r for r in rank_groups.keys() if r != pairs[0] and len(rank_groups[r]) >= 1]
        if other_ranks:
            return "two_pair", pair_cards + rank_groups[other_ranks[0]][:1] + jokers[:1], 300
    
    # 9. 원페어 체크
    if pairs:
        return "pair", rank_groups[pairs[0]][:2], 200
    elif len(jokers) >= 1 and normal_cards:
        # 조커로 페어 완성
        any_card = normal_cards[0]
        return "pair", [any_card] + jokers[:1], 200
    
    return None, [], 0


def check_straight_in_cards(cards, jokers):
    """
    카드들에서 스트레이트 확인
    조커를 와일드카드로 사용
    """
    if len(cards) + len(jokers) < 5:
        return None
    
    # 카드 값 정렬
    values = sorted([get_rank_value(c.get('rank', '')) for c in cards])
    
    # A는 1 또는 14로 사용 가능
    if 1 in values:
        values.append(14)
    
    # 연속 5개 찾기
    for start_val in range(1, 11):  # 1~10 시작 가능
        sequence = list(range(start_val, start_val + 5))
        missing = 0
        matched_cards = []
        
        for val in sequence:
            actual_val = val if val <= 13 else 1  # 14는 A로
            matching_card = next((c for c in cards if get_rank_value(c.get('rank', '')) == actual_val), None)
            
            if matching_card:
                matched_cards.append(matching_card)
            else:
                missing += 1
        
        if missing <= len(jokers):
            return matched_cards + jokers[:missing]
    
    return None


def get_suit_element(suit):
    """무늬에 따른 속성 반환"""
    elements = {
        "spade": ("dark", "암흑"),
        "heart": ("light", "빛"),
        "diamond": ("earth", "대지"),
        "club": ("poison", "독")
    }
    return elements.get(suit, ("neutral", "무속성"))


# ============================================================
# 마술사 스킬 생성
# ============================================================

def create_magician_skills():
    """마술사 스킬 생성 (트릭 덱 시스템) - 트리키한 플레이 특화"""
    skills = []
    
    # ============================================================
    # 기본 공격 (카드 드로우 + 카드 효과 발동)
    # ============================================================
    
    # 1. 카드 슬래시 (기본 BRV) - 드로우한 카드 숫자 효과 발동
    card_slash = Skill(
        "magician_card_slash",
        "카드 슬래시",
        "카드로 베어 BRV 피해. 드로우한 카드의 [숫자 효과]가 자동 발동!"
    )
    card_slash.effects = [
        DamageEffect(DamageType.BRV, 0.7)
    ]
    card_slash.costs = []
    card_slash.sfx = ("combat", "attack_magic")
    card_slash.metadata = {
        "basic_attack": True,
        "card_draw": 1,
        "attack_type": "brv",
        "apply_rank_effect": True  # 숫자 효과 적용
    }
    skills.append(card_slash)
    
    # 2. 트릭 샷 (기본 HP) - 드로우한 카드 무늬 효과 발동
    trick_shot = Skill(
        "magician_trick_shot",
        "트릭 샷",
        "기발한 각도로 HP 타격. 드로우한 카드의 [무늬 효과]가 자동 발동!"
    )
    trick_shot.effects = [
        DamageEffect(DamageType.HP, 0.5)
    ]
    trick_shot.costs = []
    trick_shot.sfx = ("combat", "attack_magic")
    trick_shot.metadata = {
        "basic_attack": True,
        "card_draw": 1,
        "attack_type": "hp",
        "apply_suit_effect": True  # 무늬 효과 적용
    }
    skills.append(trick_shot)
    
    # ============================================================
    # 트리키 유틸리티 스킬
    # ============================================================
    
    # 3. 더블 오어 낫띵 - 도박 스킬
    double_or_nothing = Skill(
        "magician_double_or_nothing",
        "더블 오어 낫띵",
        "카드 1장을 뒤집어 빨간색(♥♦)이면 다음 공격 2배, 검은색(♠♣)이면 자해 30%!"
    )
    double_or_nothing.effects = []  # 특수 처리
    double_or_nothing.costs = [MPCost(5)]
    double_or_nothing.target_type = "self"
    double_or_nothing.sfx = ("skill", "buff")
    double_or_nothing.metadata = {
        "gamble": True,
        "card_flip": 1,
        "red_effect": {"damage_mult": 2.0, "duration": 1},
        "black_effect": {"self_damage_percent": 0.3}
    }
    skills.append(double_or_nothing)
    
    # 4. 마인드 리딩 - 적 다음 행동 예측
    mind_reading = Skill(
        "magician_mind_reading",
        "마인드 리딩",
        "손패에서 같은 무늬 2장 소모. 적의 다음 행동을 예측하여 3턴간 회피율 +50%, 받는 피해 -30%"
    )
    mind_reading.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.5, duration=3),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=3)
    ]
    mind_reading.costs = [MPCost(12)]
    mind_reading.target_type = "self"
    mind_reading.sfx = ("skill", "buff")
    mind_reading.metadata = {
        "required_same_suit": 2,
        "consume_cards": True,
        "predict_enemy": True
    }
    skills.append(mind_reading)
    
    # 5. 리버스 카드 - 적 버프/디버프 반전
    reverse_card = Skill(
        "magician_reverse_card",
        "리버스 카드",
        "손패에서 5 카드 1장 소모. 적의 모든 버프를 디버프로, 디버프를 버프로 뒤집는다!"
    )
    reverse_card.effects = []  # 특수 처리
    reverse_card.costs = [MPCost(18)]
    reverse_card.sfx = ("skill", "debuff")
    reverse_card.metadata = {
        "required_rank": "5",
        "consume_cards": True,
        "reverse_all_effects": True
    }
    skills.append(reverse_card)
    
    # 6. 스탯 스왑 - 적과 스탯 교환
    stat_swap = Skill(
        "magician_stat_swap",
        "스탯 스왑",
        "[투페어 필요] 3턴간 적과 자신의 공격력/방어력을 바꿔치기! 강적에게 효과적!"
    )
    stat_swap.effects = []  # 특수 처리
    stat_swap.costs = [MPCost(20)]
    stat_swap.sfx = ("skill", "debuff")
    stat_swap.metadata = {
        "required_combination": "two_pair",
        "consume_cards": True,
        "swap_stats": ["attack", "defense"],
        "duration": 3
    }
    skills.append(stat_swap)
    
    # 7. 미러 포스 - 받은 피해 반사
    mirror_force = Skill(
        "magician_mirror_force",
        "미러 포스",
        "J(나이트) 카드 소모. 2턴간 받는 피해의 100%를 공격자에게 반사!"
    )
    mirror_force.effects = [
        BuffEffect(BuffType.COUNTER, 1.0, duration=2)  # 100% 반사
    ]
    mirror_force.costs = [MPCost(15)]
    mirror_force.target_type = "self"
    mirror_force.sfx = ("skill", "protect")
    mirror_force.metadata = {
        "required_rank": "J",
        "consume_cards": True,
        "reflect_damage": 1.0,
        "duration": 2
    }
    skills.append(mirror_force)
    
    # 8. 타임 봄 - 지연 폭발
    time_bomb = Skill(
        "magician_time_bomb",
        "타임 봄",
        "[스트레이트 필요] 적에게 시한폭탄 설치. 3턴 후 현재 손패 장수 × 0.8배 광역 폭발!"
    )
    time_bomb.effects = [
        StatusEffect(StatusType.DOOM, duration=3, value=0.8)
    ]
    time_bomb.costs = [MPCost(22)]
    time_bomb.sfx = ("skill", "curse")
    time_bomb.metadata = {
        "required_combination": "straight",
        "consume_cards": True,
        "delayed_damage": True,
        "delay_turns": 3,
        "damage_per_card": 0.8,
        "is_aoe": True
    }
    skills.append(time_bomb)
    
    # 9. 카드 카운터 - 덱 서치
    card_counter = Skill(
        "magician_card_counter",
        "카드 카운터",
        "덱에서 원하는 숫자의 카드 1장을 찾아 손패에 추가. 조합 완성에 필수!"
    )
    card_counter.effects = []  # 특수 처리
    card_counter.costs = [MPCost(8)]
    card_counter.target_type = "self"
    card_counter.sfx = ("skill", "buff")
    card_counter.metadata = {
        "search_deck": True,
        "search_by_rank": True
    }
    skills.append(card_counter)
    
    # 10. 슬립 오브 핸드 - 버프 훔치기
    sleight_hand = Skill(
        "magician_sleight_hand",
        "슬립 오브 핸드",
        "[트리플 필요] 적의 버프 2개를 훔쳐 자신에게 적용! 적은 해당 버프 상실."
    )
    sleight_hand.effects = []  # 특수 처리
    sleight_hand.costs = [MPCost(18)]
    sleight_hand.sfx = ("skill", "debuff")
    sleight_hand.metadata = {
        "required_combination": "triple",
        "consume_cards": True,
        "steal_buffs": 2
    }
    skills.append(sleight_hand)
    
    # 11. 페이탈 플러시 - 무늬별 속성 폭격
    fatal_flush = Skill(
        "magician_fatal_flush",
        "페이탈 플러시",
        "[플러시 필요] 5장 무늬에 따른 속성 폭격! ♠암흑 ♥흡혈 ♦방무 ♣맹독"
    )
    fatal_flush.effects = [
        DamageEffect(DamageType.BRV_HP, 2.2)
    ]
    fatal_flush.costs = [MPCost(25)]
    fatal_flush.is_aoe = True
    fatal_flush.target_type = "all_enemies"
    fatal_flush.sfx = ("skill", "elemental")
    fatal_flush.metadata = {
        "required_combination": "flush",
        "consume_cards": True,
        "element_by_suit": True,
        "suit_bonuses": {
            "spade": {"defense_ignore": 0.5},
            "heart": {"lifesteal": 0.5},
            "diamond": {"crit_damage": 0.5},
            "club": {"poison_duration": 5}
        }
    }
    skills.append(fatal_flush)
    
    # 12. 풀하우스 카오스 - 전장 뒤집기
    full_house_chaos = Skill(
        "magician_full_house_chaos",
        "풀하우스 카오스",
        "[풀하우스 필요] 전장의 모든 수치를 뒤섞는다! 적↔아군 BRV 교환, HP% 역전!"
    )
    full_house_chaos.effects = []  # 특수 처리
    full_house_chaos.costs = [MPCost(30)]
    full_house_chaos.is_aoe = True
    full_house_chaos.target_type = "all"
    full_house_chaos.sfx = ("skill", "ultimate")
    full_house_chaos.metadata = {
        "required_combination": "full_house",
        "consume_cards": True,
        "swap_brv": True,  # 적과 아군 BRV 교환
        "invert_hp_percent": True  # HP% 역전 (30% → 70%)
    }
    skills.append(full_house_chaos)
    
    # 13. 포카드 오버킬 - 극대 단일 피해
    four_kind_overkill = Skill(
        "magician_four_kind_overkill",
        "포카드 오버킬",
        "[포카드 필요] 4장의 힘을 모아 단일 대상 말살! 숫자가 높을수록 데미지 증가!"
    )
    four_kind_overkill.effects = [
        DamageEffect(DamageType.BRV, 2.5),
        DamageEffect(DamageType.HP, 4.0)
    ]
    four_kind_overkill.costs = [MPCost(35)]
    four_kind_overkill.sfx = ("skill", "explosion")
    four_kind_overkill.metadata = {
        "required_combination": "four_of_kind",
        "consume_cards": True,
        "rank_damage_bonus": True,  # A=1.0, K=1.3 배율
        "execute_threshold": 0.2  # HP 20% 이하 즉사
    }
    skills.append(four_kind_overkill)
    
    # 14. 조커 와일드 - 적 스킬 복사
    joker_wild = Skill(
        "magician_joker_wild",
        "조커 와일드",
        "🃏 조커 카드 소모. 적이 마지막으로 사용한 스킬을 그대로 복사하여 사용!"
    )
    joker_wild.effects = []  # 특수 처리
    joker_wild.costs = [MPCost(20)]
    joker_wild.sfx = ("skill", "cast_complete")
    joker_wild.metadata = {
        "required_joker": True,
        "consume_cards": True,
        "copy_last_enemy_skill": True
    }
    skills.append(joker_wild)
    
    # ============================================================
    # 궁극기
    # ============================================================
    
    # 15. 로얄 스트레이트 플러시 (궁극기)
    ultimate = Skill(
        "magician_ultimate",
        "로얄 스트레이트 플러시",
        "[로얄 스트레이트 플러시] 궁극의 조합! 적 전체 현재HP 50% 고정피해 + 모든 버프 제거 + 아군 풀회복 + 5턴 무적"
    )
    ultimate.effects = [
        DamageEffect(DamageType.HP, 3.0),
        StatusEffect(StatusType.STUN, duration=2, value=1.0),
        HealEffect(percentage=1.0)
    ]
    ultimate.costs = [MPCost(50)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 99
    ultimate.is_aoe = True
    ultimate.target_type = "all"
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "required_combination": "royal_straight_flush",
        "consume_cards": True,
        "ultimate": True,
        "current_hp_percent_damage": 0.5,
        "strip_all_buffs": True,
        "grant_invincible": 5
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크 스킬
    # ============================================================
    
    # 16. 럭키 드로우
    teamwork = TeamworkSkill(
        "magician_teamwork",
        "럭키 드로우",
        "아군 전체가 각자 카드 1장을 뽑아 해당 카드의 숫자 효과를 즉시 받는다!",
        gauge_cost=150
    )
    teamwork.effects = [
        BuffEffect(BuffType.LUCK, 0.3, duration=3),
        BuffEffect(BuffType.CRITICAL_UP, 0.2, duration=3)
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "magician": True,
        "party_card_draw": True,
        "apply_rank_effect_to_all": True
    }
    skills.append(teamwork)
    
    return skills


def register_magician_skills(sm):
    """스킬 매니저에 마술사 스킬 등록"""
    skills = create_magician_skills()
    for s in skills:
        sm.register_skill(s)
    
    logger.info(f"마술사 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]


# ============================================================
# 스킬 실행 시 트릭 덱 처리 함수
# ============================================================

def execute_magician_skill(character, skill, target, context):
    """
    마술사 스킬 실행 시 트릭 덱 처리
    이 함수는 skill_executor에서 호출됩니다.
    """
    metadata = skill.metadata or {}
    results = []
    
    # 1. 카드 드로우 처리
    if metadata.get('card_draw'):
        draw_count = metadata['card_draw']
        
        # 손재주 특성 체크 (기본 공격 시 추가 드로우)
        if metadata.get('basic_attack') and has_trait(character, 'sleight_of_hand'):
            draw_count += 1
        
        drawn = draw_cards(character, draw_count)
        card_names = [get_card_name(c) for c in drawn]
        results.append(f"드로우: {', '.join(card_names)}")
    
    # 2. 셔플 처리
    if metadata.get('shuffle_hand'):
        hand = getattr(character, 'card_hand', [])
        discard = getattr(character, 'card_discard', [])
        
        # 손패 모두 버림
        discard.extend(hand)
        character.card_hand = []
        character.card_discard = discard
        
        results.append(f"손패 {len(hand)}장 폐기")
        
        # 새로 드로우
        draw_count = metadata.get('card_draw', 4)
        drawn = draw_cards(character, draw_count)
        card_names = [get_card_name(c) for c in drawn]
        results.append(f"새 드로우: {', '.join(card_names)}")
    
    # 3. 포커 조합 스킬 처리
    if metadata.get('required_combination'):
        required = metadata['required_combination']
        hand = getattr(character, 'card_hand', [])
        
        # 조합 확인
        combo_type, combo_cards, score = check_poker_combination(hand)
        
        if combo_type != required and required != "pair":  # pair는 모든 조합에서 사용 가능
            # 조합이 맞지 않으면 실패
            results.append(f"조합 실패! {required} 필요 (현재: {combo_type or '없음'})")
            return {"success": False, "results": results}
        
        # 조커 보너스 체크
        joker_bonus = 1.0
        if any(c.get('is_joker') for c in combo_cards):
            if has_trait(character, 'wild_card'):
                joker_bonus = 1.3  # 데미지 +30%
            results.append("🃏 조커 사용!")
        
        # 카드 소모
        if metadata.get('consume_cards'):
            discard_cards(character, combo_cards)
            card_names = [get_card_name(c) for c in combo_cards]
            results.append(f"사용한 카드: {', '.join(card_names)}")
        
        # 특수 효과 처리
        if metadata.get('swap_buffs'):
            # 투페어 스왑: 버프/디버프 교환
            results.append("버프/디버프 교환!")
        
        if metadata.get('element_by_suit'):
            # 플러시 원소: 무늬에 따른 속성
            main_suit = combo_cards[0].get('suit') if combo_cards else 'spade'
            element_id, element_name = get_suit_element(main_suit)
            results.append(f"속성: {element_name}")
        
        return {
            "success": True, 
            "results": results, 
            "bonus_multiplier": joker_bonus,
            "combo_type": combo_type,
            "combo_cards": combo_cards
        }
    
    return {"success": True, "results": results}


def has_trait(character, trait_id):
    """캐릭터가 특정 특성을 가지고 있는지 확인"""
    if not hasattr(character, 'active_traits'):
        return False
    
    for trait in character.active_traits:
        tid = trait if isinstance(trait, str) else trait.get('id')
        if tid == trait_id:
            return True
    
    return False


def initialize_trick_deck(character):
    """마술사 트릭 덱 초기화"""
    character.card_deck = shuffle_deck(create_deck())
    character.card_hand = []
    character.card_discard = []
    character.max_hand_size = 8
    
    logger.info(f"{character.name} 트릭 덱 초기화 완료 (54장)")


def get_hand_display(character):
    """손패 표시용 문자열 반환"""
    hand = getattr(character, 'card_hand', [])
    if not hand:
        return "손패: (없음)"
    
    card_names = [get_card_name(c) for c in hand]
    combo_type, combo_cards, score = check_poker_combination(hand)
    
    combo_display = ""
    if combo_type:
        combo_names = {
            "pair": "원페어",
            "two_pair": "투페어",
            "triple": "트리플",
            "straight": "스트레이트",
            "flush": "플러시",
            "full_house": "풀하우스",
            "four_of_kind": "포카드",
            "straight_flush": "스트레이트 플러시",
            "royal_straight_flush": "로얄 스트레이트 플러시"
        }
        combo_display = f" [★ {combo_names.get(combo_type, combo_type)}]"
    
    return f"손패 ({len(hand)}/8): {', '.join(card_names)}{combo_display}"
