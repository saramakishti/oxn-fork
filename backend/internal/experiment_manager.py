
import zipfile
import yaml
from backend.internal.models.response import ResponseVariable
from fastapi import HTTPException
from pathlib import Path
import json
import time
from datetime import datetime
import fcntl
import logging
from fastapi.responses import FileResponse
from typing import Dict, Optional, Tuple, List
import pandas as pd
from backend.internal.engine import Engine
from backend.internal.kubernetes_orchestrator import KubernetesOrchestrator

logger = logging.getLogger(__name__)
logger.info = lambda message: print(message)
logger.error = lambda message: print(message)
logger.warning = lambda message: print(message)
logger.debug = lambda message: print(message)

class ExperimentManager:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.experiments_dir = self.base_path / 'experiments'
        self.lock_file = self.base_path / '.lock'
        self.counter = 0
        
        # Ensure directories exist
        self.experiments_dir.mkdir(parents=True, exist_ok=True)

    def create_experiment(self, name, config):
        """Create new experiment directory and config file"""
        if not self.acquire_lock():
            logger.info("Lock already held, skipping experiment check")
            return False
        try:
            experiment_id = str(self.counter) + str(int(time.time()))
            self.counter += 1
            experiment_dir = self.experiments_dir / experiment_id
            logger.info(f"Creating experiment: {name}")
            logger.info(f"Experiment ID: {experiment_id}")
            logger.info(f"Experiment Directory: {experiment_dir}")
            experiment = {
                'id': experiment_id,
                'name': name,
                'status': 'PENDING',
                'created_at': datetime.now().isoformat(),
                'started_at': None,
                'completed_at': None,
                'error_message': None,
                'spec': config,
                'paths': {
                    'data': str(experiment_dir / 'data'),
                    'benchmark': str(experiment_dir / 'benchmark'),
                    'report': str(experiment_dir / 'report')
                }
            }
            
            # Create directories
            experiment_dir.mkdir(parents=True)
            (experiment_dir / 'data').mkdir()
            (experiment_dir / 'benchmark').mkdir()
            (experiment_dir / 'report').mkdir()
            
            # Save experiment config
            with open(experiment_dir / 'experiment.json', 'w') as f:
                json.dump(experiment, f, indent=2)
        finally:
            self.release_lock()
        return experiment

    def get_experiment(self, experiment_id):
        """Get experiment config"""
        try:
            with open(self.experiments_dir / experiment_id / 'experiment.json') as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def get_experiment_report(self, experiment_id):
        """Get experiment report"""
        report_dir = self.experiments_dir / experiment_id / 'report'
        for file in report_dir.glob('*.yaml'):
            with open(file) as f:
                return f.read()
        return None
    
    def run_experiment(self, experiment_id, output_formats, runs):
        """Run experiment"""
        if not self.acquire_lock():
            logger.info("Lock already held, skipping experiment check")
            return False
        try:
            logger.info(f"Changing experiment status to RUNNING")
            self.update_experiment(experiment_id, {'status': 'RUNNING'})
            experiment = self.get_experiment(experiment_id)['spec']
            report_path = self.experiments_dir / experiment_id / 'report'
            out_path = self.experiments_dir / experiment_id / 'data'

            orchestrator = KubernetesOrchestrator(experiment_config=experiment)
        
            engine = Engine(
                configuration_path=experiment,
                report_path=report_path,
                out_path=out_path,
                orchestrator_class=orchestrator,
                spec=experiment,
                id=experiment_id
            )
            report_data = {}
            for idx in range(runs):
                # report contains different run keys for each run.
                # A mismatch here: the report data is stored in a dict with run keys, but the response data is stored in a dict with response names.
                # Multiple calls to run() will keep on adding to the report data, so we only care about this object when we are done with all runs.
                # In contrast, we care about the response data for each run, so we need to write it to disk immediately.
                responses, report_data = engine.run(orchestration_timeout=None, randomize=False, accounting=False)
                
                self.write_experiment_data(idx,experiment_id, responses, output_formats)

            # Write the report data to disk
            with open(report_path / "report.yaml", "w") as f:
                yaml.dump(report_data, f)
        except Exception as e:
            logger.error(f"Error running experiment: {e}")
            import traceback
            logger.error(f"stacktrace: {traceback.format_exc()}")
            self.update_experiment(experiment_id, {'status': 'FAILED', 'error_message': str(e)})
        finally:
            self.update_experiment(experiment_id, {'status': 'COMPLETED'})
            self.release_lock()
    
    def experiment_exists(self, experiment_id):
        """Check if experiment exists"""
        return (self.experiments_dir / experiment_id / 'experiment.json').exists()


    def update_experiment(self, experiment_id, updates):
        """Update experiment config"""
        try:
            experiment = self.get_experiment(experiment_id)
            if experiment:
                experiment.update(updates)
                with open(self.experiments_dir / experiment_id / 'experiment.json', 'w') as f:
                    json.dump(experiment, f, indent=2)
                return experiment
            else:
                return None
        except Exception as e:
            logger.error(f"Error updating experiment: {e}")
            return None

    def list_experiments(self):
        """List all experiments"""
        experiments = {}
        for exp_dir in self.experiments_dir.iterdir():
            if exp_dir.is_dir():
                try:
                    with open(exp_dir / 'experiment.json') as f:
                        experiments[exp_dir.name] = json.load(f)
                except FileNotFoundError:
                    continue

        return experiments

    def acquire_lock(self):
        """File-based locking using fcntl"""
        try:
            # store the lock file path as an instance variable if not already open
            if not hasattr(self, 'lock_fd'):
                self.lock_fd = open(self.lock_file, 'w')
                fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True
            return False  # lock is held
        except (IOError, BlockingIOError):
            return False

    def release_lock(self):
        """Release file lock"""
        if hasattr(self, 'lock_fd'):
            fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            self.lock_fd.close()
            delattr(self, 'lock_fd')
    
    def get_experiment_response_data(self,run: int, experiment_id: str, response_name: str, file_ending: str):
        '''gets experiments data for a given id and data format, the given file'''
        data_path = Path(self.experiments_dir) / experiment_id / 'data'
        
        # List all matching files for the given response name and file ending
        matching_files = list(data_path.glob(f"{run}_{experiment_id}_{response_name}.{file_ending}"))
        
        if not matching_files:
            raise FileNotFoundError(f"No {file_ending} files found for response {response_name}")
        
        # Match the file name to our convention
        path = data_path / f"{run}_{experiment_id}_{response_name}.{file_ending}"
        
        if file_ending == "json":
            return FileResponse(path, media_type="application/json", filename=f"{run}_{experiment_id}_{response_name}.{file_ending}")
        elif file_ending == "csv":
            return FileResponse(path, media_type="text/csv", filename=f"{run}_{experiment_id}_{response_name}.{file_ending}")
        else:
            logger.info("Unexpected file format requested")
            raise FileNotFoundError("Queried for an unsupported file format")

    def zip_experiment_data(self, experiment_id : str):
        '''zips all the data for a given experiment id'''
        # Example zip file name: <experiment_id>.zip
        data_path = Path(self.experiments_dir) / experiment_id / 'data'
        zip_path = Path(self.experiments_dir) / experiment_id / f'{experiment_id}.zip'
        
        if not data_path.is_dir():
            logger.error(f"experiment directory {experiment_id} does not exist")
            raise FileNotFoundError(f"experiment directory {experiment_id} does not exist")
            
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=7) as zipf:
            for file in data_path.iterdir():
                if file.is_file():
                    zipf.write(file, arcname=file.name)
                    
        return zip_path
    
    def get_data(self, path: Path):
        '''gets all the data for a given path'''
        with open(path, 'rb') as file:
            yield from file

        
    def write_experiment_data(self, run: int, experiment_id : str, responses : Dict[str, ResponseVariable], formats : List[str]):
        '''writes the response data to disk'''
        for _ , response in responses.items():
            # use experiment id / run id / response name as key
            for format in formats:
                if response.data is None:
                    logger.error(f"response data is None for {response.name}")
                    continue
                if format == "csv":
                    # example filename: <run_id>_<experiment_id>_<response_name>.csv
                    # Then the columns will be all the different fields of the response
                    # Then write the response data to a csv file
                    response.data.to_csv(self.experiments_dir / experiment_id / 'data' / f"{run}_{experiment_id}_{response.name}.csv", index=False)
                    logger.debug(f"wrote {run}_{experiment_id}_{response.name}.csv")
                elif format == "json":
                    if isinstance(response.data, pd.DataFrame):
                        response.data = response.data.to_dict(orient='records') # type: ignore
                    # example filename: <run_id>_<experiment_id>_<response_name>.json
                    # Then write the response data to a json file
                    with open(self.experiments_dir / experiment_id / 'data' / f"{run}_{experiment_id}_{response.name}.json", "w") as f:
                        json.dump(response.data, f)
                    logger.debug(f"wrote {run}_{experiment_id}_{response.name}.json")

    def list_experiment_variables(self, experiment_id : str )-> Optional[Tuple[List[str], List[str]]]:
        '''list all files (response varibales) in a given experiment folder, returns None if folder does not exist or is empty'''
        path = Path(self.experiments_dir ) / experiment_id / 'data'
        if not path.is_dir():
            logger.error(f"experiment directory {experiment_id} does not exist")
            return None
        
        # List all files in the data directory
        files = list(path.iterdir())
        if not files:
            logger.info(f"empty experiment directory with ID {experiment_id}, no reponse variables found")
            return None

        # Extract just the response variable name (after last underscore, before extension)
        variable_names = [file.name.split('_')[-1].split('.')[0] for file in files if file.is_file()]
        file_endings = [file.suffix[1:] for file in files if file.is_file()]

        if not variable_names:
            logger.info(f"empty experiment directory with ID {experiment_id}, no reponse variables found")
            return None

        return variable_names, file_endings
        
        


        

