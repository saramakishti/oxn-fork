"""
Purpose: Implements various treatments to be applied during experiments.
Functionality: Defines treatment classes that simulate different fault conditions or changes to the services under test.
Connection: Loaded by the Runner to apply treatments during an experiment.

Treatment implementations"""
from html.entities import name2codepoint
import logging
from os import name
import os.path
import tempfile
import time
import re
import trace
from typing import List, Optional, cast
import traceback

import docker
import yaml
import requests
from docker.errors import NotFound as ContainerNotFound
from docker.errors import APIError as DockerAPIError
from kubernetes.client.models.v1_deployment import V1Deployment

from python_on_whales import DockerClient

from backend.internal.kubernetes_orchestrator import KubernetesOrchestrator


from backend.internal.errors import OrchestratorException, OxnException, OrchestratorResourceNotFoundException
from backend.internal.utils import (
    time_string_to_seconds,
    validate_time_string,
    time_string_format_regex,
    add_env_variable, remove_env_variable, to_milliseconds,
)
from backend.internal.models.treatment import Treatment

logger = logging.getLogger(__name__)


class EmptyTreatment(Treatment):
    """
    Empty treatment to represent a simple observation of response variables
    """

    def clean(self) -> None:
        pass

    def _transform_params(self) -> None:
        relative_time_string = self.config.get("duration")
        relative_time_seconds = time_string_to_seconds(relative_time_string)
        self.config["duration_seconds"] = relative_time_seconds

    def _validate_params(self) -> bool:
        bools = []
        for key, value in self.params().items():
            if key in {"duration", } and key not in self.config:
                self.messages.append(f"Parameter {key} has to be supplied")
                bools.append(False)
            if key in self.config and not isinstance(self.config[key], value):
                self.messages.append(f"Parameter {key} has to be of type {str(value)}")
        for key, value in self.config.items():
            if key == "duration":
                if not validate_time_string(value):
                    self.messages.append(
                        f"Parameter {key} has to match {time_string_format_regex}"
                    )
                    bools.append(False)
        return all(bools)

    def inject(self) -> None:
        sleep_duration_seconds = self.config.get("duration_seconds")
        time.sleep(sleep_duration_seconds)

    def params(self) -> dict:
        return {
            "duration": str,
        }

    def preconditions(self) -> bool:
        return True

    @property
    def action(self):
        return "empty"

    def is_runtime(self):
        return True
    
    def _validate_orchestrator(self) -> bool:
        return True


class EmptyKubernetesTreatment(Treatment):
    """
    Empty treatment to represent a simple observation of response variables
    """

    def clean(self) -> None:
        pass

    def _transform_params(self) -> None:
        relative_time_string = self.config.get("duration")
        relative_time_seconds = time_string_to_seconds(relative_time_string)
        self.config["duration_seconds"] = relative_time_seconds

    def _validate_params(self) -> bool:
        bools = []
        for key, value in self.params().items():
            if key in {"duration", } and key not in self.config:
                self.messages.append(f"Parameter {key} has to be supplied")
                bools.append(False)
            if key in self.config and not isinstance(self.config[key], value):
                self.messages.append(f"Parameter {key} has to be of type {str(value)}")
        for key, value in self.config.items():
            if key == "duration":
                if not validate_time_string(value):
                    self.messages.append(
                        f"Parameter {key} has to match {time_string_format_regex}"
                    )
                    bools.append(False)
        return all(bools)

    def inject(self) -> None:
        sleep_duration_seconds = self.config.get("duration_seconds")
        time.sleep(sleep_duration_seconds)

    def params(self) -> dict:
        return {
            "duration": str,
        }

    def preconditions(self) -> bool:
        return True

    @property
    def action(self):
        return "empty"

    def is_runtime(self):
        return True
    
    def _validate_orchestrator(self) -> bool:
        if self.orchestrator.get_orchestrator_type() != "kubernetes":
            self.messages.append(f"{self.name} treatment is only supported for Kubernetes orchestrators")
            return False
        return True


class EmptyDockerComposeTreatment(Treatment):
    """
    Empty treatment to represent a simple observation of response variables
    """

    def clean(self) -> None:
        super().clean()
        pass

    def _transform_params(self) -> None:
        relative_time_string = self.config.get("duration")
        relative_time_seconds = time_string_to_seconds(relative_time_string)
        self.config["duration_seconds"] = relative_time_seconds

    def _validate_params(self) -> bool:
        if self.orchestrator.get_orchestrator_type() != "docker-compose":
            raise OrchestratorException(
                message="Wrong orchestrator type",
                explanation=f"{self.name} treatment is only supported for Docker Compose orchestrators",
            )
        bools = []
        for key, value in self.params().items():
            if key in {"duration", } and key not in self.config:
                self.messages.append(f"Parameter {key} has to be supplied")
                bools.append(False)
            if key in self.config and not isinstance(self.config[key], value):
                self.messages.append(f"Parameter {key} has to be of type {str(value)}")
        for key, value in self.config.items():
            if key == "duration":
                if not validate_time_string(value):
                    self.messages.append(
                        f"Parameter {key} has to match {time_string_format_regex}"
                    )
                    bools.append(False)
        return all(bools)

    def inject(self) -> None:
        super().inject()
        sleep_duration_seconds = self.config.get("duration_seconds")
        time.sleep(sleep_duration_seconds)

    def params(self) -> dict:
        return {
            "duration": str,
        }

    def preconditions(self) -> bool:
        super().preconditions()
        return True

    @property
    def action(self):
        return "empty"

    def is_runtime(self):
        return True



class KubernetesApplySecurityContextTreatment(Treatment):
    """
    Treatment to escalate the privileges of a service account in a Kubernetes cluster
    """

    def clean(self) -> None:
        return
        super().clean()
        namespace = self.config.get("namespace")
        label_selector = self.config.get("label_selector")
        label = self.config.get("label")
        
        assert namespace
        assert label_selector
        assert label
        assert self.config.get("capabilities")
        assert self.config.get("capabilities").get("add")
        assert isinstance(self.orchestrator, KubernetesOrchestrator)
        
        # capabilities should now be the opisite of what was applied in inject (e.g. inject was { add: ["NET_ADMIN"] } so clean should be { remove: ["NET_ADMIN"] })
        capabilities = {"add": []}
        
        error_code, error = self.orchestrator.apply_security_context_to_deployment(
            namespace=namespace,
            label_selector=label_selector,
            label=label,
            capabilities=capabilities
        )
        
        logger.info(f"Applied security context to deployment in {namespace} with {label_selector}={label} with result {error_code}: {error}")

    def _transform_params(self) -> None:
        pass
    
    def _validate_params(self) -> bool:
        bools = []
        for key, value in self.params().items():
            if key in {"capabilities", "namespace", "label_selector", "label"} and key not in self.config:
                self.messages.append(f"Parameter {key} has to be supplied")
                bools.append(False)
            if key in self.config and not isinstance(self.config[key], value):
                self.messages.append(f"Parameter {key} has to be of type {str(value)}")
        for key, value in self.config.items():
            if key == "duration":
                if not validate_time_string(value):
                    self.messages.append(
                        f"Parameter {key} has to match {time_string_format_regex}"
                    )
                    bools.append(False)
        return all(bools)

    def inject(self) -> None:
        super().inject()
        capabilities = self.config.get("capabilities")
        namespace = self.config.get("namespace")
        label_selector = self.config.get("label_selector")
        label = self.config.get("label")
        
        assert namespace
        assert label_selector
        assert label
        assert capabilities and capabilities.get("add")
        assert isinstance(self.orchestrator, KubernetesOrchestrator)
        error_code, error = self.orchestrator.apply_security_context_to_deployment(
            namespace=namespace,
            label_selector=label_selector,
            label=label,
            capabilities=capabilities
        )
        logger.info(f"Applied security context to deployment in {namespace} with {label_selector}={label} with result {error_code}: {error}")
        # TODO: check if the deployment was actually updated and if so, wait for the deployment to be ready

    def params(self) -> dict:
        return {
            "capabilities": dict,
            "namespace": str,
            "label_selector": str,
            "label": str,
        }

    def preconditions(self) -> bool:
        return True

    @property
    def action(self):
        return "security_context_kubernetes"

    def is_runtime(self):
        return False
    
    def _validate_orchestrator(self) -> bool:
        if self.orchestrator.get_orchestrator_type() != "kubernetes":
            self.messages.append(f"{self.name} treatment is only supported for Kubernetes orchestrators")
            return False
        return True




