import time
import unittest.mock
import pytest
from pathlib import Path
import json
import shutil
import tempfile
from backend.internal.experiment_manager import ExperimentManager
import pandas as pd
from backend.internal.models.response import ResponseVariable
from backend.internal.responses import MetricResponseVariable, TraceResponseVariable
import zipfile



@pytest.fixture
def test_dir():
    """Create a temporary directory for test data"""
    tmp_dir = tempfile.mkdtemp()
    yield tmp_dir
    shutil.rmtree(tmp_dir)  # Cleanup after tests

@pytest.fixture
def experiment_manager(test_dir):
    """Create ExperimentManager instance with test directory"""
    return ExperimentManager(test_dir)

@pytest.fixture
def sample_config():
    """Sample experiment configuration"""
    return {
        "experiment": {
            "name": "big",
            "version": "0.0.1",
            "orchestrator": "kubernetes",
            "services": {
                "jaeger": {
                    "name": "astronomy-shop-jaeger-query",
                    "namespace": "system-under-evaluation"
                },
                "prometheus": [
                    {
                        "name": "astronomy-shop-prometheus-server",
                        "namespace": "system-under-evaluation",
                        "target": "sue"
                    },
                    {
                        "name": "kube-prometheus-kube-prome-prometheus", 
                        "namespace": "oxn-external-monitoring",
                        "target": "oxn"
                    }
                ]
            },
            "responses": [
                {
                    "name": "frontend_traces",
                    "type": "trace", 
                    "service_name": "frontend",
                    "left_window": "10s",
                    "right_window": "10s",
                    "limit": 1
                },
                {
                    "name": "system_CPU",
                    "type": "metric",
                    "metric_name": "sum(rate(container_cpu_usage_seconds_total{namespace=\"system-under-evaluation\"}[1m]))",
                    "left_window": "10s",
                    "right_window": "10s",
                    "step": 1,
                    "target": "oxn"
                },
                {
                    "name": "recommendation_deployment_CPU",
                    "type": "metric",
                    "metric_name": "sum(rate(container_cpu_usage_seconds_total{namespace=\"system-under-evaluation\", pod=~\"astronomy-shop-recommendationservice.*\"}[90s])) by (pod)",
                    "left_window": "10s",
                    "right_window": "10s",
                    "step": 1,
                    "target": "oxn"
                }
            ],
            "treatments": [
                {
                    "name": "empty_treatment",
                    "action": "empty",
                    "params": { "duration": "1m" }
                }
            ],
            "sue": {
                "compose": "opentelemetry-demo/docker-compose.yml",
                "exclude": ["loadgenerator"],
                "required": [
                    { "namespace": "system-under-evaluation", "name": "astronomy-shop-prometheus-server" }
                ]
            },
            "loadgen": {
                "run_time": "20m",
                "max_users": 500,
                "spawn_rate": 50,
                "locust_files": ["/backend/locust/locust_basic_interaction.py", "/backend/locust/locust_otel_demo.py"],
                "target": { "name": "astronomy-shop-frontendproxy", "namespace": "system-under-evaluation", "port": 8080 }
            }
        }
    }

def test_create_experiment(experiment_manager, sample_config):
    """Test creating a new experiment"""
    experiment = experiment_manager.create_experiment(
        name="Test Experiment",
        config=sample_config
    )
    
    assert experiment['name'] == "Test Experiment"
    assert experiment['status'] == "PENDING"
    assert experiment['spec'] == sample_config
    
    # Verify directory structure
    exp_dir = Path(experiment['paths']['data']).parent
    assert exp_dir.exists()
    assert (exp_dir / 'data').exists()
    assert (exp_dir / 'benchmark').exists()
    assert (exp_dir / 'report').exists()
    
    # Verify experiment.json was created
    assert (exp_dir / 'experiment.json').exists()
    
def test_get_experiment(experiment_manager, sample_config):
    """Test retrieving an experiment"""
    created = experiment_manager.create_experiment(
        name="Test Experiment",
        config=sample_config
    )
    
    retrieved = experiment_manager.get_experiment(created['id'])
    assert retrieved == created

