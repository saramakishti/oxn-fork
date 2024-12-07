from typing import Dict, List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from backend.internal.experiment_manager import ExperimentManager

app = FastAPI(title="OXN API", version="1.0.0")

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

@app.get("/experiments/{experiment_id}/status", response_model=ExperimentStatus)
def get_experiment_status(experiment_id: str):
    """Get current status of an experiment"""
    experiment = experiment_manager.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment

# Results Endpoints
@app.get("/experiments/{experiment_id}/data")
async def get_experiment_data(
    experiment_id: str,
    format: str = Query("hdf", regex="^(hdf|json)$")
):
    """
    Get experiment run data in specified format.
    - Validates experiment exists and has completed
    - Converts data format if needed
    - Returns file download
    """
    # TODO: Implement file download response
    pass

@app.get("/experiments/{experiment_id}/benchmark")
async def get_benchmark_data(experiment_id: str):
    """
    Get benchmark results for experiment.
    Returns CSV file with detection times and accuracy metrics.
    """
    # TODO: Implement CSV file download response
    pass

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

@app.get("/experiments", response_model=List[ExperimentStatus])
async def list_experiments(
    status: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100)
):
    """
    List all experiments
    """
    return experiment_manager.list_experiments()


@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy"}