"""
    An Article on Add Java Agents to Existing Kubernetes and Helm Applications Instantly
    https://www.cncf.io/blog/2021/03/24/add-java-agents-to-existing-kubernetes-and-helm-applications-instantly/
    here with better format: https://www.rookout.com/blog/add-java-agents-to-existing-kubernetes-and-helm-applications-instantly/


    Regarding Maria, this treatment seems to be not working as expected and therefore has not to be used in the experiments for the first kubernetes experiments.
"""
class ByteMonkeyTreatment(Treatment):
    """Compile-time treatment that injects faults into a java service"""

    def __init__(self, config, name):
        super().__init__(config, name)
        self.docker_client = docker.from_env()
        self.original_entrypoint = ""
        self.dockerfile_content = ""
        self.temporary_jar_path = ""

    @property
    def action(self):
        return "bytemonkey"

    def preconditions(self) -> bool:
        return True

    def build_entrypoint(self) -> str:
        """Build a modified entrypoint from provided bytemonkey configuration"""
        mode = self.config.get("mode")
        rate = self.config.get("rate")
        template_string = f"-javaagent:byte-monkey.jar=mode:{mode},rate:{rate},"
        return template_string

    def read_dockerfile(self):
        dockerfile_path = self.config.get("dockerfile")
        with open(dockerfile_path, "r") as fp:
            self.dockerfile_content = fp.read()

    def download_jar(self, url="https://github.com/mrwilson/byte-monkey/releases/download/1.0.0/byte-monkey.jar"):
        response = requests.get(url)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix="jar", delete=False) as temporary_jar:
            self.temporary_jar_path = temporary_jar.path
            with open(self.temporary_jar_path, "wb") as fp:
                fp.write(response.content)

    def modify_dockerfile(self):
        """Modify the dockerfile to add the bytemonkey dependency and modify the entrypoint"""
        dockerfile_lines = self.dockerfile_content.splitlines()
        for idx, line in enumerate(dockerfile_lines):
            if line.startswith("ENTRYPOINT"):
                self.original_entrypoint = ""
                dockerfile_lines.insert(idx, f"COPY {self.temporary_jar_path} ./")
                dockerfile_lines[idx] = f"{self.original_entrypoint} {self.build_entrypoint()}"
        return "\n".join(dockerfile_lines)

    def restore_entrypoint(self):
        dockerfile_lines = self.dockerfile_content.splitlines()
        for idx, line in enumerate(dockerfile_lines):
            if line.startswith("ENTRYPOINT"):
                dockerfile_lines[idx] = self.original_entrypoint
        return "\n".join(dockerfile_lines)

    def write_dockerfile(self, new_content: str):
        dockerfile_path = self.config.get("dockerfile")
        with open(dockerfile_path, "w") as fp:
            fp.write(new_content)

    def inject(self) -> None:
        """Update the Dockerfile to modify the java entrypoint and re-build the image"""
        self.read_dockerfile()
        self.write_dockerfile(new_content=self.build_entrypoint())

    def clean(self) -> None:
        """Restore the original docker entrypoint"""
        self.write_dockerfile(new_content=self.dockerfile_content)

    def params(self) -> dict:
        return {
            "mode": str,
            "rate": float,
            "dockerfile": str,
            "service_name": str,
        }

    def _validate_params(self) -> bool:
        pass

    def _transform_params(self) -> None:
        pass


class CorruptPacketTreatment(Treatment):
    def action(self):
        return "corrupt"

    def preconditions(self) -> bool:
        """Check if the service has tc installed"""
        service = self.config.get("service_name")
        command = [
            "tc",
            "-Version"
        ]
        client = docker.from_env()
        try:
            container = client.containers.get(container_id=service)
            status_code, _ = container.exec_run(cmd=command)
            logger.info(
                f"Probed container {service} for tc with result {status_code}"
            )
            if not status_code == 0:
                self.messages.append(
                    f"Container {service} does not have tc installed which is required for {self}. Please install "
                    "package iptables2 in the container"
                )
            return status_code == 0

        except ContainerNotFound:
            logger.error(f"Can't find container {service}")
            return False
        except DockerAPIError as e:
            logger.error(f"Docker API returned an error: {e.explanation}")
            return False

    def inject(self) -> None:
        service = self.config.get("service_name")
        interface = self.config.get("interface")
        duration = self.config.get("duration_seconds")
        percentage = self.config.get("corrupt_percentage")
        # optional param with default arg
        correlation = self.config.get("corrupt_correlation") or "0%"

        command = [
            "tc",
            "qdic",
            "add",
            "dev",
            interface,
            "root",
            "netem",
            "corrupt",
            percentage,
            correlation,
        ]

        client = docker.from_env()
        try:
            container = client.containers.get(container_id=service)
            container.exec_run(cmd=command)
            logger.info(
                f"Injected packet corruption into container {service}. Waiting for {duration}s."
            )
            time.sleep(duration)
        except ContainerNotFound:
            logger.error(f"Can't find container {service}")
        except DockerAPIError as e:
            logger.error(f"Docker API returned an error: {e.explanation}")

    def clean(self) -> None:
        interface = self.config.get("interface") or "eth0"
        service = self.config.get("service_name")
        command = ["tc", "qdisc", "del", "dev", interface, "root", "netem"]
        client = docker.from_env()
        try:
            container = client.containers.get(container_id=service)
            container.exec_run(cmd=command)
            logger.info(f"Cleaned delay treatment from container {service}")
        except (ContainerNotFound, DockerAPIError) as e:
            logger.error(
                f"Cannot clean delay treatment from container {service}: {e.explanation}"
            )
            logger.error(f"Container state for {service} might be polluted now")

    def params(self) -> dict:
        return {
            "service_name": str,
            "interface": str,
            "duration": str,
            "corrupt_percentage": str,
            "corrupt_correlation": Optional[str],
        }

    def _validate_params(self) -> bool:
        bools = []
        for key, value in self.params().items():
            # required params
            if (
                    key in {"service_name", "duration", "interface", "corrupt_percentage"}
                    and key not in self.config
            ):
                self.messages.append(f"Parameter {key} has to be supplied")
                bools.append(False)
            # supplied params have correct type
            if key in self.config and not isinstance(self.config[key], value):
                self.messages.append(f"Parameter {key} has to be of type {str(value)}")
        for key, value in self.config.items():
            if key == "duration":
                if not validate_time_string(value):
                    self.messages.append(
                        f"Parameter {key} has to match {time_string_format_regex}"
                    )
                    bools.append(False)
            if key in {"corrupt_percentage", "corrupt_correlation"}:
                format_regex = r"^[1-9][0-9]?\%$|^100\%$"
                if not bool(re.match(format_regex, value)):
                    self.messages.append(f"Parameter {key} has to match {format_regex}")
                    bools.append(False)
        return all(bools)

    def _transform_params(self) -> None:
        relative_time_string = self.config.get("duration")
        relative_time_seconds = time_string_to_seconds(relative_time_string)
        self.config["duration_seconds"] = relative_time_seconds

    def is_runtime(self) -> bool:
        return True


