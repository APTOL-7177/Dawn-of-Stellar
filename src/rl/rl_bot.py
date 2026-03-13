"""RL 봇 - 학습된 모델로 전투 AI

TorchScript 형식으로 내보낸 RL 모델을 로드하여
게임 전투에서 행동을 결정합니다. SB3 의존성이 없습니다.
"""

import os
import numpy as np
from typing import Dict, Any, Optional
from src.core.logger import get_logger

logger = get_logger("rl.rl_bot")

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class RLBot:
    """강화학습 기반 전투 봇

    학습된 TorchScript 모델을 사용하여 전투 행동을 결정합니다.
    모델이 없거나 PyTorch가 설치되지 않은 경우 기본 휴리스틱으로 폴백합니다.

    사용법:
        bot = RLBot("data/models/combat_agent.pt")
        action = bot.get_combat_action(combat_manager, current_char)
        # action: {"type": "skill", "target_index": 0, "skill_id": "fireball"}
    """

    def __init__(self, model_path: str = "data/models/combat_agent.pt"):
        self.model_path = model_path
        self.model: Optional[Any] = None
        self._load_model()

    def _load_model(self) -> None:
        """TorchScript 모델 로드"""
        if not HAS_TORCH:
            logger.warning("PyTorch 미설치 - RL 봇 비활성화, 휴리스틱으로 동작")
            return

        try:
            if os.path.exists(self.model_path):
                self.model = torch.jit.load(self.model_path, map_location="cpu")
                self.model.eval()
                logger.info(f"RL 모델 로드: {self.model_path}")
            else:
                logger.warning(f"RL 모델 파일 없음: {self.model_path} - 휴리스틱으로 동작")
        except Exception as e:
            logger.warning(f"RL 모델 로드 실패: {e} - 휴리스틱으로 동작")
            self.model = None

    def get_combat_action(
        self,
        combat_manager: Any,
        current_char: Any,
    ) -> Dict[str, Any]:
        """전투 행동 결정

        Args:
            combat_manager: 현재 전투 상태 관리자
            current_char: 현재 행동할 캐릭터

        Returns:
            행동 딕셔너리:
            {
                "type": str,           # "skill" | "attack" | "defend" | "item"
                "target_index": int,   # 대상 인덱스
                "skill_id": str,       # 스킬 ID (type=="skill"일 때)
            }
        """
        if self.model is None or not HAS_TORCH:
            return self._heuristic_action(combat_manager, current_char)

        try:
            return self._model_action(combat_manager, current_char)
        except Exception as e:
            logger.warning(f"RL 모델 추론 실패: {e} - 휴리스틱으로 폴백")
            return self._heuristic_action(combat_manager, current_char)

    def _model_action(
        self,
        combat_manager: Any,
        current_char: Any,
    ) -> Dict[str, Any]:
        """모델 기반 행동 선택

        1. StateEncoder로 상태 인코딩
        2. ActionSpaceEncoder로 유효 마스크 획득
        3. 모델 순전파
        4. 마스크 적용 후 argmax로 행동 선택
        5. ActionSpaceEncoder.decode()로 게임 행동 변환
        """
        from src.gym.state_encoder import StateEncoder
        from src.gym.action_space import ActionSpaceEncoder

        # 1. 상태 인코딩
        obs = StateEncoder.encode(combat_manager)  # (517,)

        # 2. 유효 행동 마스크
        action_mask = ActionSpaceEncoder.get_valid_mask(combat_manager, current_char)  # (114,) bool

        # 3. 모델 순전파
        obs_tensor = torch.FloatTensor(obs).unsqueeze(0)  # (1, 517)
        with torch.no_grad():
            logits = self.model(obs_tensor)  # (1, 114)
        logits = logits.squeeze(0)  # (114,)

        # 4. 마스크 적용: 무효 행동을 -inf로
        mask_tensor = torch.BoolTensor(action_mask)
        masked_logits = logits.clone()
        masked_logits[~mask_tensor] = float("-inf")

        # 유효한 행동이 하나도 없으면 전체 허용
        if not mask_tensor.any():
            logger.warning("유효 행동 없음 - 마스크 무시하고 argmax 선택")
            masked_logits = logits

        # 5. argmax로 행동 선택 (결정론적)
        action_id = int(torch.argmax(masked_logits).item())

        # 6. 게임 행동으로 디코딩
        action_dict = ActionSpaceEncoder.decode(action_id, combat_manager, current_char)

        logger.info(
            f"RL 행동 선택: action_id={action_id}, "
            f"type={action_dict.get('type')}, "
            f"skill={action_dict.get('skill_id', '-')}"
        )
        return action_dict

    def _heuristic_action(
        self,
        combat_manager: Any,
        current_char: Any,
    ) -> Dict[str, Any]:
        """기본 휴리스틱 행동 (모델 없을 때 폴백)

        LLMPlayerBot의 강화된 _fallback_action을 활용하여 매우 지능적으로 행동합니다.
        """
        try:
            from src.multiplayer.llm_player_bot import GameStateConverter, LLMPlayerBot
            
            # 전투 상태 변환
            combat_state = GameStateConverter.from_combat_manager(combat_manager, current_char)
            
            # 임시 봇 생성 후 _fallback_action 호출
            job_id = getattr(current_char, 'job_id', 'warrior')
            temp_bot = LLMPlayerBot(current_char.name, job_id=job_id)
            bot_action = temp_bot._fallback_action(combat_state)
            
            # BotAction을 Dict 형식으로 역변환
            action_type_map = {
                "BRV_ATTACK": "brv_attack",
                "HP_ATTACK": "hp_attack",
                "SKILL": "skill",
                "ITEM": "item",
                "DEFEND": "defend",
                "FLEE": "flee"
            }
            # Enum 값 처리 (ActionType)
            action_val = bot_action.action_type.value if hasattr(bot_action.action_type, 'value') else bot_action.action_type
            raw_type = action_type_map.get(str(action_val), "brv_attack")
            
            # 타겟 인덱스 찾기
            target_index = 0
            if bot_action.target_name:
                # 적군에서 먼저 찾기
                enemies = getattr(combat_manager, "enemies", [])
                alive_enemies = [e for e in enemies if getattr(e, 'is_alive', True)]
                found = False
                for i, e in enumerate(alive_enemies):
                    if getattr(e, 'name', '') == bot_action.target_name:
                        target_index = i
                        found = True
                        break
                
                # 아군에서 찾기 (힐, 버프 등)
                if not found:
                    allies = getattr(combat_manager, "allies", getattr(combat_manager, "party", getattr(combat_manager, "_party", [])))
                    if hasattr(allies, "members"):  # Party 객체인 경우
                        allies = allies.members
                    alive_allies = [a for a in allies if getattr(a, 'is_alive', True)]
                    for i, a in enumerate(alive_allies):
                        if getattr(a, 'name', '') == bot_action.target_name:
                            target_index = i
                            break
                        
            return {
                "type": raw_type,
                "target_index": target_index,
                "skill_id": bot_action.skill_id,
                "item_id": bot_action.item_id,
                "reasoning": bot_action.reasoning
            }
            
        except Exception as e:
            logger.warning(f"고급 휴리스틱 행동 실패: {e}")

        # 최후 폴백: 기본 공격
        return {
            "type": "attack",
            "target_index": 0,
            "skill_id": "",
        }

    def get_combat_action_as_bot_action(
        self,
        combat_manager: Any,
        current_char: Any,
    ) -> "BotAction":
        """전투 행동을 BotAction 객체로 반환 (AI 관전 모드용)

        get_combat_action()의 dict 결과를 BotAction으로 변환합니다.
        """
        from src.multiplayer.llm_player_bot import BotAction, ActionType

        action_dict = self.get_combat_action(combat_manager, current_char)

        # ActionSpaceEncoder.decode() 형식: {"action_type": str, "target": obj, "skill": obj}
        # 휴리스틱 폴백 형식: {"type": str, "target_index": int, "skill_id": str}
        # 양쪽 모두 처리
        _type_map = {
            "attack": ActionType.BRV_ATTACK,
            "brv_attack": ActionType.BRV_ATTACK,
            "hp_attack": ActionType.HP_ATTACK,
            "skill": ActionType.SKILL,
            "defend": ActionType.DEFEND,
            "item": ActionType.ITEM,
            "flee": ActionType.FLEE,
        }
        raw_type = action_dict.get("action_type") or action_dict.get("type", "attack")
        action_type = _type_map.get(raw_type, ActionType.BRV_ATTACK)

        # 타겟 이름 결정
        target_name = None
        target_obj = action_dict.get("target")
        if target_obj is not None:
            # ActionSpaceEncoder 형식: target이 캐릭터 객체
            target_name = getattr(target_obj, "name", None)
        else:
            # 휴리스틱 폴백 형식: target_index
            target_index = action_dict.get("target_index")
            if target_index is not None:
                enemies = getattr(combat_manager, "enemies", [])
                alive_enemies = [e for e in enemies if getattr(e, "is_alive", True)]
                if 0 <= target_index < len(alive_enemies):
                    target_name = getattr(alive_enemies[target_index], "name", None)
                elif alive_enemies:
                    target_name = getattr(alive_enemies[0], "name", None)

        # 스킬 ID 결정
        skill_obj = action_dict.get("skill")
        skill_id = None
        if skill_obj is not None:
            skill_id = getattr(skill_obj, "skill_id", None) or getattr(skill_obj, "id", None)
        else:
            skill_id = action_dict.get("skill_id") or None

        # 아이템 ID 결정
        item_obj = action_dict.get("item")
        item_id = None
        if item_obj is not None:
            item_id = getattr(item_obj, "item_id", None) or getattr(item_obj, "id", None)
        else:
            item_id = action_dict.get("item_id") or None

        return BotAction(
            action_type=action_type,
            target_name=target_name,
            skill_id=skill_id,
            item_id=item_id,
            reasoning="RL 모델 결정" if self.is_available else "휴리스틱 결정",
        )

    @property
    def is_available(self) -> bool:
        """RL 봇 사용 가능 여부"""
        return self.model is not None and HAS_TORCH
