"""
Bot Task System

봇의 작업을 관리하는 멀티태스킹 시스템
- 우선순위 기반 작업 처리
- 멀티태스킹 가능 여부 판단
"""

import heapq
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class TaskType(Enum):
    """작업 유형"""
    IDLE = auto()
    MOVE = auto()
    FARM = auto()
    HARVEST = auto()
    COMBAT = auto()
    FOLLOW = auto()
    INTERACT = auto()  # 상호작용 (상자 열기 등)
    WAIT = auto()


@dataclass(order=True)
class BotTask:
    """봇 작업"""
    priority: int
    type: TaskType = field(compare=False)
    data: Dict[str, Any] = field(default_factory=dict, compare=False)
    created_at: float = field(default=0.0, compare=False)
    
    def __str__(self):
        return f"[{self.priority}] {self.type.name} - {self.data}"


class TaskQueue:
    """작업 큐 (멀티태스킹)"""
    
    def __init__(self):
        self.tasks: list[BotTask] = []  # heap
        self.current_tasks: list[BotTask] = []  # 현재 수행 중인 작업들
    
    def add_task(self, task_type: TaskType, priority: int, data: Optional[Dict[str, Any]] = None):
        """작업 추가"""
        if data is None:
            data = {}
        
        task = BotTask(priority=priority, type=task_type, data=data)
        heapq.heappush(self.tasks, task)
    
    def get_next_task(self) -> Optional[BotTask]:
        """다음 작업 가져오기"""
        if self.tasks:
            return heapq.heappop(self.tasks)
        return None
    
    def peek_next_task(self) -> Optional[BotTask]:
        """다음 작업 확인 (제거하지 않음)"""
        if self.tasks:
            return self.tasks[0]
        return None
    
    def clear_tasks(self):
        """모든 작업 제거"""
        self.tasks = []
        self.current_tasks = []
    
    def can_multitask(self, task1: BotTask, task2: BotTask) -> bool:
        """두 작업을 동시에 수행 가능한지 확인"""
        # 호환성 매트릭스
        # True: 동시 수행 가능, False: 불가능
        compatible = {
            (TaskType.MOVE, TaskType.FARM): True,       # 이동하면서 파밍 (스쳐 지나가며)
            (TaskType.MOVE, TaskType.HARVEST): False,   # 채집은 멈춰야 함 (일반적으로)
            (TaskType.MOVE, TaskType.COMBAT): False,    # 전투는 이동 중 불가 (턴제면 더욱)
            (TaskType.MOVE, TaskType.FOLLOW): True,     # 따라가기는 이동의 일종
            
            (TaskType.FOLLOW, TaskType.FARM): True,     # 따라가면서 파밍
            (TaskType.FOLLOW, TaskType.COMBAT): False,
            
            (TaskType.COMBAT, TaskType.FARM): False,    # 전투 중 파밍 불가
            (TaskType.COMBAT, TaskType.HARVEST): False,
        }
        
        # 키 정렬하여 조회
        key = tuple(sorted([task1.type, task2.type], key=lambda x: x.value))
        # 매트릭스에 없으면 기본적으로 False (보수적 접근)
        return compatible.get(key, False)