class MetricsExportIntervalTreatment(Treatment):
    """
    Modify the OTEL_METRICS_EXPORT interval for a given container
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_yaml = None
        # TODO: reuse the existing docker compose client
        """ self.compose_client = DockerClient(
            compose_files=[self.config.get("compose_file")]
        )
        self.docker_client = docker.from_env() """

    def action(self):
        return "otel_metrics_interval"

    def preconditions(self) -> bool:
        # TODO: check proper preconditions
        return True

    def inject(self) -> None:
        service = self.config.get("service_name")
        compose_file = self.config.get("compose_file")
        interval_ms = self.config.get("interval_ms")

        add_env_variable(
            compose_file_path=compose_file,
            service_name=service,
            variable_name="OTEL_METRIC_EXPORT_INTERVAL",
            variable_value=str(int(interval_ms)),
        )

    def clean(self) -> None:
        original_compose_file = self.config["original_yaml"]
        compose_file_path = self.config.get("compose_file")
        with open(compose_file_path, "w+") as file:
            file.write(yaml.safe_dump(original_compose_file, default_flow_style=False))

    def params(self) -> dict:
        return {
            "compose_file": str,
            "service_name": str,
            "interval": str,
        }

    def _validate_params(self) -> bool:
        for key, value in self.params().items():
            if key not in self.config:
                self.messages.append(f"Parameter {key} has to be supplied")
            if not isinstance(self.config[key], value):
                self.messages.append(f"Parameter {key} has to be of type {str(value)}")
        for key in self.config.items():
            if key == "percentage" and not 0 <= self.config[key] <= 100:
                self.messages.append(
                    f"Value for key {key} has to be in the range [0, 100] for {self.treatment_type}"
                )
            if key == "interval" and not validate_time_string(self.config[key]):
                self.messages.append(
                    f"Value for parameter {key} has to match {time_string_format_regex} for {self.treatment_type}"
                )
        return not self.messages

    def _transform_params(self) -> None:
        """Convert the provided time string into milliseconds"""
        interval_s = time_string_to_seconds(self.config["interval"])
        interval_ms = to_milliseconds(interval_s)
        self.config["interval_ms"] = interval_ms

        compose_file_path = self.config.get("compose_file")
        with open(compose_file_path, "r") as file:
            self.config["original_yaml"] = yaml.safe_load(file.read())

    def is_runtime(self) -> bool:
        return False
    
    def _validate_orchestrator(self) -> bool:
        return True


class KubernetesMetricsExportIntervalTreatment(Treatment):
    """
    Modify the OTEL_METRICS_EXPORT interval for a given container

    check rate(otelcol_exporter_sent_metric_points[30s]) to validate the change

    config:
        namespace: system-under-evaluation,
        label_selector: app.kubernetes.io/component,
        label: recommendationservice,
        interval: 1s,
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_env_value = None
        self.env_name = "OTEL_METRIC_EXPORT_INTERVAL"
        
    def action(self):
        return "kubernetes_otel_metrics_interval"

    def preconditions(self) -> bool:
        super().preconditions()
        return True

    def inject(self) -> None:
        self.namespace = self.config.get("namespace")
        self.label_selector = self.config.get("label_selector")
        self.label = self.config.get("label")
        self.interval_ms = self.config.get("interval_ms")

        assert isinstance(self.orchestrator, KubernetesOrchestrator)
        
        self.deployment = self.orchestrator.get_deployment(self.namespace, self.label_selector, self.label)
        
        deployment_environment_variables = self.orchestrator.get_deployment_env_parameters(
            deployment=self.deployment
        )
        
        # get self.env_name from the deployments environment variables
        for env_var in deployment_environment_variables:
            if env_var.name == self.env_name:
                self.init_env_value = env_var.value
                break 

        self.deployment = self.orchestrator.get_deployment(self.namespace, self.label_selector, self.label)
        result = self.orchestrator.set_deployment_env_parameter(
            deployment=self.deployment,
            environment_variable_name=self.env_name,
            environment_variable_value=str(int(self.interval_ms)),
        )
        
        logging.info(f"Environment variable '{self.env_name} set to '{self.interval_ms}'ms for the deployment '{self.deployment.metadata.name}'.")

        time.sleep(3)

        for x in range(0, 10):
            if self.orchestrator.is_deployment_ready(self.deployment):
                break
            logging.info(f"Waiting for deployment {self.deployment.metadata.name} to be ready")
            time.sleep(2)


    def clean(self) -> None:
        if self.init_env_value is None:
            return
        assert isinstance(self.orchestrator, KubernetesOrchestrator)
        # update the deployment as otherwise there will be an error because the deployment is outdated
        self.deployment = self.orchestrator.get_deployment(self.namespace, self.label_selector, self.label)
        result = self.orchestrator.set_deployment_env_parameter(
            deployment=self.deployment,
            environment_variable_name=self.env_name,
            environment_variable_value=self.init_env_value,
        )
        logging.info(f"Environment variable '{self.env_name} reset for deployment '{self.deployment.metadata.name}' to initial value.")

    def params(self) -> dict:
        return {
            "namespace": str,
            "label_selector": str,
            "label": str,
            "interval": str,
        }

    def _validate_params(self) -> bool:
        for key, value in self.params().items():
            if key not in self.config:
                self.messages.append(f"Parameter {key} has to be supplied")
            if not isinstance(self.config[key], value):
                self.messages.append(f"Parameter {key} has to be of type {str(value)}")
        for key in self.config.items():
            if key == "interval" and not validate_time_string(self.config[key]):
                self.messages.append(
                    f"Value for parameter {key} has to match {time_string_format_regex} for {self.treatment_type}"
                )
        return not self.messages

    def _transform_params(self) -> None:
        """Convert the provided time string into milliseconds"""
        interval_s = time_string_to_seconds(self.config["interval"])
        interval_ms = to_milliseconds(interval_s)
        self.config["interval_ms"] = interval_ms

    def is_runtime(self) -> bool:
        return False
    
    def _validate_orchestrator(self) -> bool:
        return super()._validate_orchestrator(["kubernetes"])


class ProbabilisticSamplingTreatment(Treatment):
    """
    Add a probabilistic sampling policy to the opentelemetry collector
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = docker.from_env()

    @property
    def action(self):
        return "probl"

    def is_runtime(self) -> bool:
        return False

    def preconditions(self) -> bool:
        # TODO: write tests to check if file exists
        return True

    def inject(self) -> None:
        path = self.config.get("otelcol_extras")
        # support only the base attributes for now
        sampling_percentage = self.config.get("percentage")
        seed = self.config.get("seed")
        updated_extras = {
            "processors": {
                "probabilistic_sampler": {
                    "hash_seed": seed,
                    "sampling_percentage": sampling_percentage
                }
            },
            "service": {
                "pipelines": {
                    "traces": {
                        "processors": ["probabilistic_sampler"],
                    }
                }
            },
        }
        with open(path, "w+") as file:
            existing_config = yaml.safe_load(file.read())
            if not existing_config:
                existing_config = {}
            existing_config.update(updated_extras)
            yaml.dump(existing_config, file, default_flow_style=False)

    def clean(self) -> None:
        original_extras = self.config.get("otelcol_extras_yaml")
        path = self.config.get("otelcol_extras")
        with open(path, "w+") as file:
            file.write(yaml.dump(original_extras, default_flow_style=False))

    def params(self) -> dict:
        return {
            "otelcol_extras": str,
            "percentage": int,
            "seed": int,
        }

    def _validate_params(self) -> bool:
        for key, value in self.params().items():
            if key == "otelcol_extras" and key not in self.config:
                self.messages.append(f"Key {key} is required for {self.treatment_type}")
            if key == "percentage" and key not in self.config:
                self.messages.append(f"Key {key} is required for {self.treatment_type}")
            if key == "seed" and key not in self.config:
                self.messages.append(f"Key {key} is required for {self.treatment_type}")
            if key in self.config and not isinstance(self.config[key], value):
                self.messages.append(f"Key {key} has to be of type {value} for {self.treatment_type}")
        for key in self.config.items():
            if key == "percentage" and not 0 <= self.config[key] <= 100:
                self.messages.append(
                    f"Value for key {key} has to be in the range [0, 100] for {self.treatment_type}"
                )
        return not self.messages

    def _transform_params(self) -> None:
        path = self.config.get("otelcol_extras")
        with open(path, "r") as file:
            contents = yaml.safe_load(file.read())
            if not contents:
                contents = {}
            self.config["otelcol_extras_yaml"] = contents



class KubernetesProbabilisticHeadSamplingTreatment(Treatment):
        
    """
        Treatment to change the global sampling rate for head-based trace sampling in the OpenTelemetry collector

        use "increase(otelcol_processor_probabilistic_sampler_count_traces_sampled[1m])" in prometheus to see the change between sampled:true and sampled:false when changing the sampling percentage

        otel documentation: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/probabilisticsamplerprocessor

        """

    def preconditions(self) -> bool:
        """Check that the config exists at the specified location and that Prometheus is running"""
        assert isinstance(self.orchestrator, KubernetesOrchestrator)
        configmap_name = "astronomy-shop-otelcol"
        
        try:
            configmap = self.orchestrator.kube_client.read_namespaced_config_map(name=configmap_name, namespace="system-under-evaluation")
        except Exception as e:
            raise OrchestratorException(
                message=f"Error while reading ConfigMap {configmap_name} in namespace system-under-evaluation: {e.body}",
                explanation=str(e),
            )

        self.deployment = self.orchestrator.get_deployment("system-under-evaluation", "app.kubernetes.io/name", "otelcol")

        if not configmap:
            self.messages.append(f"ConfigMap {configmap_name} not found in namespace system-under-evaluation")
            return False
        
        if self.deployment is None:
            self.messages.append(f"Deployment otelcol not found in namespace system-under-evaluation")
            return False
        

        return True

    def inject(self) -> None:
        assert self.config.get("sampling_percentage")
        assert self.config.get("hash_seed")
        assert isinstance(self.orchestrator, KubernetesOrchestrator)
        
        self.deployment = self.orchestrator.get_deployment("system-under-evaluation", "app.kubernetes.io/name", "otelcol")
        
        self.initial_sampling_percentage, self.initial_hash_seed = self.orchestrator.get_otel_collector_probabilistic_sampling_values()
        self.orchestrator.set_otel_collector_probabilistic_sampling_values(sampling_percentage=self.config.get("sampling_percentage"), hash_seed=self.config.get("hash_seed"))
        logging.info(f"Set otel collectors probabilistic sampling rate {self.initial_sampling_percentage} -> {self.config.get('sampling_percentage')} and hash seed {self.initial_hash_seed} -> {self.config.get('hash_seed')}")


         # TODO: it seams as there might be a way to reload config maps without restarting the pods in some cases. This should be investigated (https://kubernetes.io/docs/concepts/configuration/configmap/#mounted-configmaps-are-updated-automatically)
        self.orchestrator.restart_pods_of_deployment(self.deployment)


    def clean(self) -> None:
        assert self.initial_sampling_percentage
        assert self.initial_hash_seed
        assert isinstance(self.orchestrator, KubernetesOrchestrator)

        self.orchestrator.set_otel_collector_probabilistic_sampling_values(sampling_percentage=self.initial_sampling_percentage, hash_seed= self.initial_hash_seed)
        logging.info(f"Reset otel collectors probabilistic sampling rate  {self.config.get('sampling_percentage')} -> {self.initial_sampling_percentage} and hash seed to {self.config.get('hash_seed')} -> {self.initial_hash_seed}")

         # TODO: it seams as there might be a way to reload config maps without restarting the pods in some cases. This should be investigated (https://kubernetes.io/docs/concepts/configuration/configmap/#mounted-configmaps-are-updated-automatically)
        self.orchestrator.restart_pods_of_deployment(self.deployment)

        return
        


    def params(self) -> dict:
        return {
            "sampling_percentage": float,
            "hash_seed": int,
        }

    def _validate_params(self) -> bool:
        for key, val in self.params().items():
            if key in self.config and not isinstance(self.config[key], val):
                self.messages.append(
                    f"Parameter {key} has to be of type {val} for {self.treatment_type}"
                )
        for key, value in self.config.items():
            if key == "sampling_percentage" and not (0 <= self.config[key] <= 100):
                self.messages.append(
                    f"Parameter {key} has to be between 0 and 100 for {self.treatment_type}"
                )
            if key == "sampling_percentage" and self.config[key] > 20:
               logging.warning(f"Sampling percentage is set to {self.config[key]}. High sampling rates can lead to high costs and performance issues and crashes.")
        return not self.messages

    def _transform_params(self) -> None:
       pass

    def _validate_orchestrator(self) -> bool:
        return super()._validate_orchestrator(["kubernetes"])
    
    @property
    def action(self):
        return "kube_probl"

    def is_runtime(self) -> bool:
        return False


class TailSamplingTreatment(Treatment):
    """
    Add a tracing tail sampling policy to the OpenTelemetry collector
    As of 2023-03-24, the otelcol is not able to do a hot reload,
    which means we need to restart the container via docker after
    changing the config.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = docker.from_env()

    @property
    def action(self):
        return "tail"

    def is_runtime(self) -> bool:
        return True

    def preconditions(self) -> bool:
        """
        Check that the collector exists and is running

        Not implemented yet
        """
        return True

    def inject(self) -> None:
        """Write the policy to the otelcol-extras file"""
        path = self.config.get("otelcol_extras")
        # get existing configuration
        # inject the policy
        policy_type = self.config.get("type")
        policy_name = self.config.get("policy_name")
        policy_params = self.config.get("policy_params")
        updated_extras = {
            "processors": {
                "tail_sampling": {
                    "policies": [
                        {
                            "name": policy_name,
                            "type": policy_type,
                            policy_type: policy_params,
                        }
                    ]
                }
            },
            "service": {
                "pipelines": {
                    "traces": {
                        "processors": ["tail_sampling"],
                    }
                }
            },
        }
        with open(path, "w+") as file:
            file.write(yaml.dump(updated_extras, default_flow_style=False))

        # restart the collector and block until it has restarted
        container = self.client.containers.get("otel-col")
        container.stop()
        container.wait()
        container.start()

        duration = self.config.get("duration", "0m")
        if duration:
            seconds = time_string_to_seconds(duration)
            time.sleep(seconds)

    def clean(self) -> None:
        original_extras = self.config.get("otelcol_extras_yaml")
        path = self.config.get("otelcol_extras")
        with open(path, "w+") as file:
            file.write(yaml.dump(original_extras, default_flow_style=False))

    def params(self) -> dict:
        return {
            "otelcol_extras": str,
            "policy_name": str,
            "decision_wait": str,
            "num_traces": int,
            "expected_new_traces": int,
            "type": str,
            "policy_params": dict,
        }

    def _validate_params(self) -> bool:
        # TODO: implement the method
        return True

    def _transform_params(self) -> None:
        path = self.config.get("otelcol_extras")
        with open(path, "r") as file:
            contents = yaml.safe_load(file.read())
            if not contents:
                contents = {}
            self.config["otelcol_extras_yaml"] = contents


