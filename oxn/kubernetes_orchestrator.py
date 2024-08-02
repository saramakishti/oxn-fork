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
from kubernetes.client.models.v1_deployment import V1Deployment

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
        self.api_client = client.AppsV1Api()

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
        Get the first address found for a service

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
        assert self.experiment_config["experiment"] is not None
        assert self.experiment_config["experiment"]["pods"] is not None
        assert self.experiment_config["experiment"]["pods"]["jaeger"] is not None
        
        jaeger_label_selector = self.experiment_config["experiment"]["pods"]["jaeger"]["label_selector"]
        jaeger_label = self.experiment_config["experiment"]["pods"]["jaeger"]["label"]
        jaeger_namespace = self.experiment_config["experiment"]["pods"]["jaeger"]["namespace"]
        return self.get_address_for_service(
            label_selector=jaeger_label_selector,
            label=jaeger_label,
            namespace=jaeger_namespace,
        )
    
    def get_prometheus_address(self) -> str:
        """
        Get the address of the Prometheus service

        Returns:
            The address of the Prometheus service

        """
        
        assert self.experiment_config["experiment"] is not None
        assert self.experiment_config["experiment"]["pods"] is not None
        assert self.experiment_config["experiment"]["pods"]["prometheus"] is not None
        
        prometheus_label_selector = self.experiment_config["experiment"]["pods"]["prometheus"]["label_selector"]
        prometheus_label = self.experiment_config["experiment"]["pods"]["prometheus"]["label"]
        prometheus_namespace = self.experiment_config["experiment"]["pods"]["prometheus"]["namespace"]
        return self.get_address_for_service(
            label_selector=prometheus_label_selector,
            label=prometheus_label,
            namespace=prometheus_namespace,
        )
    
    def get_orchestrator_type(self) -> str:
        """
        Get the orchestrator type

        Returns:
            The orchestrator type

        """
        return "kubernetes"
    

    def get_deployment(self, namespace, label_selector, label) -> V1Deployment:
        """
        Get the deployment for a service

        Args:
            namespace: The namespace of the service
            label_selector: The label selector for the service
            label: The label of the service

        Returns:
            The deployment of the service

        """
        deployments = self.api_client.list_namespaced_deployment(namespace, label_selector=f"{label_selector}={label}")
        if not deployments.items:
            raise OrchestratorResourceNotFoundException(
                message=f"No deployments found for service {label}",
                explanation="No deployments found for the given service",
            )
        if len(deployments.items) > 1:
            raise OrchestratorException(
                message=f"Multiple deployments found for service {label}",
                explanation="Multiple deployments found for the given service",
            )
        return deployments.items[0]
    
    def scale_deployment(self, deployment: V1Deployment, replicas: int):
        """
        Scale a deployment

        Args:
            deployment: The deployment to scale
            replicas: The number of replicas

        """
        assert deployment is not None
        assert deployment.spec is not None
        assert deployment.metadata is not None
        assert deployment.metadata.name is not None
        assert deployment.metadata.namespace is not None
        assert deployment.spec.replicas is not None
        assert replicas >= 0

        deployment.spec.replicas = replicas
        response = self.api_client.patch_namespaced_deployment_scale(
            name=deployment.metadata.name,
            namespace=deployment.metadata.namespace,
            body=deployment,
        )
        return response
