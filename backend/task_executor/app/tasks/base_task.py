"""
Base Task Handler
모든 태스크 핸들러의 기본 클래스
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTask(ABC):
    """태스크 핸들러 기본 클래스"""
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        작업 실행
        
        Args:
            action: 실행할 액션 이름
            params: 작업 파라미터
            
        Returns:
            작업 결과
        """
        pass
    
    def validate_params(self, params: Dict[str, Any], required: list) -> bool:
        """파라미터 유효성 검사"""
        for key in required:
            if key not in params:
                raise ValueError(f"필수 파라미터가 누락되었습니다: {key}")
        return True

