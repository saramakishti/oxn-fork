""" 
Purpose: Defines the base class for treatments.
Functionality: Provides an abstract base class Treatment with methods to be implemented by subclasses.
Connection: Used as a base class for specific treatment implementations in treatments.py.
 """

import abc
from typing import List
import logging
import uuid

from backend.internal.errors import OxnException
from backend.internal.utils import humanize_utc_timestamp
from backend.internal.models.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


# TODO: think about refactoring validation of params into validator class so it can happen earlier

class Treatment(abc.ABC):
    def __init__(self, config, name, orchestrator):
        self.id: str = uuid.uuid4().hex
        """Random machine-readable unique identifier"""
        self.name: str = name
        """The name of the treatment as provided in the experiment specification"""
        self.orchestrator: Orchestrator = orchestrator
        """A reference to the orchestrator instance"""
        self.config: dict = config
        """A dictionary containing parameter names and supplied parameter values from the experiment specification"""
        self.start = None
        """A unix float timestamp in utc indicating when the treatment instance has been started"""
        self.end = None
        """A unix float timestamp in utc indicating when the treatment instance has finished execution"""
        self.messages = []
        """A list of strings to provide helpful messages to the user in case of any errors"""
        validates = self._validate_params()
        """Validate the parameters the treatment instance was provided with"""

        if not validates:
            raise OxnException(
                message=f"Invalid configuration for {self.__repr__()} provided.",
                explanation="\n".join(self.messages),
            )
        
        orchestrator_validates = self._validate_orchestrator()
        if not orchestrator_validates:
            raise OxnException(
                message=f"Invalid orchestrator for {self.__repr__()} provided.",
                explanation="\n".join(self.messages),
            )

        self._transform_params()
        """Populate the treatment with any additional values depending on user-supplied parameters"""

    def __repr__(self):
        config_string = [f"{key}={value}, " for key, value in self.config.items()]
        return f"{self.__class__.__name__}(name={self.name}, {''.join(config_string)})"

    @property
    def treatment_type(self):
        return self.__class__.__name__

    @property
    def short_id(self):
        """Return the truncated id for the treatment instance"""
        return self.id[:8]

    @property
    def humanize_start_time(self):
        """Provide a human-readable version of the start timestamp"""
        return humanize_utc_timestamp(self.start)

    @property
    def humanize_end_time(self):
        """Provide a human-readable version of the end timestamp"""
        return humanize_utc_timestamp(self.end)

    @property
    @abc.abstractmethod
    def action(self):
        """The action key is used to match treatment descriptions from the experiment specification"""
        return self.action

    @abc.abstractmethod
    def preconditions(self) -> bool:
        """
        Return true if the preconditions for this treatment are met.

        Preconditions can be anything that is required for the treatment to successfully execute,
        such as third-party software. An implementation of this message should populate the messages
        instance variable to provide helpful error messages in case of unmet preconditions.
        Implementations for runtime treatments of this method can depend on a provisioned SUE,
        while implementations for compile time treatments cannot.

        :return: A boolean indicating if the preconditions for this treatment are met
        """
        logger.info(f"Checking preconditions for treatment {self.name}")

    @abc.abstractmethod
    def inject(self) -> None:
        """
        Inject the treatment. This method takes no arguments. Arguments to the injection function
        need to be supplied via the params method.

        :return: None
        """
        logger.info(f"Injecting treatment {self.name}")

    @abc.abstractmethod
    def clean(self) -> None:
        """
        Clean any residual effects of the treatment injection.
        :return:
        """
        logger.info(f"Cleaning treatment {self.name}")

    @abc.abstractmethod
    def params(self) -> dict:
        """
        Return parameters of the Treatment together with expected types
        :return: A dictionary mapping parameter names to parameter types
        """

    @abc.abstractmethod
    def _validate_params(self) -> bool:
        """
        Validate the supplied parameters for this treatment.
        This method should return true on a valid config, false otherwise.
        It can optionally populate the message dict with a helpful error message.
        """

    @abc.abstractmethod
    def _transform_params(self) -> None:
        """
        Optionally transform any supplied parameters into a format required by the treatment
        This method returns None and should update the values in self.config.
        This method can be used to supply additional parameters to the injection and cleanup methods,
        depending on the use case.
        """

    @abc.abstractmethod
    def is_runtime(self) -> bool:
        """
        Return True if the treatment is a runtime treatment and False otherwise

        Runtime treatments are treatments that are executed when the system under test is
        built and running, while compile time treatments are executed before the system under test is built.
        Compile time treatments change properties about the system that require a restart of the system or a rebuilding
        of the systems containers. We decided on introducing this distinction as it avoids having to restart
        containers during the runtime of the experiment, which sometimes made implementation awkward and lead to
        unexpected artefacts in the experiment data.


        :return: bool
        """
        return True

    @abc.abstractmethod
    def _validate_orchestrator(self, valid_for: List[str]) -> bool:
        """
        Validate if the orchestrator is suitable for this treatment.
        This method should return true if the orchestrator is valid, false otherwise.
        """
        return self.orchestrator.get_orchestrator_type() in valid_for