class PauseTreatment(Treatment):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = docker.from_env()

    def is_runtime(self) -> bool:
        return True

    @property
    def action(self):
        return "pause"

    def params(self) -> dict:
        return {
            "service_name": str,
            "duration": str,
        }

    def _validate_params(self) -> bool:
        for key, value in self.params().items():
            # required key
            if key == "service_name" and key not in self.config:
                self.messages.append(f"Key {key} is required for {self.treatment_type}")
            # required key
            if key == "duration" and key not in self.config:
                self.messages.append(f"Key {key} is required for {self.treatment_type}")
            # key has correct type
            if key in self.config and not isinstance(self.config[key], value):
                self.messages.append(
                    f"Key {key} has to be of type {value} for {self.treatment_type}"
                )
        for key in self.config.items():
            # if an interval is supplied, a timeout needs to be supplied as well
            if key == "duration" and not validate_time_string(self.config[key]):
                self.messages.append(
                    f"Value for key {key} has to match {time_string_format_regex} for {self.treatment_type}"
                )
        return not self.messages

    def _transform_params(self) -> None:
        if "duration" in self.config:
            relative_time_string = self.config.get("duration")
            relative_time_seconds = time_string_to_seconds(relative_time_string)
            self.config |= {"duration_seconds": relative_time_seconds}

    def preconditions(self) -> bool:
        """Check if the docker daemon is running and the container is running"""
        service = self.config.get("service_name")
        try:
            container = self.client.containers.get(container_id=service)
            container_state = container.status
            logger.info(
                f"Probed container {service} for state running with result {container_state}"
            )
            if not container_state == "running":
                self.messages.append(
                    f"Container {service} is not running which is required for {self.treatment_type}."
                )
            return container_state == "running"
        except ContainerNotFound:
            self.messages.append(
                f"Can't find container {service} for {self.treatment_type}"
            )
            return False
        except DockerAPIError as e:
            self.messages.append(
                f"Can't talk to Docker API: {e.explanation} in {self.treatment_type}"
            )
            return False

    def inject(self):
        duration_seconds = self.config.get("duration_seconds")
        service = self.config.get("service_name")

        try:
            container = self.client.containers.get(container_id=service)
            container.pause()
        except ContainerNotFound:
            logger.error(f"Can't find container {service}")
        except DockerAPIError as e:
            logger.error(f"Docker API returned an error: {e.explanation}")
        logger.info(
            f"Injected pause into container {service}. Waiting for {duration_seconds}s"
        )
        time.sleep(duration_seconds)

    def clean(self):
        service = self.config.get("service_name")
        try:
            container = self.client.containers.get(container_id=service)
            container.unpause()
            logger.debug(f"Cleaned pause from container {service}.")
            self.client.close()
        except (ContainerNotFound, DockerAPIError) as e:
            logger.error(
                f"Cannot clean pause treatment from container {service}: {e.explanation}"
            )
            logger.error(f"Container state for {service} might be polluted now")


