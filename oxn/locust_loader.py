
import importlib
from importlib.machinery import ModuleSpec
import importlib.util
import logging

from locust import HttpUser, TaskSet, task
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging
from .errors import LocustException, OxnException
from .kubernetes_orchestrator import KubernetesOrchestrator
from .models.orchestrator import Orchestrator
import oxn.utils as utils

from gevent import Greenlet
from gevent.pool import Group

logger = logging.getLogger(__name__)


class LocustLoader:
    """
    Locust loader for oxn
    This loads the locust file and runs the locust file
    """
    
    def __init__(self, orchestrator: Orchestrator, config: dict):
        assert orchestrator is not None
        self.orchestrator = orchestrator
        """A reference to the orchestrator instance"""
        assert config is not None
        self.config = config
        """The experiment spec"""
        self.run_time: int = 0
        """The total desired run time of the load generation"""
        self.env = None
        """Locust environment"""
        self.locust_files = None
        """List of Locust files to run"""
        self._read_config()
        """Read the experiment spec and populate stages and tasks"""
        self.greenlets = Group()

    def _read_config(self):
        """Read the load generation section of an experiment specification"""
        loadgen_section: dict = self.config["experiment"]["loadgen"]
        self.stages = loadgen_section.get("stages", None)
        self.run_time = int(utils.time_string_to_seconds(loadgen_section["run_time"]))
        self.locust_files = loadgen_section.get("locust_files", None)
       
        self.target = loadgen_section.get("target")
        
        self.base_address = "localhost"
        self.port = 8080
        
        if self.target:
            assert isinstance(self.orchestrator, KubernetesOrchestrator), "Orchestrator must be KubernetesOrchestrator if target is specified"
            self.base_address = self.orchestrator.get_address_for_service(self.target["label_selector"], self.target["label"], self.target["namespace"])
            self.port = self.target["port"]
            
        logger.info(f"Base address for load generation set to {self.base_address}:{self.port}")
        
        self.env = Environment(user_classes=[], host=f"http://{self.base_address}:{self.port}")
        self.env.create_local_runner()
        
        for locust_file in self.locust_files:
            path = locust_file["path"]
            locust_module = self._load_locust_file(path)
            for user_class in dir(locust_module):
                user_class_instance = getattr(locust_module, user_class)
                if isinstance(user_class_instance, type) and issubclass(user_class_instance, HttpUser) and user_class_instance is not HttpUser:
                    self.env.user_classes.append(user_class_instance)
                    logger.info(f"Added user class {user_class_instance.__name__} from {path}")
                    
        
    def _load_locust_file(self, path):
        """Load a locust file from the specified path"""
        spec = importlib.util.spec_from_file_location("locustfile", path)
        if not spec:
            raise LocustException(f"Could not load locust file from {path}")
        
        assert isinstance(spec, ModuleSpec)
        assert spec.loader is not None
        
        locustfile = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(locustfile)
        return locustfile

    def start(self):
        """Start the load generation"""
        setup_logging("INFO", None)
        
        assert self.env is not None, "Locust environment must be initialized before starting"
        assert self.env.runner is not None, "Locust runner must be initialized before starting"
        
        self.env.runner.start(100, 5.0)
        self.greenlets.spawn(stats_printer(self.env.stats))
        self.greenlets.spawn(stats_history, self.env.runner)


    def stop(self):
        """Join the greenlet created by locust env (= wait until it has finished)"""
        if self.env and self.env.runner:
            self.env.runner.quit()
            self.greenlets.join(timeout=30)  # Add a timeout to ensure it doesn't stall indefinitely
            self.greenlets.kill()  # Kill any remaining greenlets if they didn't terminate

    def kill(self):
        """Kill all greenlets spawned by locust"""
        self.greenlets.kill()
        if self.env and self.env.runner:
            self.env.runner.quit()  # Ensure the runner is stopped if kill is called