def test_get_nonexistent_experiment(experiment_manager):
    """Test retrieving a non-existent experiment"""
    assert experiment_manager.get_experiment("nonexistent") is None

def test_experiment_exists(experiment_manager, sample_config):
    """Test checking if experiment exists"""
    experiment = experiment_manager.create_experiment(
        name="Test Experiment",
        config=sample_config
    )
    
    assert experiment_manager.experiment_exists(experiment['id']) is True
    assert experiment_manager.experiment_exists("nonexistent") is False

def test_update_experiment(experiment_manager, sample_config):
    """Test updating experiment metadata"""
    experiment = experiment_manager.create_experiment(
        name="Test Experiment",
        config=sample_config
    )
    
    updates = {
        'status': 'RUNNING',
        'started_at': '2023-12-07T12:00:00'
    }
    
    updated = experiment_manager.update_experiment(experiment['id'], updates)
    assert updated['status'] == 'RUNNING'
    assert updated['started_at'] == '2023-12-07T12:00:00'
    
    # Verify changes were persisted
    retrieved = experiment_manager.get_experiment(experiment['id'])
    assert retrieved['status'] == 'RUNNING'
    assert retrieved['started_at'] == '2023-12-07T12:00:00'

def test_list_experiments(experiment_manager, sample_config):
    """Test listing all experiments"""
    # Create a few experiments
    exp1 = experiment_manager.create_experiment("Test 1", sample_config)
    time.sleep(1)
    exp2 = experiment_manager.create_experiment("Test 2", sample_config)
    
    experiments = experiment_manager.list_experiments()
    assert len(experiments) == 2
    assert experiments[exp1['id']] == exp1
    assert experiments[exp2['id']] == exp2

def test_acquire_release_lock(experiment_manager):
    """Test experiment locking mechanism"""
    # Should be able to acquire lock initially
    assert experiment_manager.acquire_lock() is True
    
    # Second attempt should fail
    assert experiment_manager.acquire_lock() is False
    
    # After releasing, should be able to acquire again
    experiment_manager.release_lock()
    assert experiment_manager.acquire_lock() is True

@pytest.mark.asyncio
async def test_run_experiment(experiment_manager, sample_config):
    """Test running an experiment"""
    experiment = experiment_manager.create_experiment(
        name="Test Experiment",
        config=sample_config
    )
    
    # Engine class mock
    with unittest.mock.patch('backend.internal.engine.Engine') as MockEngine:
        mock_engine = MockEngine.return_value
        
        experiment_manager.run_experiment(
            experiment['id'],
            output_format='hdf',
            runs=1
        )
        
        MockEngine.assert_called_once()
        mock_engine.run.assert_called_once_with(
            runs=1,
            orchestration_timeout=None,
            randomize=False,
            accounting=False
        )

