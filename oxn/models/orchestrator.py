from abc import ABC, abstractmethod
from typing import List, Tuple

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

    @abstractmethod
    def execute_console_command(self, service: str, command: List[str]) -> Tuple[int, str]:
        """
        Execute a console command on the orchestrator

        Args:
            service: The service to execute the command on
            command: The command to execute

        Returns:
            A tuple of the return code and the output of the command

        """
        pass

    @abstractmethod
    def get_address_for_service(self, service: str) -> str:
        """
        Get the address for a service

        Args:
            service: The service to get the address for

        Returns:
            The address of the service

        """
        pass

    @abstractmethod
    def get_prometheus_address(self) -> str:
        """
        Get the address for the Prometheus service

        Returns:
            The address of the Prometheus service

        """
        pass

    @abstractmethod
    def get_jaeger_address(self) -> str:
        """
        Get the address for the Jaeger service

        Returns:
            The address of the Jaeger service

        """
        pass
