"""Damage Share Effect - 피해 분담 이펙트

대상 아군에게 damage_share 상태를 부여한다.
대상이 피해를 받을 때 share_percent 비율만큼 시전자(linked_to=caster)가 대신 받는다.

YAML 형식:
  - type: damage_share
    target: selected_ally
    share_percent: 0.4
    duration: 3
    linked_to: caster
"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.core.logger import get_logger

logger = get_logger("damage_share_effect")


class DamageShareEffect(SkillEffect):
    """피해 분담 이펙트 - 아군이 받는 피해 일부를 시전자가 대신 받는다.

    대상 캐릭터의 damage_share_links 속성에 링크 정보를 등록한다.
    실제 피해 분담 처리는 combat_manager의 _check_damage_share()에서 수행된다.
    """

    def __init__(self, share_percent: float, duration: int, linked_to: str = "caster"):
        """
        Args:
            share_percent: 분담 비율 (0.0~1.0). 0.4 = 40% 분담
            duration: 지속 턴 수
            linked_to: 피해를 대신 받을 주체 ("caster"만 지원)
        """
        super().__init__(EffectType.BUFF)
        self.share_percent = max(0.0, min(1.0, float(share_percent)))
        self.duration = max(1, int(duration))
        self.linked_to = linked_to

    def execute(self, user, target, context):
        """damage_share 링크를 대상에게 등록한다."""
        result = EffectResult(effect_type=EffectType.BUFF, success=True)

        targets = target if isinstance(target, list) else [target]

        for t in targets:
            if not getattr(t, 'is_alive', True):
                continue
            if t is user:
                # 자기 자신에게는 분담 적용하지 않음
                continue

            # damage_share_links 초기화
            if not hasattr(t, 'damage_share_links'):
                t.damage_share_links = []

            # 동일 분담자의 기존 링크 제거 후 재등록 (중복 방지)
            t.damage_share_links = [
                link for link in t.damage_share_links
                if link.get('sharer') is not user
            ]

            link_info = {
                'sharer': user,           # 피해를 대신 받을 캐릭터 (시전자)
                'share_percent': self.share_percent,
                'duration': self.duration,
                'turns_remaining': self.duration,
            }
            t.damage_share_links.append(link_info)

            logger.info(
                f"[피해분담] {getattr(t, 'name', '?')} → {getattr(user, 'name', '?')}에게 "
                f"{self.share_percent*100:.0f}% 분담 ({self.duration}턴)"
            )

        pct = int(self.share_percent * 100)
        result.message = f"피해 분담 설정: {pct}% ({self.duration}턴)"
        return result
