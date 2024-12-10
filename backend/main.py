from typing import Dict, List, Optional
import logging
uvicorn_logger_error = logging.getLogger("uvicorn.error")
uvicorn_logger_error.setLevel(logging.DEBUG)
uvicorn_logger_access = logging.getLogger("uvicorn.access")
uvicorn_logger_access.setLevel(logging.DEBUG)

logger = logging.getLogger("uvicorn")
logger.info = lambda message: print(message)

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query

from pydantic import BaseModel
from datetime import datetime
from backend.internal.experiment_manager import ExperimentManager
from fastapi.responses import FileResponse




app = FastAPI(title="OXN API", version="1.0.0")
""" @app.on_event("startup")
async def startup_event():
    logger = logging.getLogger("uvicorn.access")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler) """




# Initialize experiment manager
# TODO: Get base path from some kind of config
experiment_manager = ExperimentManager("/mnt/oxn-data")

# Pydantic models for request/response validation
class ExperimentCreate(BaseModel):
    name: str
    config: Dict

class ExperimentRun(BaseModel):
    runs: int = 1
    output_format: str = "json"  # or csv

class ExperimentStatus(BaseModel):
    id: str
    name: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]


@app.post("/experiments", response_model=ExperimentStatus)
async def create_experiment(experiment: ExperimentCreate):
    """
    Create a new experiment with configuration.
    Stores experiment metadata and creates necessary directories.
    """
    return experiment_manager.create_experiment(
        name=experiment.name,
        config=experiment.config
    )

@app.post("/experiments/{experiment_id}/run", response_model=Dict)
async def run_experiment(
    experiment_id: str,
    run_config: ExperimentRun,
    background_tasks: BackgroundTasks
):
    """
    Start experiment execution asynchronously.
    - Validates experiment exists
    - Checks if another experiment is running
    - Starts execution in background
    - Returns immediately with acceptance status
    """
    if not experiment_manager.experiment_exists(experiment_id):
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    if not experiment_manager.acquire_lock():
        raise HTTPException(status_code=409, detail="Another experiment is currently running")
    
    logger.info(f"Adding background task for experiment: {experiment_id}")
    background_tasks.add_task(
        experiment_manager.run_experiment,
        experiment_id,
        output_format=run_config.output_format,
        runs=run_config.runs
    )
    
    return {
        "status": "accepted",
        "message": "Experiment started successfully",
        "experiment_id": experiment_id
    }

@app.post("/experiments/{experiment_id}/runsync", response_model=Dict)
async def run_experiment_sync(
    experiment_id: str,
    run_config: ExperimentRun,
):
    """
    Start experiment execution asynchronously.
    - Validates experiment exists
    - Checks if another experiment is running
    - Starts execution in background
    - Returns immediately with acceptance status
    """
    if not experiment_manager.experiment_exists(experiment_id):
        raise HTTPException(status_code=404, detail="Experiment not found")
        
    if not experiment_manager.acquire_lock():
        raise HTTPException(status_code=409, detail="Another experiment is currently running")
    
    logger.info(f"Running experiment synchronously: {experiment_id}")
    experiment_manager.run_experiment(
        experiment_id,
        output_format=run_config.output_format,
        runs=run_config.runs
    )
    
    return {
        "status": "accepted",
        "message": "Experiment started successfully",
        "experiment_id": experiment_id
    }

@app.get("/experiments/{experiment_id}/status", response_model=ExperimentStatus)
async def get_experiment_status(experiment_id: str):
    """Get current status of an experiment"""
    experiment = experiment_manager.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment

""" '''gets the resulting data for the given experiment id and respone variable id and the file format. If file is found it will be returned. Else a 404 not found will be given.
Supported file types are json and csv. '''
@app.get("/experiments/{experiment_id}/data/{response_name}/", response_class=None)
async def get_experiment_data(
    experiment_id: str,
    response_name : str,
    format: str = Query("csv", regex="^(json|csv)$")
):
    if format not in {"json", "csv"}:
        raise HTTPException(status_code=400, detail="Invalid type. Only 'json' and 'csv' are allowed.")
    try:
        return experiment_manager.get_experiment_data(experiment_id=experiment_id, response_name=response_name, file_ending=format)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"response variable: {response_name} for experiment: {experiment_id} not found")
   
'''Lists the reponse variables in the directory for a given, experiment id with file ending suffixes. Gives back empty lists if experiemnt id is not
a directory, or the directory is emtpy. Will be mainly used by the analysis service'''
@app.get("/experiments/{experiment_id}" , response_model=None)
async def list_experiment_files(
    experiment_id : str
):
    res  =  experiment_manager.list_experiment_variables(experiment_id=experiment_id)
    if res is not None:
        return {"response_names": res[0], "response_file_suffixes": res[1]}
    else:
        return {"response_names": [], "response_file_suffixes": []} """

@app.get("/experiments/{experiment_id}/benchmark")
async def get_benchmark_data(experiment_id: str):
    """
    Get benchmark results for experiment.
    Returns CSV file with detection times and accuracy metrics.
    """
    # TODO: Implement CSV file download response
    pass

@app.get("/experiments/{experiment_id}/report")
async def get_experiment_report(experiment_id: str):
    """
    Get experiment report for experiment.
    Returns HTML file with experiment results.
    """
    report = experiment_manager.get_experiment_report(experiment_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

# Additional Feature Endpoints
@app.post("/experiments/batch")
async def run_batch_experiments(
    experiments: List[ExperimentCreate],
    background_tasks: BackgroundTasks
):
    """
    Queue multiple experiments for execution.
    - Creates all experiments
    - Validates configurations
    - Queues them for sequential execution
    """
    # TODO: Implement batch execution queue
    pass

'''This endpoint lists all experiments in the file system with corresponding meta data. The difference  to the route : /experiemnts/experiments_id that this route lists
repsonse variables inside a directory and does not list directories. This route will be mainly used by the frontend.'''
@app.get("/experiments", response_model=List[ExperimentStatus])
async def list_experiments(
    status: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100)
):
    """
    List all experiments
    """
    experiments = experiment_manager.list_experiments()
    # Convert dict to list for response validation
    return list(experiments.values())


@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy"}

@app.get("/experiments/{experiment_id}/config")
async def get_experiment_config(experiment_id: str):
    """Get experiment configuration"""
    return experiment_manager.get_experiment(experiment_id)

# run with uvicorn:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_config=None)
