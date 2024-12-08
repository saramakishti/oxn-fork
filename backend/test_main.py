from fastapi.testclient import TestClient
import pytest
import time
from httpx import ASGITransport, AsyncClient
from .main import app
print("attempting to create client")
client = TestClient(app)
print("Client created")
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
@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_create_experiment(sample_config):
    print("Creating experiment")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/experiments", json={"name": "Test Experiment 1", "config": sample_config})
    assert response.status_code == 200
    assert response.json()["name"] == "Test Experiment 1"


@pytest.mark.anyio
async def test_list_experiments(sample_config):
    print("Listing experiments")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Create first test experiment
        await ac.post("/experiments", json={"name": "List Test 1", "config": sample_config})
        
        # Get initial list
        response = await ac.get("/experiments")
        initial_count = len(response.json())
        assert response.status_code == 200
        assert initial_count > 0

        # Create second test experiment
        await ac.post("/experiments", json={"name": "List Test 2", "config": sample_config})
        
        # Get updated list
        response = await ac.get("/experiments")
        assert response.status_code == 200
        assert len(response.json()) == initial_count + 1


@pytest.mark.anyio
async def test_get_experiment_config(sample_config):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_response = await ac.post("/experiments", json={"name": "Test Experiment 2", "config": sample_config})
        id = create_response.json()["id"]
        print(f"Created experiment with id: {id}")
        response = await ac.get(f"/experiments/{id}/config")
        assert response.status_code == 200


@pytest.mark.anyio
async def test_run_experiment(sample_config):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_response = await ac.post("/experiments", json={"name": "Test Experiment 3", "config": sample_config})
        id = create_response.json()["id"]
        response = await ac.post(f"/experiments/{id}/run", json={"output_format": "json", "runs": 1})
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


@pytest.mark.anyio
async def test_get_experiment_status(sample_config):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        create_response = await ac.post("/experiments", json={"name": "Test Experiment 4", "config": sample_config})
        id = create_response.json()["id"]
        response = await ac.get(f"/experiments/{id}/status")
        assert response.status_code == 200
        assert response.json()["status"] == "PENDING"

        await ac.post(f"/experiments/{id}/run", json={"output_format": "json", "runs": 1})
        
        # Poll status with timeout
        start_time = time.time()
        while time.time() - start_time < 30:
            response = await ac.get(f"/experiments/{id}/status")
            if response.json()["status"] == "RUNNING":
                break
            await asyncio.sleep(0.5)
        
        assert response.status_code == 200
        assert response.json()["status"] == "RUNNING"