class KubernetesNetworkDelayTreatment(Treatment):
    """Inject network delay into a service"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.client = docker.from_env()
        self.client = self.orchestrator

    action = "delay"

    def is_runtime(self) -> bool:
        return True

    def _validate_params(self) -> bool:
        for key, val in self.params().items():
            # required params
            if (
                    key in {"namespace", "label_selector", "label", "interface", "duration", "delay_time"}
                    and key not in self.config
            ):
                self.messages.append(
                    f"Parameter {key} has to be supplied for {self.treatment_type}"
                )
            # supplied params have correct type
            if key in self.config and not isinstance(self.config[key], val):
                self.messages.append(
                    f"Parameter {key} has to be of type {val.__class__.__name__} for {self.treatment_type}"
                )
        for key, value in self.config.items():
            if key in {"duration", "delay_time", "delay_jitter"}:
                if not validate_time_string(value):
                    self.messages.append(
                        f"Value for parameter {key} has to match {time_string_format_regex} for {self.treatment_type}"
                    )
            if key == "delay_correlation":
                format_regex = r"\d+\%"
                if not bool(re.match(format_regex, value)):
                    self.messages.append(
                        f"Value for parameter {key} has to match {format_regex} for {self.treatment_type}"
                    )
            if key == "distribution":
                distribution_set = {"uniform", "pareto", "normal", "paretonormal"}
                if key not in distribution_set:
                    self.messages.append(
                        f"Value for parameter {key} has to be one of {distribution_set} for {self.treatment_type}"
                    )
        return not self.messages

    def _transform_params(self) -> None:
        # correctly formatted params can be passed to tc directly as it can handle values + units
        # we need only transform the duration into seconds for the time.sleep call
        relative_time_string = self.config.get("duration")
        relative_time_seconds = time_string_to_seconds(relative_time_string)
        self.config["duration_seconds"] = relative_time_seconds

    def params(self) -> dict:
        return {
            "interface": str,
            "duration": str,
            "delay_time": str,
            "delay_jitter": Optional[str],
            "delay_correlation": Optional[str],
            "delay_distribution": Optional[str],
        }

    def preconditions(self) -> bool:
        super().preconditions()
        """Check if the service has tc installed"""
        #service = self.config.get("service_name")
        namespace = self.config.get("namespace")
        label_selector = self.config.get("label_selector")
        label = self.config.get("label")
        command = ["tc", "-Version"]
        try:
            assert namespace
            assert label_selector
            assert label
            assert isinstance(self.orchestrator, KubernetesOrchestrator)
            status_code, _ = self.orchestrator.execute_console_command_on_all_matching_pods(
                namespace=namespace,
                label_selector=label_selector,
                label=label,
                command=command
            )
            logger.info(f"Probed pods in {namespace} with {label_selector}={label} for tc with result {status_code}")
            if status_code > 1 or status_code < 0:
                install_command = ["apt", "update", "&&", "apt", "install", "iproute2", "-y"]
                status_code_2, _ = self.orchestrator.execute_console_command_on_all_matching_pods(
                    namespace=namespace,
                    label_selector=label_selector,
                    label=label,
                    command=install_command
                )
                if status_code_2 > 1 or status_code_2 < 0:
                    self.messages.append(
                        f"Not all pods in {namespace} with {label_selector}={label} does not have tc installed which is required for {self.treatment_type}. Please install "
                        "package iproute2 in the container"
                    )
                    return False
                return False
            return True
        except OrchestratorResourceNotFoundException as e:
            self.messages.append(e.message)
            return False
        except OrchestratorException as e:
            self.messages.append(e.message)
            return False
        except Exception as e:
            self.messages.append(str(e))
            print(traceback.format_exc())
            return False

    def inject(self) -> None:
        super().inject()
        # required params
        namespace = self.config.get("namespace")
        label_selector = self.config.get("label_selector")
        label = self.config.get("label")
        interface = self.config.get("interface")
        delay_time = self.config.get("delay_time")
        duration = self.config.get("duration_seconds")
        # optional params: use default values so we dont need to construct multiple commands
        jitter = self.config.get("delay_jitter", "0ms")
        correlation = self.config.get("delay_correlation", "0%")
        command = [
            "tc",
            "qdisc",
            "add",
            "dev",
            interface,
            "root",
            "netem",
            "delay",
            delay_time,
            jitter,
            correlation,
        ]
        try:
            assert namespace
            assert label_selector
            assert label
            assert duration
            assert isinstance(self.orchestrator, KubernetesOrchestrator)
            status_code, _ = self.orchestrator.execute_console_command_on_all_matching_pods(
                namespace=namespace,
                label_selector=label_selector,
                label=label,
                command=command
            )
            if status_code > 1:
                logger.error(
                    f"Failed to inject delay into pods in {namespace} with {label_selector}={label}. Return code: {status_code}"
                )
                return
            logger.info(
                f"Injected delay into pods in {namespace} with {label_selector}={label}. Waiting for {duration}s."
            )
            time.sleep(duration)
        except ContainerNotFound:
            logger.error(f"Can't find container ")
        except DockerAPIError as e:
            logger.error(f"Docker API returned an error: {e.explanation}")

    def clean(self) -> None:
        super().clean()
        interface = self.config.get("interface") or "eth0"
        namespace = self.config.get("namespace")
        label_selector = self.config.get("label_selector")
        label = self.config.get("label")
        command = ["tc", "qdisc", "del", "dev", interface, "root", "netem"]
        try:
            assert namespace
            assert label_selector
            assert label
            assert isinstance(self.orchestrator, KubernetesOrchestrator)
            status_code, _ = self.orchestrator.execute_console_command_on_all_matching_pods(
                namespace=namespace,
                label_selector=label_selector,
                label=label,
                command=command
            )
            
            logger.info(f"Cleaned delay treatment from pods in {namespace} with {label_selector}={label}")
            #self.client.close()
        except (ContainerNotFound, DockerAPIError) as e:
            logger.error(
                f"Cannot clean delay treatment from pods in {namespace} with {label_selector}={label}: {e.explanation}"
            )
            logger.error(f"State for pods in {namespace} with {label_selector}={label} might be polluted now")
            
    def _validate_orchestrator(self) -> bool:
        if self.orchestrator.get_orchestrator_type() != "kubernetes":
            self.messages.append(f"{self.name} treatment is only supported for Kubernetes orchestrators")
            return False
        return True

class PacketLossTreatment(Treatment):
    """Inject packet loss into a service"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = docker.from_env()

    action = "loss"

    def is_runtime(self) -> bool:
        return True

    def params(self) -> dict:
        return {
            "service_name": str,
            "duration": str,
            "interface": str,
            "loss_percentage": str,
        }

    def _validate_params(self) -> bool:
        for key, value in self.params().items():
            if key not in self.config:
                self.messages.append(
                    f"Parameter {key} has to be supplied for {self.treatment_type}"
                )
            if not isinstance(self.config[key], value):
                self.messages.append(
                    f"Parameter {key} has to be of type {value.__class__.__name__} for {self.treatment_type}"
                )
        for key in self.config:
            if key == "duration":
                if not validate_time_string(self.config[key]):
                    self.messages.append(
                        f"Value for parameter {key} has to match {time_string_format_regex} for {self.treatment_type}"
                    )
            if key == "loss_percentage":
                format_regex = r"^[1-9][0-9]?\%$|^100\%$"
                if not bool(re.match(format_regex, self.config[key])):
                    self.messages.append(
                        f"Value for parameter {key} has to match {format_regex} for {self.treatment_type}"
                    )
        return not self.messages

    def _transform_params(self) -> None:
        if "duration" in self.config:
            relative_time_string = self.config.get("duration")
            relative_time_seconds = time_string_to_seconds(relative_time_string)
            self.config |= {"duration_string": str(relative_time_seconds)}
            self.config |= {"duration_integer": relative_time_seconds}

    def preconditions(self) -> bool:
        """Check if the service has tc installed"""
        service = self.config.get("service_name")
        command = ["tc", "-Version"]
        try:
            container = self.client.containers.get(container_id=service)
            status_code, _ = container.exec_run(cmd=command)
            logger.info(f"Probed container {service} for tc with result {status_code}")
            if not status_code == 0:
                self.messages.append(
                    f"Container {service} does not have tc installed which is required for {self}. Please install "
                    "package iptables2 in the container"
                )
            return status_code == 0
        except ContainerNotFound:
            logger.error(f"Can't find container {service}")
            return False
        except DockerAPIError as e:
            logger.error(f"Docker API returned an error: {e.explanation}")
            return False

    def inject(self):
        duration_seconds = self.config.get("duration_integer")
        service = self.config.get("service_name")
        percentage = self.config.get("loss_percentage")
        interface = self.config.get("interface")
        command = [
            "tc",
            "qdisc",
            "add",
            "dev",
            interface,
            "root",
            "netem",
            "loss",
            "random",
            percentage,
        ]
        try:
            container = self.client.containers.get(container_id=service)
            status_code, _ = container.exec_run(cmd=command)
            logger.debug(
                f"Injected packet loss into container {service} with status code {status_code}. Waiting for {duration_seconds}s"
            )
            time.sleep(duration_seconds)
        except ContainerNotFound:
            logger.error(f"Can't find container {service}")
        except DockerAPIError as e:
            logger.error(f"Docker API returned an error: {e.explanation}")

    def clean(self):
        interface = self.config.get("interface") or "eth0"
        service = self.config.get("service_name")
        command = [
            "tc",
            "qdisc",
            "del",
            "dev",
            interface,
            "root",
            "netem",
        ]
        try:
            container = self.client.containers.get(container_id=service)
            container.exec_run(cmd=command)
            logger.info(f"Cleaned packet loss treatment in container {service}.")
            self.client.close()
        except (DockerAPIError, ContainerNotFound) as e:
            logger.error(
                f"Cannot clean packet loss treatment from container {service}: {e.explanation}"
            )
            logger.error(f"Container state for {service} might be polluted now")



