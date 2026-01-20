from abc import ABC, abstractmethod
from typing import List, Dict, AsyncGenerator

class BaseLLM(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]]) -> str:
        pass

    @abstractmethod
    async def stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        pass