def test_write_experiment_data(experiment_manager):
    """Test writing experiment data in different formats"""
    experiment = experiment_manager.create_experiment(
        name="Test Experiment vhjifk",
        config={"test": "config"}
    )
    
    # Create mock orchestrator
    mock_orchestrator = unittest.mock.Mock()
    
    # Create test response data using concrete implementations
    responses = {
        "metric1": MetricResponseVariable(
            orchestrator=mock_orchestrator,
            name="metric1",
            experiment_start=1000,
            experiment_end=2000,
            right_window="10s",
            left_window="10s",
            description={
                "metric_name": "test_metric",
                "step": 1,
                "left_window": "10s",
                "right_window": "10s"
            },
            target="oxn"
        ),
        "trace1": TraceResponseVariable(
            orchestrator=mock_orchestrator,
            name="trace1",
            experiment_start=1000,
            experiment_end=2000,
            right_window="10s",
            left_window="10s",
            description={
                "service_name": "test-service",
                "limit": 100,
                "left_window": "10s",
                "right_window": "10s"
            }
        )
    }
    
    # Set the data directly since we're not actually observing
    responses["metric1"].data = pd.DataFrame({
        "timestamp": [1, 2, 3],
        "value": [10.0, 20.0, 30.0],
        "cpu_usage": [0.5, 0.7, 0.9],
        "memory_mb": [256, 512, 1024],
        "requests_per_sec": [100, 150, 200]
    })
    responses["trace1"].data = pd.DataFrame({
        "id": [1, 2],
        "name": ["trace1", "trace2"], 
        "duration": [100, 200],
        "status": ["success", "success"],
        "error_count": [0, 0],
        "span_count": [5, 8]
    })
    
    # Write data in different formats
    # responses : Dict[str, ResponseVariable]
    experiment_manager.write_experiment_data(
        run=0,
        experiment_id=experiment['id'],
        responses=responses,
        formats=["csv", "json"]
    )
    
    # Verify files were created
    data_dir = experiment_manager.experiments_dir / experiment['id'] / 'data'
    assert (data_dir / f"0_{experiment['id']}_metric1.csv").exists()
    assert (data_dir / f"0_{experiment['id']}_metric1.json").exists()
    assert (data_dir / f"0_{experiment['id']}_trace1.json").exists()
    
    # Verify CSV content
    df = pd.read_csv(data_dir / f"0_{experiment['id']}_metric1.csv")
    assert len(df) == 3
    assert list(df.columns) == ["timestamp", "value", "cpu_usage", "memory_mb", "requests_per_sec"]
    
    # Verify JSON content
    with open(data_dir / f"0_{experiment['id']}_trace1.json") as f:
        trace_data = json.load(f)
        assert len(trace_data) == 2

def test_get_experiment_response_data(experiment_manager):
    """Test retrieving experiment response data"""
    experiment = experiment_manager.create_experiment(
        name="Test Experiment",
        config={"test": "config"}
    )
    print(experiment['id'])
    # Create mock orchestrator
    mock_orchestrator = unittest.mock.Mock()
    
    # Create test response data
    responses = {
        "metric1": MetricResponseVariable(
            orchestrator=mock_orchestrator,
            name="metric1",
            experiment_start=1000,
            experiment_end=2000,
            right_window="10s",
            left_window="10s",
            description={
                "metric_name": "test_metric",
                "step": 1,
                "left_window": "10s",
                "right_window": "10s"
            },
            target="oxn"
        )
    }
    
    # Set the data directly
    responses["metric1"].data = pd.DataFrame({
        "timestamp": [1, 2, 3],
        "value": [10.0, 20.0, 30.0]
    })

    # Write data in different formats
    experiment_manager.write_experiment_data(
        run=0,
        experiment_id=experiment['id'],
        responses=responses,
        formats=["csv", "json"]
    )

    # Test retrieving CSV data
    csv_response = experiment_manager.get_experiment_response_data(
        run=0,
        experiment_id=experiment['id'],
        response_name=f"metric1",
        file_ending="csv"
    )
    assert csv_response.media_type == "text/csv"
    assert csv_response.filename == f"0_{experiment['id']}_metric1.csv"

    # Test retrieving JSON data  
    json_response = experiment_manager.get_experiment_response_data(
        run=0,
        experiment_id=experiment['id'],
        response_name=f"metric1", 
        file_ending="json"
    )
    assert json_response.media_type == "application/json"
    assert json_response.filename == f"0_{experiment['id']}_metric1.json"

    # Test retrieving non-existent file
    with pytest.raises(FileNotFoundError):
        experiment_manager.get_experiment_response_data(
            run=0,
            experiment_id=experiment['id'],
            response_name="nonexistent",
            file_ending="csv"
        )

    # Test retrieving invalid file type
    with pytest.raises(FileNotFoundError):
        experiment_manager.get_experiment_response_data(
            run=0,
            experiment_id=experiment['id'],
            response_name=f"0_{experiment['id']}_metric1",
            file_ending="invalid"
        )

