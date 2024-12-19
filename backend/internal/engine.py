""" 
Purpose: Core logic for executing experiments.
Functionality: Manages the orchestration, execution, and observation of experiments.
Connection: Central component that coordinates between treatments, load generation, and response observation.

 """

import logging
from typing import Tuple
import yaml
from jsonschema import validate
from pathlib import Path

from backend.internal.models.response import ResponseVariable
from backend.internal.runner import ExperimentRunner
from backend.internal.docker_orchestration import DockerComposeOrchestrator
from backend.internal.kubernetes_orchestrator import KubernetesOrchestrator
from backend.internal.report import Reporter
from backend.internal.store import configure_output_path, write_dataframe, write_json_data
from backend.internal.locust_file_loadgenerator import LocustFileLoadgenerator
from backend.internal.utils import utc_timestamp
from backend.internal.errors import OxnException, OrchestrationException

logger = logging.getLogger(__name__)
logger.info = lambda message: print(message)
logger.exception = lambda message: print(message)

class Engine:
    """
    Observability experiments engine

    This class encapsulates all behavior needed to execute observability experiments.
    """

    def __init__(self, configuration_path=None, report_path=None, out_path=None, orchestrator_class=None, spec=None, id=None):
        assert configuration_path is not None, "Configuration path must be specified"
        self.config = configuration_path
        """The path to the configuration file for this engine"""
        self.id = id
        """The id of the experiment"""
        self.spec = spec
        """The loaded experiment specification"""
        self.report_path = report_path
        """The path to write the experiment report to"""
        assert report_path is not None, "Report path must be specified"
        self.reporter = Reporter(report_path=report_path)
        """A reference to a reporter instance"""
        self.out_path = out_path
        """The path to write the experiment data to"""
        self.out_formats = [] # todo erase
        """The formats to write the experiment data to"""
        self.orchestrator = orchestrator_class or KubernetesOrchestrator
        """A reference to an orchestrator instance"""
        self.generator = None
        """A reference to a load generator instance"""
        self.runner = None
        """A reference to a runner instance"""
        self.loadgen_running = False
        """Status of the load generator"""
        self.sue_running = False
        """Status of the sue"""
        self.additional_treatments = []
        self.status = 'PENDING'
        self.error_message = None
        self.started_at = None
        self.completed_at = None
        # configure the output path for HDF storage
        if self.out_path:
            configure_output_path(self.out_path)

    def read_experiment_specification(self):
        """Read the experiment specification file and confirm that its valid yaml"""
        with open(self.config, "r") as fp:
            contents = fp.read()
            try:
                self.spec = yaml.safe_load(contents)
            except yaml.YAMLError as e:
                raise OxnException(
                    message="Provided experiment spec is not valid YAML",
                    explanation=str(e),
                )

    def run(
        self,
        orchestration_timeout=None,
        randomize=False,
        accounting=False,
    ) -> Tuple[dict[str, ResponseVariable], dict[str, dict[str, dict[str, str]]]]:
        """Run an experiment 1 time"""
        assert self.spec
        assert self.spec["experiment"]
        assert self.spec["experiment"]["orchestrator"]
        self.generator = LocustFileLoadgenerator(orchestrator=self.orchestrator, config=self.spec)
        names = []
        self.runner = ExperimentRunner(
            config=self.spec,
            experiment_id=self.id,
            additional_treatments=self.additional_treatments,
            random_treatment_order=randomize,
            accountant_names=names,
            orchestrator=self.orchestrator,
        )
        self.runner.execute_compile_time_treatments()
        self.orchestrator.orchestrate()
        if not self.orchestrator.ready(expected_services=None, timeout=orchestration_timeout):
            self.runner.clean_compile_time_treatments()
            self.orchestrator.teardown()
            raise OrchestrationException(
                message="Error while building the sue",
                explanation=f"Could not build the sue within {orchestration_timeout}",
            )
        self.sue_running = True
        logger.info("Started sue")
        for treatment in self.runner.treatments.values():
            if not treatment.preconditions():
                raise OxnException(
                    message=f"Error while checking preconditions for treatment {treatment.name} which is class {treatment.__class__}",
                    explanation="\n".join(treatment.messages),
                )
        self.generator.start()
        logger.info("Started load generation")
        self.loadgen_running = True
        experiment_start = utc_timestamp()
        self.runner.experiment_start = experiment_start
        self.runner.observer.experiment_start = experiment_start
        self.runner.execute_runtime_treatments()
        self.runner.clean_compile_time_treatments()
        self.runner.experiment_end = utc_timestamp()
        self.runner.observer.experiment_end = self.runner.experiment_end
        # This runs all of the queries (prometheus, jaeger) at the end, populates self.runner.observer.variables().items()
        # It sleeps and blocks and then runs the observe() function
        # of every response variable. All of the data is stored in memory and written to disk at once.
        # If memory footprint becomes an issue, we can refactor to write the data to disk sequentially.
        self.runner.observe_response_variables()
        self.generator.stop()
        self.loadgen_running = False
        logger.info("Stopped load generation")

        

        #return self.runner.observer.variables(), self.reporter.report_data

        # Populate the report data: for each response variable, gather the interaction data for each treatment
        for _, response in self.runner.observer.variables().items():
            for _, treatment in self.runner.treatments.items():
                self.reporter.gather_interaction(
                    experiment=self.runner,
                    treatment=treatment,
                    response=response,
                )
                logger.debug(
                    f"Gathered interaction data for {treatment} and {response}"
                )
            self.reporter.assemble_interaction_data(
                run_key=self.runner.short_id
            )
            logger.debug("Assembled all interaction data")
            self.reporter.add_loadgen_data(
                runner=self.runner, request_stats=self.generator.env.stats
            )
            self.reporter.add_experiment_data(runner=self.runner)
        # Now we return two dicts, one with the dataframes and one with the report. This data then gets written to disk by the caller (ExperimentManager)

        return self.runner.observer.variables(), self.reporter.get_report_data()
    
        # Old approach: 
        for _, response in self.runner.observer.variables().items():
            # default is hdf
            if self.out_formats and 'hdf' in self.out_formats:
                write_dataframe(
                    dataframe=response.data,
                    experiment_key=self.runner.experiment_id,
                    run_key=self.runner.short_id,
                    response_key=response.name,
                )
            if self.out_formats and 'json' in self.out_formats:
                write_json_data(
                    data=response.data,
                    run_key=self.runner.short_id,
                    response_key=response.name,
                    out_path=self.out_path,
                )

            logger.debug(
                f"Experiment {self.runner.experiment_id}: DataFrame: {len(response.data)} rows"
            )
            logger.info(f"Wrote {response.name} to store")
            if self.report_path:
                for _, treatment in self.runner.treatments.items():
                    self.reporter.gather_interaction(
                        experiment=self.runner,
                        treatment=treatment,
                        response=response,
                    )
                    logger.debug(
                        f"Gathered interaction data for {treatment} and {response}"
                    )
                self.reporter.assemble_interaction_data(
                    run_key=self.runner.short_id
                )
                logger.debug("Assembled all interaction data")
                self.reporter.add_loadgen_data(
                    runner=self.runner, request_stats=self.generator.env.stats
                )
                logger.debug("Added load generation data")
                if accounting:
                    self.reporter.add_accountant_data(runner=self.runner)
                    logger.debug("Added accounting data")
        self.orchestrator.teardown()
        logger.info("Stopped sue")
        self.sue_running = False

    def prepare_experiment(self):
        """Prepare experiment directories and validate configuration"""
        try:
            # Ensure output directories exist
            output_dir = Path(self.out_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Configure output paths
            if self.out_path:
                configure_output_path(self.out_path)
                
            return True, None
        except Exception as e:
            logger.exception("Failed to prepare experiment")
            return False, str(e)

    def start_experiment(self):
        """Start experiment execution in current thread"""
        try:
            self.status = 'RUNNING'
            self.started_at = utc_timestamp()
            
            # Run with default settings
            self.run(runs=1, orchestration_timeout=300)
            
            self.status = 'COMPLETED'
            self.completed_at = utc_timestamp()
            
            return True, None
        except Exception as e:
            logger.exception("Error running experiment")
            self.status = 'FAILED'
            self.error_message = str(e)
            return False, str(e)
        finally:
            # Cleanup if needed
            if self.loadgen_running:
                self.generator.stop()
            if self.sue_running:
                self.orchestrator.teardown()

    @classmethod
    def create_from_config(cls, config_dict, output_format='hdf', output_path=None, 
                          report_path=None, orchestrator_class=None):
        """Factory method to create Engine instance from config dictionary"""
        try:
            # Validate config
            if not isinstance(config_dict, dict):
                raise ValueError("Configuration must be a dictionary")
                
            return cls(
                configuration_path=config_dict,
                out_formats=output_format,
                out_path=output_path,
                report_path=report_path,
                orchestrator_class=orchestrator_class
            )
        except Exception as e:
            logger.exception("Failed to create engine from config")
            raise ValueError(f"Invalid configuration: {str(e)}")
