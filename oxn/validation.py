"""
Purpose: Validates experiment specifications.
Functionality: Implements syntactic and semantic validation of experiment configurations.
Connection: Used by the Engine to ensure the experiment configuration is correct before execution.
"""
import os
import json
import jsonschema
from typing import Set, List
from pathlib import Path

from .errors import OxnException
from .jaeger import Jaeger
from .prometheus import Prometheus
from .settings import SCHEMA_PATH

def load_schema():
    """Load the JSON schema file"""
    with open(SCHEMA_PATH) as f:
        return json.load(f)

class SemanticValidator:
    """Semantic validation for experiment specifications"""

    def __init__(self, experiment_spec: dict):
        self.experiment_spec = experiment_spec
        self.prometheus = Prometheus()
        self.jaeger = Jaeger()
        self.metric_names = None
        self.label_names = None
        self.label_values = None
        self.service_names = None
        self.messages: List[str] = []
        
        # Perform syntactic validation
        self.validate_syntax()
        
        # Then populate data for semantic validation
        self._populate_metrics()
        self._populate_labels()
        self._populate_label_values()
        self._populate_service_names()

    def validate_syntax(self):
        """Validate the experiment specification against JSON schema"""
        try:
            schema = load_schema()
            jsonschema.validate(instance=self.experiment_spec, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            raise OxnException(
                message="Experiment specification failed JSON schema validation",
                explanation=str(e)
            )

    def _populate_service_names(self) -> Set[str]:
        """Call jaeger to get a list of service names from Jaeger traces"""
        service_names = self.jaeger.get_services()
        self.service_names = set(service_names)
        return self.service_names

    def _populate_metrics(self) -> Set[str]:
        """Call Prometheus to get a list of existing metric names"""
        prometheus_response = self.prometheus.metrics()
        metric_names = prometheus_response["data"]
        self.metric_names = set(metric_names)
        return self.metric_names

    def _populate_labels(self) -> Set[str]:
        """Call Prometheus to get all labels it knows about"""
        prometheus_response = self.prometheus.labels()
        label_names = prometheus_response["data"]
        self.label_names = set(label_names)
        return self.label_names

    def _populate_label_values(self) -> dict[str, Set[str]]:
        """For a given label, get all legal label values"""
        self.label_values = {}
        for label in self.label_names:
            prometheus_response = self.prometheus.label_values(label=label)
            label_values = prometheus_response["data"]
            self.label_values[label] = set(label_values)
        return self.label_values

    def _validate_metric_name(self, name: str) -> None:
        """A metric name is valid if it is recognized by Prometheus"""
        if name not in self.metric_names:
            self.messages.append(f"Prometheus does not recognize metric name {name}")

    def _validate_label_name(self, label: str) -> bool:
        """A label name is valid if it is recognized by Prometheus"""
        return label in self.label_names

    def _validate_label_value(self, label: str, label_value: str) -> bool:
        """A label value is valid if it is recognized by Prometheus given a valid label name"""
        return (
                self._validate_label_name(label=label)
                and label_value in self.label_values[label]
        )

    def _validate_labels(self, labels: dict):
        """Validate the labels dict from a metric response variable"""
        for k, v in labels.items():
            if not self._validate_label_name(k):
                self.messages.append(f"Prometheus does not recognize label name {k}")
            if not self._validate_label_value(k, v):
                self.messages.append(f"Prometheus does not recognize label value {v} for label {k}")

    def validate_metric_response_description(self, response: dict) -> None:
        """Validate a single metric response variable description"""
        rvar_name = next(iter(response))
        rvar = response[rvar_name]
        metric_name = rvar["metric_name"]
        try:
            rvar_labels = response[rvar_name]["labels"]
        except KeyError:
            rvar_labels = {}
        self._validate_metric_name(metric_name),
        self._validate_labels(rvar_labels),

    def validate_trace_response_description(self, response: dict):
        """Validate a single trace response description from an experiment specification"""
        rvar_name = next(iter(response))
        service_name = response[rvar_name]["service_name"]
        if service_name not in self.service_names:
            self.messages.append(f"Jaeger does not know service name {rvar_name}")

    def validate_treatment(self, treatment_description: dict):
        """
        Validate a single treatment description from an experiment specification
        """
        raise NotImplementedError

    def validate_response(self, response: dict):
        """Validate a response variable"""
        rvar_name = next(iter(response))
        rvar_type = response[rvar_name]["type"]
        # trace/metric is already validated by syntax schema
        if rvar_type == "metric":
            self.validate_metric_response_description(response=response)
        if rvar_type == "trace":
            self.validate_trace_response_description(response=response)

    def validate_responses(self):
        """Validate the response section in the specification"""
        responses = self.experiment_spec["experiment"]["responses"]
        for response in responses:
            self.validate_response(response=response)

    def validate_treatments(self):
        treatments = self.experiment_spec["experiment"]["treatments"]
        for treatment in treatments:
            self.validate_treatment(treatment_description=treatment)

    def validate(self):
        """Validate the experiment specification"""
        self.validate_responses()

        if self.messages:
            # something did not validate
            message = "\n".join(self.messages)
            raise OxnException(
                message="Experiment specification did not pass semantic validation",
                explanation=message,
            )
