"""
"""

from math import exp
import re
import yaml

import logging
from typing import Optional, List, Tuple
from click import File
from kubernetes import client, config
from kubernetes.stream import stream
from kubernetes.client.exceptions import ApiException

from oxn.models.orchestrator import Orchestrator  # Import the abstract base class

from .errors import OxnException, OrchestratorException, OrchestratorResourceNotFoundException

class KubernetesOrchestrator(Orchestrator):
    def __init__(self, experiment_config=None):
        logging.info("Initializing Kubernetes orchestrator")
        if experiment_config is None:
            logging.error("No experiment configuration provided. Continue with empty configuration")
            experiment_config = {}
        self.experiment_config: dict = experiment_config
        config.load_kube_config()
        self.kube_client = client.CoreV1Api()

        logging.info("Loading all running resources in k8s cluster")
        
        self.list_of_all_pods = self.kube_client.list_pod_for_all_namespaces(watch=False)
        #for i in self.list_of_all_pods.items:
            #print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
        pass

        self.list_of_all_services = self.kube_client.list_service_for_all_namespaces(watch=False)
        #for i in self.list_of_all_services.items:
            #print("%s\t%s" % (i.metadata.namespace, i.metadata.name))

        """Check if all of experiment_config.sue.required services are running"""
        self.required_services = self.experiment_config["experiment"]["sue"]["required"]
        #self._check_required_services(self.required_services)
            
    
    def _check_required_services(self, required_services) -> bool:
        """Check if all of experiment_config.sue.required services are running"""
        for service in required_services:
            service_name = service["name"]
            namespace = service["namespace"]
            try:
                service = self.kube_client.read_namespaced_service(service_name, namespace)
                #logging.info(f"Service {service_name} in namespace {namespace} is running")
            except ApiException as e:
                #logging.error(f"Service {service_name} in namespace {namespace} is not running")
                raise OxnException(
                    message=f"Service {service_name} in namespace {namespace} is not running but set as a required service",
                    explanation=str(e),
                )
        return True
            
    
    def orchestrate(self):
        logging.info("orchestrate noop implementation")
        pass

    def ready(self, expected_services: List[str] | None, timeout: int = 120) -> bool:
        if expected_services is None:
            expected_services = self.required_services
        return self._check_required_services(expected_services)

    def teardown(self):
        logging.info("teardown noop implementation")
        pass

    def translate_compose_names(self, compose_names: List[str]):
        logging.info("translate_compose_names noop implementation")
        pass

    def translate_container_names(self, container_names: List[str]):
        logging.info("translate_container_names noop implementation")
        pass

    def running_services(self) -> List[str]:
        return self.list_of_all_services.items

    """
    Get all pods for a given service and execute a command on them and aggregate the results
    If the command fails on any pod, the function will return the error code and the error message
    """
    def execute_console_command(self, label: str, command: List[str]) -> Tuple[int, str]:
        """
        Execute a console command via the kubernetes orchestrator on pods with a given label

        Args:
            label: The name of the pods as specified in app.kubernetes.io/name=<label>
            command: The command to execute

        Returns:
            A tuple of the return code and the output of the command

        Throws:
            OrchestratorResourceNotFoundException: If no pods are found for the given label
            OrchestratorException: If an error occurs while executing the command
        
        """
        #logging.info("execute_console_command noop implementation for service %s with command %s", service, command)

        # Get all pods with label app.kubernetes.io/name=service
        pods = self.kube_client.list_pod_for_all_namespaces(label_selector=f"app.kubernetes.io/name={label}")

        if not pods.items:
            raise OrchestratorResourceNotFoundException(
                message=f"No pods found for service {label}",
                explanation="No pods found for the given service",
            )
        
        # Execute the command on each pod
        for pod in pods.items:
            try:
                exec_command = command
                assert pod.metadata.annotations['kubectl.kubernetes.io/default-container']

                wrapped_command = ['sh', '-c', f"{' '.join(exec_command)}; echo $?"]
    
                response = stream(self.kube_client.connect_get_namespaced_pod_exec,
                                name=pod.metadata.name,
                                namespace=pod.metadata.namespace,
                                command=wrapped_command,
                                container=pod.metadata.annotations.get('kubectl.kubernetes.io/default-container', None),
                                stderr=True,
                                stdin=False,
                                stdout=True,
                                tty=False)
                
                # Split the response to separate the command output and exit status
                response_lines = response.split('\n')
                exit_status_line = response_lines[-2].strip()
                exit_status = int(exit_status_line)
                command_output = '\n'.join(response_lines[:-2])
                
                return exit_status, command_output
                
                logging.info(response)
            except ApiException as e:
                raise OrchestratorException(
                    message=f"Error while executing command {command} on pod {pod.metadata.name} in namespace {label}: {e.body}",
                    explanation=str(e),
                )
            

        return 0, "Success"
    
    def get_address_for_service(self, label_selector: str, label: str, namespace: str) -> str:
        """
        Get the address for a service

        Args:
            label_selector: The label selector for the service
            label: The label of the service
            namespace: The namespace of the service

        Returns:
            The address of the service

        """
        pods = self.kube_client.list_namespaced_pod(namespace, label_selector=f"{label_selector}={label}")
        if not pods.items:
            raise OrchestratorResourceNotFoundException(
                message=f"No pods found for service {label}",
                explanation="No pods found for the given service",
            )
        return pods.items[0].status.pod_ip
    
    def get_jaeger_address(self) -> str:
        """
        Get the address of the Jaeger service

        Returns:
            The address of the Jaeger service

        """
        return self.get_address_for_service(
            label_selector="app.kubernetes.io/name",
            label="jaeger",
            namespace="default",
        )
    
    def get_prometheus_address(self) -> str:
        """
        Get the address of the Prometheus service

        Returns:
            The address of the Prometheus service

        """
        return self.get_address_for_service(
            label_selector="app.kubernetes.io/name",
            label="prometheus",
            namespace="default",
        )
    
    def get_orchestrator_type(self) -> str:
        """
        Get the orchestrator type

        Returns:
            The orchestrator type

        """
        return "kubernetes"


def read_experiment_specification(self):
    """Read the experiment specification file and confirm that its valid yaml"""

    
    
    with open("C:\\Users\\Roschy\\Documents\\Masterarbeit\\oxn\\experiments\\test.yml", "r") as fp:
        contents = fp.read()
        try:
            spec = yaml.safe_load(contents)
        except yaml.YAMLError as e:
            raise OxnException(
                message="Provided experiment spec is not valid YAML",
                explanation=str(e),
            )
        return spec

def main():
    FORMAT = "%(levelname)s: %(asctime)s [%(filename)s:%(lineno)s - %(funcName)10s() ] %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT)


    """Load the experiments config file"""
    experiment_config = read_experiment_specification("experiments/test.yaml")
    logging.info("Experiment configuration loaded")
    logging.info(experiment_config)

    logging.info("Check for expected services")
    try:
        orchestrator = KubernetesOrchestrator(experiment_config)
    except OxnException as e:
        logging.error(e.message)
        logging.debug(e.explanation)
    pass
    
    

  