def test_zip_experiment_data(experiment_manager):
    """Test zipping experiment data"""
    experiment = experiment_manager.create_experiment(
        name="Test Experiment",
        config={"test": "config"}
    )
    
    # Create mock orchestrator
    mock_orchestrator = unittest.mock.Mock()
    
    # Create test response data
    responses = {
        "metric1": MetricResponseVariable(
            orchestrator=mock_orchestrator,
            name="metric1",
            experiment_start=1000,
            experiment_end=2000,
            right_window="10s",
            left_window="10s",
            description={
                "metric_name": "test_metric",
                "step": 1,
                "left_window": "10s",
                "right_window": "10s"
            },
            target="oxn"
        ),
        "trace1": TraceResponseVariable(
            orchestrator=mock_orchestrator,
            name="trace1",
            experiment_start=1000,
            experiment_end=2000,
            right_window="10s",
            left_window="10s",
            description={
                "service_name": "test-service",
                "limit": 100,
                "left_window": "10s",
                "right_window": "10s"
            }
        )
    }
    
    # Set the data directly
    responses["metric1"].data = pd.DataFrame({
        "timestamp": [1, 2, 3],
        "value": [10.0, 20.0, 30.0],
        "cpu_usage": [0.5, 0.7, 0.9],
        "memory_mb": [256, 512, 1024],
        "requests_per_sec": [100, 150, 200]
    })
    responses["trace1"].data = pd.DataFrame({
        "id": [1, 2],
        "name": ["trace1", "trace2"], 
        "duration": [100, 200],
        "status": ["success", "success"],
        "error_count": [0, 0],
        "span_count": [5, 8]
    })

    # Write data in different formats
    experiment_manager.write_experiment_data(
        run=0,
        experiment_id=experiment['id'],
        responses=responses,
        formats=["csv", "json"]
    )

    # Test zipping experiment data
    zip_response = experiment_manager.zip_experiment_data(
        experiment_id=experiment['id']
    )

    # the zip response is a PosixPath
    assert isinstance(zip_response, Path)
    assert zip_response.name == f"{experiment['id']}.zip"
    assert zip_response.exists()
    assert zip_response.is_file()
    

    # Test zipping non-existent experiment data
    with pytest.raises(FileNotFoundError):
        experiment_manager.zip_experiment_data(
            experiment_id="nonexistent"
        )

def test_list_experiment_variables(experiment_manager):
    """Test listing experiment variables"""
    # Create test experiment with data
    experiment = experiment_manager.create_experiment(
        name="Test Experiment",
        config={"test": "config"}
    )

    mock_orchestrator = unittest.mock.Mock()
    
    # Create and write test data
    responses = {
        "metric1": MetricResponseVariable(
            orchestrator=mock_orchestrator,
            name="metric1",
            experiment_start=1000,
            experiment_end=2000,
            right_window="10s",
            left_window="10s",
            description={
                "metric_name": "test_metric",
                "step": 1,
                "left_window": "10s",
                "right_window": "10s"
            },
            target="oxn"
        ),
        "trace1": TraceResponseVariable(
            orchestrator=mock_orchestrator,
            name="trace1",
            experiment_start=1000,
            experiment_end=2000,
            right_window="10s",
            left_window="10s",
            description={
                "service_name": "test-service",
                "limit": 100,
                "left_window": "10s",
                "right_window": "10s"
            }
        )
    }

    responses["metric1"].data = pd.DataFrame({
        "timestamp": [1, 2, 3],
        "value": [10.0, 20.0, 30.0],
        "cpu_usage": [0.5, 0.7, 0.9],
        "memory_mb": [256, 512, 1024],
        "requests_per_sec": [100, 150, 200]
    })
    responses["trace1"].data = pd.DataFrame({
        "id": [1, 2],
        "name": ["trace1", "trace2"], 
        "duration": [100, 200],
        "status": ["success", "success"],
        "error_count": [0, 0],
        "span_count": [5, 8]
    })
    
    experiment_manager.write_experiment_data(
        run=0,
        experiment_id=experiment['id'],
        responses=responses,
        formats=["csv", "json"]
    )
    
    # Test listing variables
    variables = experiment_manager.list_experiment_variables(experiment['id'])
    assert variables is not None
    print(variables)
    var_names, file_endings = variables
    assert f"metric1" in var_names
    assert f"trace1" in var_names
    assert "csv" in file_endings
    assert "json" in file_endings
    
    # Test non-existent experiment
    assert experiment_manager.list_experiment_variables("nonexistent") is None