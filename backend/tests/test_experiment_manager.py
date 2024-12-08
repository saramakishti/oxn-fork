import time
import unittest.mock
import pytest
from pathlib import Path
import json
import shutil
import tempfile
from backend.internal.experiment_manager import ExperimentManager



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