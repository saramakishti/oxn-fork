from abc import ABC, abstractmethod
from typing import List

class Orchestrator(ABC):
    """
    Abstract base class for orchestrators.
    """

    @abstractmethod
    def orchestrate(self):
        pass

    @abstractmethod
    def ready(self, expected_services: List[str] = None, timeout: int = 120) -> bool:
        pass

    @abstractmethod
    def teardown(self):
        pass

    @abstractmethod
    def translate_compose_names(self, compose_names: List[str]):
        pass

    @abstractmethod
    def translate_container_names(self, container_names: List[str]):
        pass

    @property
    @abstractmethod
    def running_services(self) -> List[str]:
        pass
