"""
"""

from cProfile import label
from math import exp
import re
import yaml
import time

import logging
from typing import Optional, List, Tuple
from click import File
from kubernetes import client, config
from kubernetes.stream import stream
from kubernetes.client.exceptions import ApiException
from kubernetes.client.models.v1_deployment import V1Deployment
from kubernetes.client.models.v1_pod import V1Pod

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
    def execute_console_command_on_all_matching_pods(self, label_selector:str, label: str, namespace: str, command: List[str]) -> Tuple[int, str]:
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
        pods = self.kube_client.list_namespaced_pod(namespace=namespace, label_selector=f"{label_selector}={label}")
        #pods = self.kube_client.list_pod_for_all_namespaces(label_selector=f"app.kubernetes.io/name={label}")

        if not pods.items:
            raise OrchestratorResourceNotFoundException(
                message=f"No pods found with the given label selector {label_selector}={label}",
                explanation="No pods found with the given label selector {label_selector}={label}",
            )
        
        # Execute the command on each pod
        for pod in pods.items:
            try:
                exec_command = command
                assert pod.metadata.labels[label_selector]
                
                container = None
                if pod.spec.containers and pod.spec.containers.__len__() > 1:
                    logging.warning(f"Pod {pod.metadata.name} in namespace {label} has more than one container. Using the first container to execute the command. (Container: {pod.spec.containers[0].name})")
                    container = pod.spec.containers[0]
                else:
                    container = pod.spec.containers[0]

                wrapped_command = ['sh', '-c', f"{' '.join(exec_command)}; echo $?"]
    
                response = stream(self.kube_client.connect_get_namespaced_pod_exec,
                                name=pod.metadata.name,
                                namespace=pod.metadata.namespace,
                                command=wrapped_command,
                                container=container.name,
                                stderr=True,
                                stdin=False,
                                stdout=True,
                                tty=False)
                
                if response == "0":
                    return 0, "Success"
                
                # if response includes "not found" or "no such file or directory" then the command was not found
                if "not found" in response or "no such file or directory" in response:
                    return -1, f"Command not found: {' '.join(exec_command)}"
                    
                # Split the response to separate the command output and exit status
                response_lines = response.split('\n')
                exit_status_line = response_lines[-2].strip()
                print(exit_status_line)
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
    
    def apply_security_context_to_deployment(self, label_selector:str, label: str, namespace: str, capabilities: dict) -> Tuple[int, str]:
        """
        Apply a security context to a deployment

        Args:
            label_selector: The label selector for the deployment
            label: The name of the deployment
            namespace: The namespace of the deployment
            security_context: The security context to apply

        Returns:
            A tuple of the return code and the output of the command

        Throws:
            OrchestratorResourceNotFoundException: If no pods are found for the given label
            OrchestratorException: If an error occurs while executing the command
        
        """
        try:
            # Get the deployment
            deployment = self.get_deployment(namespace, label_selector, label)

           
            
             # Apply the security context to each container
            container_bodies = []
            containers = deployment.spec.template.spec.containers
            for container in containers:
                container_body = {
                    "name": container.name,
                    "securityContext": {
                        "capabilities": capabilities
                    }
                }
                container_bodies.append(container_body)
                
            # Prepare the patch body
            patch_body = {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": container_bodies
                        }
                    }
                }
            }

        
            print(patch_body)
            # Apply the patch
            response = self.api_client.patch_namespaced_deployment(
                name=deployment.metadata.name,
                namespace=deployment.metadata.namespace,
                body=patch_body,
            )
            return 0, "Success"

        except ApiException as e:
            print(f"Exception when calling AppsV1Api->patch_namespaced_deployment: {e}")
            return 1, str(e)
        except Exception as e:
            print(f"Unexpected error: {e}")
            return 1, str(e)
                
    
    def get_address_for_service(self, namespace: str, name: str) -> str:
        """
        Get the first address found for a service

        Args:
            label_selector: The label selector for the service
            label: The label of the service
            namespace: The namespace of the service

        Returns:
            The address of the service

        """
        
        service = self.kube_client.read_namespaced_service(namespace=namespace, name=name)
        if not service:
            raise OrchestratorResourceNotFoundException(
                message=f"No service found for service {label}",
                explanation="No service found for the given service",
            )
        cluster_ip = service.spec.cluster_ip
        
        if cluster_ip is None or cluster_ip == "None":  
            logging.info(f"Service {name} in namespace {namespace} has no cluster IP. Falling back to pod IP by selecting first pod and receiving its IP")
            # fall back to pod IP
            name_label_of_service = service.metadata.labels["app.kubernetes.io/name"]
            pods = self.kube_client.list_namespaced_pod(namespace=namespace, label_selector=f"app.kubernetes.io/name={name_label_of_service}")
            if not pods.items:
                raise OrchestratorResourceNotFoundException(
                    message=f"No pods found for service {label}",
                    explanation="No pods found for the given service",
                )
            cluster_ip = pods.items[0].status.pod_ip
        
        return cluster_ip
        
    
    def get_jaeger_address(self) -> str:
        """
        Get the address of the Jaeger service

        Returns:
            The address of the Jaeger service

        """
        assert self.experiment_config["experiment"] is not None
        assert self.experiment_config["experiment"]["services"] is not None
        assert self.experiment_config["experiment"]["services"]["jaeger"] is not None
        
        jaeger_name = self.experiment_config["experiment"]["services"]["jaeger"]["name"]
        jaeger_namespace = self.experiment_config["experiment"]["services"]["jaeger"]["namespace"]
        return self.get_address_for_service(
            name=jaeger_name,
            namespace=jaeger_namespace,
        )
    
    def get_prometheus_address(self, target) -> str:
        """
        Get the address of the Prometheus service

        Returns:
            The address of the Prometheus service

        """
        
        assert self.experiment_config["experiment"] is not None
        assert self.experiment_config["experiment"]["services"] is not None
        assert self.experiment_config["experiment"]["services"]["prometheus"] is not None
        
        prometheus_configs = self.experiment_config["experiment"]["services"]["prometheus"]
               
        for prometheus_config in prometheus_configs:
            assert prometheus_config["target"] is not None
            if prometheus_config["target"] == target:
                assert prometheus_config["name"] is not None
                assert prometheus_config["namespace"] is not None
                prometheus_name = prometheus_config["name"]
                prometheus_namespace = prometheus_config["namespace"]
                return self.get_address_for_service(
                    name=prometheus_name,
                    namespace=prometheus_namespace,
                )
        
        raise OrchestratorException(
            message=f"No Prometheus configuration found for target {target}",
            explanation="No Prometheus configuration found for the given target",
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

    def get_pods(self, namespace, label_selector, label) -> List[V1Pod]:
        """
        Get the pods for a service

        Args:
            namespace: The namespace of the service
            label_selector: The label selector for the service
            label: The label of the service

        Returns:
            The pods of the service

        """
        pods = self.kube_client.list_namespaced_pod(namespace, label_selector=f"{label_selector}={label}")
        if not pods.items:
            raise OrchestratorResourceNotFoundException(
                message=f"No pods found with the given label selector {label_selector}={label}",
                explanation="No pods found with the given label selector {label_selector}={label}",
            )
        return pods.items
    
    def kill_pod(self, pod: V1Pod):
        """
        Kill a pod

        Args:
            pod: The pod to kill

        """
        assert pod is not None
        assert pod.metadata is not None
        assert pod.metadata.name is not None
        assert pod.metadata.namespace is not None
        try:
            response = self.kube_client.delete_namespaced_pod(
                name=pod.metadata.name,
                namespace=pod.metadata.namespace,
                grace_period_seconds=0,
            )
            return response
        except ApiException as e:
            raise OrchestratorException(
                message=f"Error while deleting pod {pod.metadata.name} in namespace {pod.metadata.namespace}: {e.body}",
                explanation=str(e),
            )
    def set_deployment_env_parameter(self, deployment: V1Deployment, environment_variable_name: str, environment_variable_value: str):
        """
        Set an environment variable for a deployment

        Args:
            deployment: The deployment to set the environment variable for
            environment_variable_name: The name of the environment variable
            environment_variable_value: The value of the environment variable


        """
        assert deployment is not None
        assert deployment.spec is not None
        assert deployment.metadata is not None
        assert deployment.metadata.name is not None
        assert deployment.metadata.namespace is not None
        assert deployment.spec.template is not None
        assert deployment.spec.template.spec is not None
        assert deployment.spec.template.spec.containers is not None
        assert environment_variable_name is not None
        assert environment_variable_value is not None
        
        new_env_var = client.V1EnvVar(name=environment_variable_name, value=environment_variable_value)
        
        # repeate until it is working
        for i in range(0, 10):
            try:
                deployment = self.get_deployment(namespace=deployment.metadata.namespace, label_selector="app.kubernetes.io/name", label=deployment.metadata.name)

                container_bodies = []
                containers = deployment.spec.template.spec.containers
                container = containers[0]

                if container.env is None:
                    container.env = []

                # check if env variable already exists and update it
                is_updated = False
                for env_var in container.env:
                    if env_var.name == environment_variable_name:
                        env_var.value = environment_variable_value
                        is_updated = True
                        break
                if not is_updated:
                    container.env.append(new_env_var)
                    
                response = self.api_client.patch_namespaced_deployment(
                    name=deployment.metadata.name,
                    namespace=deployment.metadata.namespace,
                    body=deployment,
                )
                return response
            except ApiException as e:
                logging.error(f"Error while updating deployment {deployment.metadata.name} in namespace {deployment.metadata.namespace}: {e.body}. Waiting for 1 second and retrying. Retry {i}")
                time.sleep(1)
                
        raise OrchestratorException(
            message=f"Error while updating deployment {deployment.metadata.name} in namespace {deployment.metadata.namespace}",
            explanation="Error while updating deployment",
        )
        
    
    def get_deployment_env_parameters(self, deployment: V1Deployment) -> List[client.V1EnvVar]:
        """
        Get the environment variables for a deployment

        Args:
            deployment: The deployment to get the environment variables for

        Returns:
            The environment variables of the deployment

        """
        assert deployment is not None
        assert deployment.spec is not None
        assert deployment.metadata is not None
        assert deployment.metadata.name is not None
        assert deployment.metadata.namespace is not None
        assert deployment.spec.template is not None
        assert deployment.spec.template.spec is not None
        assert deployment.spec.template.spec.containers is not None
        
        containers = deployment.spec.template.spec.containers
        container = containers[0]
        if container.env is None:
            return []
        return container.env
    
    def is_deployment_ready(self, deployment: V1Deployment) -> bool:
        """
        Check if a deployment is ready

        Args:
            deployment: The deployment to check

        Returns:
            True if the deployment is ready, False otherwise

        """
        assert deployment is not None
        assert deployment.metadata is not None
        assert deployment.metadata.name is not None
        assert deployment.metadata.namespace is not None
        
        # update deployment status
        deployment = self.api_client.read_namespaced_deployment_status(
            name=deployment.metadata.name,
            namespace=deployment.metadata.namespace,
        )
        
        assert deployment.status is not None
        return deployment.status.ready_replicas == deployment.status.replicas and deployment.status.replicas > 0
    
    def set_prometheus_scrape_values(self, scrape_interval, evaluation_interval, scrape_timeout):
        """
        Set the Prometheus scrape values

        Args:
            scrape_interval: The scrape interval
            evaluation_interval: The evaluation interval
            scrape_timeout: The scrape timeout

        """
        
        # TODO: make this more generic
        try:
            configmap = self.kube_client.read_namespaced_config_map(name="astronomy-shop-prometheus-server", namespace="system-under-evaluation")
        except ApiException as e:
            raise OrchestratorException(
                message=f"Error while reading ConfigMap astronomy-shop-prometheus-server in namespace system-under-evaluation: {e.body}",
                explanation=str(e),
            )
            
        assert configmap is not None
        assert isinstance(configmap, client.V1ConfigMap)
        assert configmap.data is not None
        
        prometheus_config_yaml = configmap.data.get('prometheus.yml')

        if not prometheus_config_yaml:
            raise OrchestratorException(
                message="prometheus.yml not found in ConfigMap",
                explanation="prometheus.yml not found in ConfigMap",
            )


        prometheus_config = yaml.safe_load(prometheus_config_yaml)

        if scrape_interval is not None:
            prometheus_config['global']['scrape_interval'] = scrape_interval
        if evaluation_interval is not None:
            prometheus_config['global']['evaluation_interval'] = evaluation_interval
        if scrape_timeout is not None:
            prometheus_config['global']['scrape_timeout'] = scrape_timeout

        updated_prometheus_config_yaml = yaml.dump(prometheus_config, default_flow_style=False)

        configmap.data['prometheus.yml'] = updated_prometheus_config_yaml
        
        try:
            self.kube_client.patch_namespaced_config_map(name="astronomy-shop-prometheus-server", namespace="system-under-evaluation", body=configmap)
            logging.info(f"ConfigMap astronomy-shop-prometheus-server updated successfully.")
        except ApiException as e:
            raise OrchestratorException(
                message=f"Error while updating ConfigMap astronomy-shop-prometheus-server in namespace system-under-evaluation: {e.body}",
                explanation=str(e),
            )
                
                
    def get_prometheus_scrape_values(self) -> Tuple[str, str, str]:
        """
        Get the Prometheus scrape values

        Returns:
            A tuple of the scrape interval, evaluation interval, and scrape timeout

        """
        
        try:
            configmap = self.kube_client.read_namespaced_config_map(name="astronomy-shop-prometheus-server", namespace="system-under-evaluation")
        except ApiException as e:
            raise OrchestratorException(
                message=f"Error while reading ConfigMap astronomy-shop-prometheus-server in namespace system-under-evaluation: {e.body}",
                explanation=str(e),
            )
            
        assert configmap is not None
        assert isinstance(configmap, client.V1ConfigMap)
        assert configmap.data is not None
        
        prometheus_config_yaml = configmap.data.get('prometheus.yml')

        if not prometheus_config_yaml:
            raise OrchestratorException(
                message="prometheus.yml not found in ConfigMap",
                explanation="prometheus.yml not found in ConfigMap",
            )

        prometheus_config = yaml.safe_load(prometheus_config_yaml)

        scrape_interval = prometheus_config['global']['scrape_interval']
        evaluation_interval = prometheus_config['global']['evaluation_interval']
        scrape_timeout = prometheus_config['global']['scrape_timeout']

        return scrape_interval, evaluation_interval, scrape_timeout

    def restart_pods_of_deployment(self, deployment: V1Deployment):
        """
        Restart pods for a service

        Args:
            deployment: The deployment to restart the pods for

        """
        assert deployment is not None
        assert deployment.metadata is not None
        assert deployment.metadata.name is not None
        assert deployment.metadata.namespace is not None
        assert deployment.spec is not None
        assert deployment.spec.selector is not None
        assert deployment.spec.selector.match_labels is not None
    
        
        pods = self.kube_client.list_namespaced_pod(
            namespace=deployment.metadata.namespace,
            label_selector="app.kubernetes.io/name=prometheus" # TODO: make this more generic
        )
        for pod in pods.items:
            self.kill_pod(pod)
            
        time.sleep(1)
        for i in range(0, 10):
            if self.is_deployment_ready(deployment):
                break
            time.sleep(i * 2)
            logging.info(f"Waiting for deployment {deployment.metadata.name} to be ready after restart. Retry {i}")
            
        logging.info(f"Deployment {deployment.metadata.name} is ready after restart")
            
        
