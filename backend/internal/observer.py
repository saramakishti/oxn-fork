"""
Purpose: Observes and records response variables during experiments.
Functionality: Initializes response variables and collects data during the experiment.
Connection: Works with responses.py to monitor and collect experiment results.

Module to handle data capture during experiment execution"""
import logging
from typing import Dict, List, Optional
from operator import attrgetter

import pandas as pd
from backend.internal.models.orchestrator import Orchestrator


from backend.internal.responses import MetricResponseVariable, TraceResponseVariable
from backend.internal.models.response import ResponseVariable
from backend.internal.utils import time_string_to_seconds

logger = logging.getLogger(__name__)
logger.info = lambda message: print(message)

class Observer:
    """
    The observer class is responsible for constructing response variables from
    an experiment description and then observing the variables during or after an experiment.
    """

    def __init__(self, config: dict, orchestrator):
        self.config = config
        self.orchestrator = orchestrator
        self.experiment_start: Optional[float] = None
        self.experiment_end: Optional[float] = None
        self._response_variables: Dict[str, ResponseVariable] = {}

    def initialize_variables(self) -> None:
        """Initialize response variables from the experiment specification"""
        if not self.config or not self.experiment_start or not self.experiment_end:
            return

        responses = self.config["experiment"]["responses"]
        for response in responses:
            response_type = response["type"]
            name = response["name"]

            if response_type == "metric":
                response_variable = MetricResponseVariable(
                    orchestrator=self.orchestrator,
                    name=name,
                    experiment_start=self.experiment_start,
                    experiment_end=self.experiment_end,
                    description=response,
                    target=response["target"],
                    right_window=response["right_window"],
                    left_window=response["left_window"],
                )
                self._response_variables[name] = response_variable
            
            elif response_type == "trace":
                response_variable = TraceResponseVariable(
                    orchestrator=self.orchestrator,
                    name=name,
                    experiment_start=self.experiment_start,
                    experiment_end=self.experiment_end,
                    description=response,
                    right_window=response["right_window"],
                    left_window=response["left_window"],
                )
                self._response_variables[name] = response_variable

    def variables(self) -> Dict[str, ResponseVariable]:
        """Return all response variables"""
        return self._response_variables

    def time_to_wait_right(self) -> float:
        """Return the maximum right window time to wait"""
        max_time = 0
        for response in self.variables().values():
            # If we ever implement a response variable that does not have a right window, this will break
            in_seconds = time_string_to_seconds(response.right_window)
            if in_seconds > max_time:
                max_time = in_seconds
        return max_time

    def time_to_wait_left(self) -> float:
        """Return the maximum left window time to wait"""
        max_time = 0
        for response in self.variables().values():
            # If we ever implement a response variable that does not have a left window, this will break
            in_seconds = time_string_to_seconds(response.left_window)
            if in_seconds > max_time:
                max_time = in_seconds
        return max_time

    def get_metric_variables(self) -> list[MetricResponseVariable]:
        """Return the metric variables of this observer"""
        return [
            v
            for _, v in self.variables().items()
            if isinstance(v, MetricResponseVariable)
        ]

    def get_trace_variables(self) -> list[TraceResponseVariable]:
        """Return the trace variables of this observer"""
        return [
            v
            for _, v in self.variables().items()
            if isinstance(v, TraceResponseVariable)
        ]
    def observe(self) -> None:
        for variable in self.variables().values():
            try:
                variable.observe()
            except Exception as e:
                logger.info(f"failed to capture {variable.name}, proceeding. {e}")
