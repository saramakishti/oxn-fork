
from fastapi import HTTPException
from pathlib import Path
import json
import time
from datetime import datetime
import fcntl
import logging
from fastapi.responses import FileResponse
from typing import Optional, Tuple, List

from backend.internal.engine import Engine

logger = logging.getLogger(__name__)

class ExperimentManager:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.experiments_dir = self.base_path / 'experiments'
        self.lock_file = self.base_path / '.lock'
        
        # Ensure directories exist
        self.experiments_dir.mkdir(parents=True, exist_ok=True)

    def create_experiment(self, name, config):
        """Create new experiment directory and config file"""
        experiment_id = str(int(time.time()))
        experiment_dir = self.experiments_dir / experiment_id
        
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
        
        return experiment

    def get_experiment(self, experiment_id):
        """Get experiment config"""
        try:
            with open(self.experiments_dir / experiment_id / 'experiment.json') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
    
    def run_experiment(self, experiment_id, output_format, runs):
        """Run experiment"""
        if not self.experiment_exists(experiment_id):
            raise HTTPException(status_code=404, detail="Experiment not found")
        experiment = self.get_experiment(experiment_id)['spec']
        report_path = self.experiments_dir / experiment_id / 'report'
        out_path = self.experiments_dir / experiment_id / 'data'
        engine = Engine(configuration_path=None, report_path=report_path, out_path=out_path, out_formats=[output_format], orchestrator_class=None, spec=experiment)

        engine.run(runs=runs, orchestration_timeout=None, randomize=False, accounting=False)

    
    def experiment_exists(self, experiment_id):
        """Check if experiment exists"""
        return (self.experiments_dir / experiment_id / 'experiment.json').exists()

    def update_experiment(self, experiment_id, updates):
        """Update experiment config"""
        experiment = self.get_experiment(experiment_id)
        if experiment:
            experiment.update(updates)
            with open(self.experiments_dir / experiment_id / 'experiment.json', 'w') as f:
                json.dump(experiment, f, indent=2)
        return experiment

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
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (IOError, BlockingIOError):
            return False

    def release_lock(self):
        """Release file lock"""
        if hasattr(self, 'lock_fd'):
            fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            self.lock_fd.close()
            delattr(self, 'lock_fd')
    
    def get_experiment_data(self, experiment_id : str, response_name : str , file_ending : str):
        '''gets experiments data for a given id and data format, the given file'''
        path = Path(self.experiments_dir) / experiment_id /(response_name + "." + file_ending)
        logger.info(f"Path: {path}")
        logger.info(f"Suffix: {path.suffix}")
        if not path.is_file():
            raise FileNotFoundError()
        
        if path.suffix == ".json":
            return FileResponse(path, media_type="application/json", filename=f"{response_name}{path.suffix}")
        elif path.suffix == ".csv":
            return FileResponse(path, media_type="text/csv", filename=f"{response_name}{path.suffix}")
        else:
            logger.info("unexpected behavior inside the filesystem")
            raise FileNotFoundError("queried for a not specified error")


    def list_experiment_variables(self, experiment_id : str )-> Optional[Tuple[List[str], List[str]]]:
        '''list all files (response varibales) in a given experiment folder, returns None if folder does not exist or is empty'''
        path = Path(self.experiments_dir ) / experiment_id
        if not path.is_dir():
            logger.error(f"experiment directory {experiment_id} does not exist")
            return None

        variable_names = [file.name.split('.')[0] for file in path.iterdir() if file.is_file()]
        file_endings = [file.suffix[1:] for file in path.iterdir() if file.is_file()]

        if not variable_names:
            logger.info(f"empty experiment directory with ID {experiment_id}, no reponse variables found")
            return None

        return variable_names , file_endings
        
        


        

