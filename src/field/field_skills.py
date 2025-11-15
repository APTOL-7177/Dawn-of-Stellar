"""
Field Skills - 필드 스킬 관리자

자물쇠 해제, 탐지, 은신 등의 필드 스킬
"""

from typing import Dict, Any, Optional
from src.character.skill_types import (
    skill_type_registry,
    SkillCategory
)
from src.core.logger import get_logger


class FieldSkillManager:
    """필드 스킬 매니저"""

    def __init__(self) -> None:
        self.logger = get_logger("field_skills")

        # 필드 스킬 타입들 가져오기
        self.field_skills = skill_type_registry.get_by_category(SkillCategory.FIELD)

    def use_skill(
        self,
        skill_type_id: str,
        user: Any,
        target: Any,
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        필드 스킬 사용

        Args:
            skill_type_id: 스킬 타입 ID
            user: 사용자
            target: 대상
            context: 컨텍스트

        Returns:
            실행 결과
        """
        skill_type = skill_type_registry.get(skill_type_id)

        if not skill_type:
            self.logger.warning(f"알 수 없는 스킬 타입: {skill_type_id}")
            return None

        if skill_type.category != SkillCategory.FIELD:
            self.logger.warning(f"필드 스킬이 아님: {skill_type_id}")
            return None

        # 사용 가능 여부 확인
        if not skill_type.can_use(user, context):
            self.logger.info(f"스킬 사용 불가: {skill_type.name}")
            return None

        # 스킬 실행
        result = skill_type.execute(user, target, context)

        self.logger.info(
            f"필드 스킬 사용: {skill_type.name}",
            {"user": user.name if hasattr(user, "name") else "Unknown", "result": result}
        )

        return result

    def get_available_skills(self, user: Any) -> list:
        """사용 가능한 필드 스킬 목록"""
        available = []

        for skill_type in self.field_skills:
            if skill_type.can_use(user, {}):
                available.append(skill_type)

        return available


# 전역 인스턴스
field_skill_manager = FieldSkillManager()
