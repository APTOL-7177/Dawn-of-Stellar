"""Job Stats Loader - 직업별 스탯 로더"""
import yaml
from pathlib import Path
from typing import Dict, Any
from src.core.logger import get_logger

class JobStatsLoader:
    """직업 스탯 로더"""
    def __init__(self):
        self.logger = get_logger("job_stats")
        self.stats = {}
        self._load_stats()
    
    def _load_stats(self):
        """스탯 YAML 로드"""
        stats_file = Path(__file__).parent.parent.parent / "data" / "jobs" / "stats_base.yaml"
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                self.stats = yaml.safe_load(f)
            self.logger.info(f"직업 스탯 {len(self.stats)}개 로드 완료")
        except Exception as e:
            self.logger.error(f"스탯 로드 실패: {e}")
            self.stats = {}
    
    def get_base_stats(self, job_id: str) -> Dict[str, int]:
        """기본 스탯 반환"""
        if job_id not in self.stats:
            self.logger.warning(f"알 수 없는 직업: {job_id}")
            return self._default_stats()
        return self.stats[job_id].get('base', self._default_stats())
    
    def get_stat_growth(self, job_id: str) -> Dict[str, float]:
        """레벨당 성장률 반환"""
        if job_id not in self.stats:
            return {}
        return self.stats[job_id].get('growth', {})
    
    def calculate_stats_at_level(self, job_id: str, level: int) -> Dict[str, int]:
        """특정 레벨의 스탯 계산"""
        base = self.get_base_stats(job_id)
        growth = self.get_stat_growth(job_id)
        
        result = {}
        for stat, base_value in base.items():
            growth_value = growth.get(stat, 0)
            result[stat] = int(base_value + (level - 1) * growth_value)
        
        return result
    
    def _default_stats(self) -> Dict[str, int]:
        """기본 스탯"""
        return {
            'hp': 100,
            'mp': 50,
            'strength': 10,
            'defense': 10,
            'magic': 10,
            'spirit': 10,
            'speed': 10,
            'luck': 10
        }

_job_stats_loader = None

def get_job_stats_loader() -> JobStatsLoader:
    """전역 스탯 로더"""
    global _job_stats_loader
    if _job_stats_loader is None:
        _job_stats_loader = JobStatsLoader()
    return _job_stats_loader