class KubernetesNetworkPacketLossTreatment(Treatment):
    """
    Inject network errors into a service to induce packet loss
    
    To high values of loss_percentage can provoke a cascading effect and lead to nearly 100% packet loss
    To low values of loss_percentage can lead to no effect at all or a small increas in latency
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.client = docker.from_env()
        self.client = self.orchestrator

    action = "kubernetes_loss"

    def is_runtime(self) -> bool:
        return True

    def _validate_params(self) -> bool:
        for key, val in self.params().items():
            # required params
            if (
                    key in {"namespace", "label_selector", "label", "interface", "duration", "loss_percentage"}
                    and key not in self.config
            ):
                self.messages.append(
                    f"Parameter {key} has to be supplied for {self.treatment_type}"
                )
            # supplied params have correct type
            if key in self.config and not isinstance(self.config[key], val):
                self.messages.append(
                    f"Parameter {key} has to be of type {val.__class__.__name__} for {self.treatment_type}"
                )
        for key, value in self.config.items():
            if key in {"duration"}:
                if not validate_time_string(value):
                    self.messages.append(
                        f"Value for parameter {key} has to match {time_string_format_regex} for {self.treatment_type}"
                    )
        return not self.messages

    def _transform_params(self) -> None:
        # correctly formatted params can be passed to tc directly as it can handle values + units
        # we need only transform the duration into seconds for the time.sleep call
        relative_time_string = self.config.get("duration")
        relative_time_seconds = time_string_to_seconds(relative_time_string)
        self.config["duration_seconds"] = relative_time_seconds

    def params(self) -> dict:
        return {
            "interface": str,
            "duration": str,
            "loss_percentage": float,
        }

    def preconditions(self) -> bool:
        super().preconditions()
        """Check if the service has tc installed"""
        #service = self.config.get("service_name")
        namespace = self.config.get("namespace")
        label_selector = self.config.get("label_selector")
        label = self.config.get("label")
        command = ["tc", "-Version"]
        try:
            assert namespace
            assert label_selector
            assert label
            assert isinstance(self.orchestrator, KubernetesOrchestrator)
            status_code, _ = self.orchestrator.execute_console_command_on_all_matching_pods(
                namespace=namespace,
                label_selector=label_selector,
                label=label,
                command=command
            )
            logger.info(f"Probed pods in {namespace} with {label_selector}={label} for tc with result {status_code}")
            if status_code > 1 or status_code < 0:
                install_command = ["apt", "update", "&&", "apt", "install", "iproute2", "-y"]
                status_code_2, _ = self.orchestrator.execute_console_command_on_all_matching_pods(
                    namespace=namespace,
                    label_selector=label_selector,
                    label=label,
                    command=install_command
                )
                if status_code_2 > 1 or status_code_2 < 0:
                    self.messages.append(
                        f"Not all pods in {namespace} with {label_selector}={label} does not have tc installed which is required for {self.treatment_type}. Please install "
                        "package iproute2 in the container"
                    )
                    return False
                return False
            return True
        except OrchestratorResourceNotFoundException as e:
            self.messages.append(e.message)
            return False
        except OrchestratorException as e:
            self.messages.append(e.message)
            return False
        except Exception as e:
            self.messages.append(str(e))
            print(traceback.format_exc())
            return False

    def inject(self) -> None:
        super().inject()
        # required params
        namespace = self.config.get("namespace")
        label_selector = self.config.get("label_selector")
        label = self.config.get("label")
        interface = self.config.get("interface")
        duration = self.config.get("duration_seconds")
        loss_percentage = self.config.get("loss_percentage")
        command = [
            "tc",
            "qdisc",
            "add",
            "dev",
            interface,
            "root",
            "netem",
            "loss",
            "random",
            str(loss_percentage),
        ]
        try:
            assert namespace
            assert label_selector
            assert label
            assert duration
            assert isinstance(self.orchestrator, KubernetesOrchestrator)
            status_code, _ = self.orchestrator.execute_console_command_on_all_matching_pods(
                namespace=namespace,
                label_selector=label_selector,
                label=label,
                command=command
            )
            if status_code > 1:
                logger.error(
                    f"Failed to inject packet loss into pods in {namespace} with {label_selector}={label}. Return code: {status_code}"
                )
                return
            logger.info(
                f"Injected packet loss into pods in {namespace} with {label_selector}={label}. Waiting for {duration}s."
            )
            time.sleep(duration)
        except ContainerNotFound:
            logger.error(f"Can't find container ")
        except DockerAPIError as e:
            logger.error(f"Docker API returned an error: {e.explanation}")

    def clean(self) -> None:
        super().clean()
        interface = self.config.get("interface") or "eth0"
        namespace = self.config.get("namespace")
        label_selector = self.config.get("label_selector")
        label = self.config.get("label")
        command = ["tc", "qdisc", "del", "dev", interface, "root", "netem"]
        try:
            assert namespace
            assert label_selector
            assert label
            assert isinstance(self.orchestrator, KubernetesOrchestrator)
            status_code, _ = self.orchestrator.execute_console_command_on_all_matching_pods(
                namespace=namespace,
                label_selector=label_selector,
                label=label,
                command=command
            )

            if status_code > 1:
                logger.error(f"Failed to clean packet loss from pods in {namespace} with {label_selector}={label}. Return code: {status_code}")
                return
            
            logger.info(f"Cleaned packet loss treatment from pods in {namespace} with {label_selector}={label}")
            #self.client.close()
        except Exception as e:
            logger.error(f"Cannot clean packet loss treatment from pods in {namespace} with {label_selector}={label}: {e}")
            logger.error(f"State for pods in {namespace} with {label_selector}={label} might be polluted now")
            
    def _validate_orchestrator(self) -> bool:
        if self.orchestrator.get_orchestrator_type() != "kubernetes":
            self.messages.append(f"{self.name} treatment is only supported for Kubernetes orchestrators")
            return False
        return True
    

class DeploymentScaleTreatment(Treatment):
    """
    Will scale a deployment to 0 replicas and back to the original number of replicas.
    """
    
    action = "scale_deployment"


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.replicas_before = 0
        self.deployment = None



    def preconditions(self) -> bool:
        """Check if the deployment exists"""
        super().preconditions()
        return True
        
        

    def inject(self) -> None:
        super().inject()
        namespace = self.config.get("namespace")
        label_selector = self.config.get("label_selector")
        label = self.config.get("label")
        scale_to = self.config.get("scale_to")
        assert scale_to is not None and scale_to >= 0 
        try:
            assert isinstance(self.orchestrator, KubernetesOrchestrator)
            self.deployment = KubernetesOrchestrator.get_deployment(self.orchestrator, namespace, label_selector, label)
            if self.deployment is None:
                self.messages.append(f"Deployment with {label_selector}={label} not found in namespace {namespace}")
                return
        except OrchestratorException as e:
            self.messages.append(e.message)
            return 
        
        assert self.deployment.spec
        assert self.deployment.metadata
        assert self.deployment.metadata.name

        self.replicas_before = self.deployment.spec.replicas
        response = KubernetesOrchestrator.scale_deployment(self.orchestrator, self.deployment, scale_to)
        if response is None:
            self.messages.append(f"Failed to scale deployment {self.deployment.metadata.name} to {scale_to}")
            return
        # TODO: Wait until scaling is done
        logging.info(f"Deployment {self.deployment.metadata.name} scaled to {scale_to}")

    def clean(self) -> None:
        """
        Scale the deployment back to the original number of replicas.

        We have to fetch the deployment again as otherwise there will be an error form the kubernetes API because the deployment object is not up to date.
        """
        super().clean()
        namespace = self.config.get("namespace")
        label_selector = self.config.get("label_selector")
        label = self.config.get("label")
        try:
            assert isinstance(self.orchestrator, KubernetesOrchestrator)
            self.deployment = KubernetesOrchestrator.get_deployment(self.orchestrator, namespace, label_selector, label)
            if self.deployment is None:
                self.messages.append(f"Deployment with {label_selector}={label} not found in namespace {namespace}")
                return
        except OrchestratorException as e:
            self.messages.append(e.message)
            return 
        assert self.deployment.metadata
        assert self.deployment.metadata.name
        response = KubernetesOrchestrator.scale_deployment(self.orchestrator, self.deployment, self.replicas_before)
        if response is None:
            self.messages.append(f"Failed to scale deployment {self.deployment.metadata.name} to {self.replicas_before}")
            return
        logging.info(f"Deployment {self.deployment.metadata.name} scaled to {self.replicas_before}")

    def params(self) -> dict:
        return {
            "namespace": str,
            "label_selector": str,
            "label": str,
            "scale_to": int,
        }

    def _validate_params(self) -> bool:
        """ 
        Check if all required parameters are supplied and have the correct type.        
        """

        for key, value in self.params().items():
            if key not in self.config:
                self.messages.append(f"Parameter {key} has to be supplied for {self.treatment_type}")
            if not isinstance(self.config[key], value):
                self.messages.append(f"Parameter {key} has to be of type {value} for {self.treatment_type}")

        return not self.messages
        

    def _transform_params(self) -> None:
        pass

    def is_runtime(self) -> bool:
        return False

    def _validate_orchestrator(self) -> bool:
        return super()._validate_orchestrator(["kubernetes"])


class KillTreatment(Treatment):
    """
    Kill a Docker container.
    """

    action = "kill"

    def preconditions(self) -> bool:
        """Check if the docker daemon is running and the container is running"""
        service = self.config.get("service_name")
        client = docker.from_env()
        try:
            container = client.containers.get(container_id=service)
            container_state = container.status
            logger.debug(
                f"Probed container {service} for state running with result {container_state}"
            )
            if not container_state == "running":
                self.messages.append(
                    f"Container {service} is not running which is required for {self.treatment_type}."
                )
            return container_state == "running"
        except ContainerNotFound:
            logger.error(f"Can't find container {service}")
            return False
        except DockerAPIError as e:
            logger.error(f"Docker API returned an error: {e.explanation}")
            return False

    def inject(self) -> None:
        service_name = self.config.get("service_name")
        duration_seconds = self.config.get("duration_seconds")
        client = docker.from_env()
        try:
            container = client.containers.get(container_id=service_name)
            container.kill()
            logger.debug(
                f"Killed container {service_name}. Sleeping for {duration_seconds}"
            )
            time.sleep(duration_seconds)
        except ContainerNotFound:
            logger.error(f"Can't find container {service_name}")
        except DockerAPIError as e:
            logger.error(f"Docker API returned an error: {e.explanation}")

    def clean(self) -> None:
        service_name = self.config.get("service_name")
        client = docker.from_env()
        try:
            container = client.containers.get(container_id=service_name)
            container.restart()
            logger.debug(f"Restarted container {service_name}")
        except ContainerNotFound:
            logger.error(f"Can't find container {service_name}")
        except DockerAPIError as e:
            logger.error(f"Docker API returned an error: {e.explanation}")

    def params(self) -> dict:
        return {
            "service_name": str,
            "duration": str,
        }

    def _validate_params(self) -> bool:
        for key, value in self.params().items():
            if key == "service_name" and key not in self.config:
                self.messages.append(
                    f"Parameter {key} has to be supplied for {self.treatment_type}"
                )
            if key == "service_name" and not isinstance(self.config[key], value):
                self.messages.append(
                    f"Parameter {key} has to be of type {value} for {self.treatment_type}"
                )
        for key, value in self.config.items():
            if key == "duration" and not validate_time_string(value):
                self.messages.append(
                    f"Parameter {key} has to match {time_string_format_regex} for {self.treatment_type}"
                )
        return not self.messages

    def _transform_params(self):
        relative_time_string = self.config.get("duration", "0s")
        relative_time_seconds = time_string_to_seconds(relative_time_string)
        self.config |= {"duration_seconds": relative_time_seconds}

    def is_runtime(self) -> bool:
        return True


class KubernetesKillTreatment(Treatment):
    """
    Kill a Kubernetes Pod.
    """

    action = "kubernetes_kill"

    def preconditions(self) -> bool:
        """Check if the kubernetes pod is running"""
        super().preconditions()
        namespace = self.config.get("namespace")
        label_selector = self.config.get("label_selector")
        label = self.config.get("label")
        amount_to_kill = self.config.get("amount_to_kill")
        try:
            assert namespace
            assert label_selector
            assert label
            assert amount_to_kill
            assert isinstance(self.orchestrator, KubernetesOrchestrator)
            self.pods = KubernetesOrchestrator.get_pods(self.orchestrator, namespace, label_selector, label)
            if self.pods is None:
                self.messages.append(f"Pod with {label_selector}={label} not found in namespace {namespace}")
                return False
            
            if len(self.pods) < amount_to_kill:
                self.messages.append(f"Amount to kill is higher than the amount of pods matching the label selector. Amount to kill: {amount_to_kill}, amount of pods found for label selector: {len(self.pods)}")
                return False
                
            for pod in self.pods:
                if pod.status and pod.status.phase != "Running":
                    self.messages.append(f"At least one Pod ({pod.metadata.name}) is not running ({pod.status.phase})")
                    return False
        
        except OrchestratorException as e:
            self.messages.append(e.message)
            return False
        
        return True

    def inject(self) -> None:
        assert self.pods
        assert self.orchestrator
        assert isinstance(self.orchestrator, KubernetesOrchestrator)
        if not self.pods:
            logger.error("No pods found to kill")
            return
        
        amount_to_kill = self.config.get("amount_to_kill")
        pods_to_kill = self.pods[:amount_to_kill]
        for pod in pods_to_kill:
            KubernetesOrchestrator.kill_pod(self.orchestrator, pod)
            
        # TODO: scale down deployment of the pods?
        
        logger.debug(f"Killed {amount_to_kill} pods.")

    def clean(self) -> None:
        # TODO: Wait untill als pods are running again?
        super().clean()

    def params(self) -> dict:
        return {
            "namespace": str,
            "label_selector": str,
            "label": str,
            "amount_to_kill": int,
        }

    def _validate_params(self) -> bool:
        for key, value in self.params().items():
            if key == "namespace" and key not in self.config:
                self.messages.append(
                    f"Parameter {key} has to be supplied for {self.treatment_type}"
                )
            if key == "label_selector" and key not in self.config:
                self.messages.append(
                    f"Parameter {key} has to be supplied for {self.treatment_type}"
                )
            if key == "label" and key not in self.config:
                self.messages.append(
                    f"Parameter {key} has to be supplied for {self.treatment_type}"
                )
            if key == "amount_to_kill" and key not in self.config:
                self.messages.append(
                    f"Parameter {key} has to be supplied for {self.treatment_type}"
                )
        return not self.messages
    
    def _transform_params(self) -> None:
        return super()._transform_params()

    def is_runtime(self) -> bool:
        return True
    
    def _validate_orchestrator(self) -> bool:
        return super()._validate_orchestrator(["kubernetes"])


class PacketReorderTreatment(Treatment):
    """
    Reorder packets. This can be used to simulate different cache locality effects.
    This is an example of a non-destructive treatment incompatible with the chaos engineering approach.
    Rather, this could be used to improve upon the system.
    Confer https://www.usenix.org/conference/nsdi22/presentation/ghasemirahni
    """

    # TODO: implement packet reordering


class SlotTreatment(Treatment):
    """Defer the delivery of accumulated packets to within a slot.
    Each slot is configurable with a minimum delay, number of bytes delivered per slot and
    number of delivered packets per slot.

    This treatment can be used to simulate bursty traffic, i.e. network congestion effects.
    """

    # TODO: implement slot treatment


class PrometheusIntervalTreatment(Treatment):
    """
    Treatment to change the global scrape interval of a Prometheus instance.

    Prometheus is able to reload its configuration at runtime on a post request to  /-/reload
    (cf. https://prometheus.io/docs/prometheus/latest/configuration/configuration/),
    therefore we only need as a parameter the path to the prometheus configuration file
    and the new scrape interval. The treatment memorizes the old scrape_interval for the cleanup method and
    writes the new scrape interval to the config.


    """

    def preconditions(self) -> bool:
        """Check that the config exists at the specified location and that Prometheus is running"""
        return True

    def inject(self) -> None:
        prometheus_yaml = self.config.get("prometheus_yaml")
        prometheus_yaml["global"]["scrape_interval"] = self.config.get("interval")
        prometheus_path = self.config.get("prometheus_config")
        with open(prometheus_path, "w+") as fp:
            yaml.dump(prometheus_yaml, fp, default_flow_style=False)
        # tell prometheus to reload the config
        # TODO: infer the url from docker compose file or have it be user provided
        requests.post("http://localhost:9090/-/reload")

    def clean(self) -> None:
        prometheus_yaml = self.config.get("prometheus_yaml")
        prometheus_yaml["global"]["scrape_interval"] = self.config.get(
            "original_interval"
        )
        prometheus_path = self.config.get("prometheus_config")
        with open(prometheus_path, "w+") as fp:
            yaml.dump(prometheus_yaml, fp, default_flow_style=False)
        # tell prometheus to reload the config
        requests.post("http://localhost:9090/-/reload")

    def params(self) -> dict:
        return {
            "prometheus_config": str,
            "interval": str,
        }

    def _validate_params(self) -> bool:
        for key, val in self.params().items():
            if key in {"prometheus_config", "interval"} and key not in self.config:
                self.messages.append(
                    f"Parameter {key} has to be supplied for {self.treatment_type}"
                )
            if key in self.config and not isinstance(self.config[key], val):
                self.messages.append(
                    f"Parameter {key} has to be of type {val} for {self.treatment_type}"
                )
        for key, value in self.config.items():
            prometheus_regex = (
                r"((([0-9]+)y)?(([0-9]+)w)?(([0-9]+)d)?(([0-9]+)h)?(([0-9]+)m)?((["
                r"0-9]+)s)?(([0-9]+)ms)?|0)"
            )
            if key == "interval" and not bool(re.match(prometheus_regex, value)):
                self.messages.append(
                    f"Parameter {key} has to match {prometheus_regex} for {self.treatment_type}"
                )
            if key == "prometheus_config":
                if not os.path.isfile(value):
                    self.messages.append(f"Prometheus config at {value} does not exist")
        return not self.messages

    def _transform_params(self) -> None:
        """
        Memorize the original prometheus setting and provide a loaded version of the prometheus yaml config
        """
        # since _transform_params always get called after validation, we know the file exists
        path = self.config.get("prometheus_config")
        with open(path, "r") as fp:
            self.config["prometheus_yaml"] = yaml.safe_load(fp.read())
            self.config["original_interval"] = self.config["prometheus_yaml"]["global"][
                "scrape_interval"
            ]

    @property
    def action(self):
        return "sampling"

    def is_runtime(self) -> bool:
        return False



class KubernetesPrometheusIntervalTreatment(Treatment):
    """
    Treatment to change the global scrape interval of a Prometheus instance.

    """

    def preconditions(self) -> bool:
        """Check that the config exists at the specified location and that Prometheus is running"""
        return True

    def inject(self) -> None:
        assert self.config.get("interval")
        assert self.config.get("evaluation_interval")
        assert self.config.get("scrape_timeout")
        assert isinstance(self.orchestrator, KubernetesOrchestrator)
        
        self.deployment = self.orchestrator.get_deployment("system-under-evaluation", "app.kubernetes.io/name", "prometheus")
        
        self.initial_interval, self.initial_evaluation_interval, self.inital_scrape_timeout = self.orchestrator.get_prometheus_scrape_values()
        self.orchestrator.set_prometheus_scrape_values(scrape_interval=self.config.get("interval"), evaluation_interval=self.config.get("evaluation_interval"), scrape_timeout=self.config.get("scrape_timeout"))
        logging.info(f"Set prometheus scrape interval to {self.config.get('interval')}, evaluation interval to {self.config.get('evaluation_interval')} and scrape timeout to {self.config.get('scrape_timeout')}")

        self.orchestrator.restart_pods_of_deployment(self.deployment)


    def clean(self) -> None:
        return
        # if we clean up the changes to prometheus, the pods have to be restarted. The prometheus data is currently not persistent, so we would loose the benchmark data.
        
        assert isinstance(self.orchestrator, KubernetesOrchestrator)
        self.orchestrator.set_prometheus_scrape_values(scrape_interval=self.initial_interval, evaluation_interval=self.initial_evaluation_interval, scrape_timeout=self.inital_scrape_timeout)
        logging.info(f"Set prometheus scrape interval back to {self.initial_interval}, evaluation interval back to {self.initial_evaluation_interval} and scrape timeout back to {self.inital_scrape_timeout}")

        self.deployment = self.orchestrator.get_deployment("system-under-evaluation", "app.kubernetes.io/name", "prometheus")
        self.orchestrator.restart_pods_of_deployment(self.deployment)


    def params(self) -> dict:
        return {
            "interval": str,
            "evaluation_interval": str,
            "scrape_timeout": str,
        }

    def _validate_params(self) -> bool:
        for key, val in self.params().items():
            if key in self.config and not isinstance(self.config[key], val):
                self.messages.append(
                    f"Parameter {key} has to be of type {val} for {self.treatment_type}"
                )
        for key, value in self.config.items():
            prometheus_regex = (
                r"((([0-9]+)y)?(([0-9]+)w)?(([0-9]+)d)?(([0-9]+)h)?(([0-9]+)m)?((["
                r"0-9]+)s)?(([0-9]+)ms)?|0)"
            )
            if key == "interval" and not bool(re.match(prometheus_regex, value)):
                self.messages.append(
                    f"Parameter {key} has to match {prometheus_regex} for {self.treatment_type}"
                )
            if key == "evaluation_interval" and not bool(re.match(prometheus_regex, value)):
                self.messages.append(
                    f"Parameter {key} has to match {prometheus_regex} for {self.treatment_type}"
                )
            if key == "scrape_timeout" and not bool(re.match(prometheus_regex, value)):
                self.messages.append(
                    f"Parameter {key} has to match {prometheus_regex} for {self.treatment_type}"
                )
        return not self.messages

    def _transform_params(self) -> None:
       pass

    def _validate_orchestrator(self) -> bool:
        return super()._validate_orchestrator(["kubernetes"])
    
    @property
    def action(self):
        return "sampling"

    def is_runtime(self) -> bool:
        return False

class KubernetesPrometheusRulesTreatment(Treatment):
    """Treatment to configure Prometheus alert rules."""
    
    def preconditions(self) -> bool:
        return True

    def inject(self) -> None:
        assert self.config.get("latency_threshold")
        assert self.config.get("evaluation_window")
        assert isinstance(self.orchestrator, KubernetesOrchestrator)
        
        self.deployment = self.orchestrator.get_deployment(
            "system-under-evaluation", 
            "app.kubernetes.io/name", 
            "prometheus"
        )
        
        # Store initial values for cleanup
        self.initial_rules = self.orchestrator.get_prometheus_alert_rules()
        
        # Apply new rules
        self.orchestrator.configure_prometheus_alert_rules(
            latency_threshold=self.config.get("latency_threshold"),
            evaluation_window=self.config.get("evaluation_window")
        )
        
        # Restart to apply changes
        self.orchestrator.restart_pods_of_deployment(self.deployment)

    def clean(self) -> None:
        # Similar to PrometheusIntervalTreatment, might want to skip cleanup
        # to preserve metrics during benchmark
        pass

    def _transform_params(self) -> None:
        pass

    def _validate_orchestrator(self) -> bool:
        return super()._validate_orchestrator(["kubernetes"])
    
    def params(self) -> dict:
        return {
            "latency_threshold": int,
            "evaluation_window": str
        }

    def _validate_params(self) -> bool:
        for key, val in self.params().items():
            if key not in self.config:
                self.messages.append(
                    f"Required parameter {key} missing for {self.treatment_type}"
                )
            elif not isinstance(self.config[key], val):
                self.messages.append(
                    f"Parameter {key} has to be of type {val} for {self.treatment_type}"
                )
        return not self.messages
    
    @property
    def action(self):
        return "rule_configuration"

    def is_runtime(self) -> bool:
        return False

class StressTreatment(Treatment):
    """
    Stress system resources of a service via stress-ng.
    """

    action = "stress"

    def preconditions(self) -> bool:
        """Check if the service has stress-ng installed"""
        service = self.config.get("service_name")
        command = ["stress-ng", "--version"]
        client = docker.from_env()
        try:
            container = client.containers.get(container_id=service)
            status_code, _ = container.exec_run(cmd=command)
            logger.debug(
                f"Probed container {service} for stress-ng installation with result {status_code}"
            )
            if not status_code == 0:
                self.messages.append(
                    f"Container {service} does not have stress-ng installed which is required for {self.treatment_type}."
                )
            return status_code == 0

        except ContainerNotFound:
            logger.error(f"Can't find container {service}")
            return False
        except DockerAPIError as e:
            logger.error(f"Docker API returned an error: {e.explanation}")
            return False

    def _build_stressor_list(self):
        return list(sum(self.stressors.items(), ()))

    def _build_command(self):
        stressor_list = self._build_stressor_list()
        return (
                ["stress-ng"] + stressor_list + ["--timeout", self.config.get("duration")]
        )

    def inject(self) -> None:
        service_name = self.config.get("service_name")

        command = self._build_command()
        client = docker.from_env()

        try:
            container = client.containers.get(container_id=service_name)
            status_code, _ = container.exec_run(cmd=command)
            logger.debug(
                f"Injected stress into container {service_name}. stress-ng terminated with status code {status_code}."
            )
        except ContainerNotFound:
            logger.error(f"Can't find container {service_name}")
        except DockerAPIError as e:
            logger.error(f"Docker API returned an error: {e.explanation}")

    def clean(self) -> None:
        # stress-ng cleans up after itself
        pass

    def params(self) -> dict:
        return {
            "service_name": str,
            "stressors": dict,
            "duration": str,
        }

    def _validate_params(self) -> bool:
        for key, val in self.params().items():
            if (
                    key in {"service_name", "duration", "stressors"}
                    and key not in self.config
            ):
                self.messages.append(
                    f"Parameter {key} has to be supplied for {self.treatment_type}"
                )
            if key in self.config and not isinstance(self.config[key], val):
                self.messages.append(
                    f"Parameter {key} has to be of type {val.__class__.__name__} for {self.treatment_type}"
                )
        for key, value in self.config.items():
            if key == "duration" and not validate_time_string(value):
                self.messages.append(
                    f"Parameter {key} has to match {time_string_format_regex} for {self.treatment_type}"
                )
            if key == "stressors" and not value:
                self.messages.append(
                    f"Parameter {key} has to have at least one stressor for {self.treatment_type}"
                )
        return not self.messages

    def _transform_params(self) -> None:
        if "duration" in self.config:
            relative_time_string = self.config.get("duration")
            relative_time_seconds = time_string_to_seconds(relative_time_string)
            self.config |= {"duration_integer": relative_time_seconds}
        if "stressors" in self.config:
            # transform the stressors by prefixing with -- and place them into a new dict for clarity
            self.stressors = {}
            for stressor_name, stressor_count in self.config["stressors"].items():
                prefixed_stressor = f"--{stressor_name}"
                self.stressors[prefixed_stressor] = str(stressor_count)

    def is_runtime(self) -> bool:
        return False
