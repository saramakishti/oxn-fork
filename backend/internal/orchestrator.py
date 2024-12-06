from abc import ABC, abstractmethod

class Orchestrator(ABC):
    @abstractmethod
    def orchestrate(self):
        pass
    
    @abstractmethod
    def ready(self, expected_services=None, timeout=None):
        pass
    
    @abstractmethod
    def teardown(self):
        pass 