# OXN Treatments Guide

## Overview
Treatments in OXN are actions that can be injected into the system under evaluation (SUE). They are defined as Python classes and can be referenced in experiment YAML files.

## Treatment Types
Treatments can be:
- **Runtime Treatments**: Execute during experiment runtime (e.g., network delays, packet loss)
- **Compile-time Treatments**: Execute before the experiment (e.g., configuration changes)

## Architecture

### 1. Orchestrator Layer
- Located in `kubernetes_orchestrator.py` or `docker_orchestrator.py`
- Provides low-level operations for interacting with the infrastructure
- Example operations:
  * Get/modify deployments
  * Restart pods
  * Update configurations
  * Access Kubernetes API

### 2. Treatment Layer
- Located in `treatments.py`
- Defines treatment classes that inherit from `Treatment` base class
- Each treatment must implement:
  * `inject()`: Apply the treatment
  * `clean()`: Clean up after treatment
  * `preconditions()`: Check if treatment can be applied
  * `params()`: Define required parameters
  * `is_runtime()`: Indicate if runtime or compile-time

### 3. Runner Layer
- Located in `runner.py`
- Maps treatment names to treatment classes
- Executes treatments in order
- Handles experiment flow

## Adding a New Treatment

1. **Add Orchestrator Methods**
```python
# kubernetes_orchestrator.py
class KubernetesOrchestrator:
    def new_kubernetes_operation(self, param1, param2):
        # Implement Kubernetes API calls
        pass
```

2. **Create Treatment Class**
```python
# treatments.py
class NewKubernetesTreatment(Treatment):
    def inject(self) -> None:
        assert isinstance(self.orchestrator, KubernetesOrchestrator)
        self.orchestrator.new_kubernetes_operation(
            self.config.get("param1"),
            self.config.get("param2")
        )

    def clean(self) -> None:
        # Cleanup logic

    def params(self) -> dict:
        return {
            "param1": str,
            "param2": int,
        }

    def is_runtime(self) -> bool:
        return False  # or True for runtime treatments
```

3. **Register Treatment**
```python
# runner.py
treatment_keys = {
    "new_treatment": NewKubernetesTreatment,
    # ... other treatments
}
```

4. **Use in Experiment**
```yaml
treatments:
  - new_treatment:
      action: new_treatment
      params:
        param1: "value1"
        param2: 42
```

## Best Practices

1. **Parameter Validation**
- Always validate parameters in `params()` method
- Use type hints and assertions
- Check for required parameters

2. **Clean Up**
- Implement proper cleanup in `clean()`
- Store initial state if needed
- Handle cleanup failures gracefully

3. **Orchestrator Usage**
- Use orchestrator methods for infrastructure operations
- Type check orchestrator in treatment
- Keep treatments focused on single responsibility

4. **Documentation**
- Document treatment purpose and parameters
- Include example YAML configuration
- Note any side effects or requirements

## Example: Prometheus Rules Treatment
```python
class KubernetesPrometheusRulesTreatment(Treatment):
    """Treatment to configure Prometheus alert rules"""
    
    def inject(self) -> None:
        assert isinstance(self.orchestrator, KubernetesOrchestrator)
        self.orchestrator.set_prometheus_alert_rules(
            self.config.get("latency_threshold"),
            self.config.get("evaluation_window")
        )

    def params(self) -> dict:
        return {
            "latency_threshold": int,
            "evaluation_window": str,
        }

    def is_runtime(self) -> bool:
        return False
``` 