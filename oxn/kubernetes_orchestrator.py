"""
"""

from math import exp
import os
import yaml
import schema

import logging
from typing import Optional, List
from click import File
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from errors import OxnException

class KubernetesOrchestrator:
    def __init__(self, experiment_config=None):
        logging.info("Initializing Kubernetes orchestrator")
        if experiment_config is None:
            logging.error("No experiment configuration provided. Continue with empty configuration")
            experiment_config = {}
        self.experiment_config: dict = experiment_config
        config.load_kube_config()
        self.kube_client = client.CoreV1Api()

        logging.info("Loading all running resources in k8s cluster")
        
        list_of_all_pods = self.kube_client.list_pod_for_all_namespaces(watch=False)
        for i in list_of_all_pods.items:
            print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
        pass

        list_of_all_services = self.kube_client.list_service_for_all_namespaces(watch=False)
        for i in list_of_all_services.items:
            print("%s\t%s" % (i.metadata.namespace, i.metadata.name))

        """Check if all of experiment_config.sue.required services are running"""
        self._check_required_services()
            
    
    def _check_required_services(self):
        """Check if all of experiment_config.sue.required services are running"""
        required_services = self.experiment_config["experiment"]["sue"]["required"]
        for service in required_services:
            service_name = service["name"]
            namespace = service["namespace"]
            try:
                service = self.kube_client.read_namespaced_service(service_name, namespace)
                logging.info(f"Service {service_name} in namespace {namespace} is running")
            except ApiException as e:
                logging.error(f"Service {service_name} in namespace {namespace} is not running")
                raise OxnException(
                    message=f"Service {service_name} in namespace {namespace} is not running but set as a required service",
                    explanation=str(e),
                )












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

if __name__ == "__main__":
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
    
    

  