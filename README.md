## Introduction
OXN - **O**bservability e**X**periment e**N**gine - 
is an extensible software framework to run observability experiments and compare observability design decisions.
OXN follows the design principles of cloud benchmarking and strives towards portable and repeatable experiments.
Experiments are defined as yaml-based configuration files, which allows them to be shared, versioned and repeated.
OXN automates every step of the experiment process in a straightforward manner, from SUE setup to data collection, processing and reporting. 


## Installation

##### Prerequisites
- Docker + Docker Compose
- Python >= v3.10
- Jupyter


###### Setup the OpenTelemetry demo application
1.  Change to the forked demo submodule folder

    ```cd opentelemetry-demo/```

2. Build needed containers. This will take a while a while

    ``` make build ```

    Alternativly, you can just build the container with fault injection, e.g., the recommender service. This may cause incompatability in the future. 

    ``` docker compose build recommendationservice ```

3. Run docker compose to start the demo

    ```docker compose up```

3. Verify the demo application is working by visiting

* ```http:localhost:8080/``` for the Webstore
* ```http:localhost:8080/jaeger/ui``` for Jaeger
* ```http:localhost:9090``` for Prometheus

##### Install oxn via pip

> Note: oxn requires Python >= 3.10

1. Install virtualenv

    ```pip install virtualenv```

2. Create a virtualenv (named venv here)

    ```virtualenv venv```

3. Source the venv 

    ```source venv/bin/activate```

4. Install oxn

    ```pip install . ```

> Note: oxn requires the pytables package, which in turn requires a set of dependencies.


##### Run an example observability experiment
1. Verify that oxn is correctly installed 

```
oxn --help
usage: oxn [-h] [--times TIMES] [--report REPORT] [--accounting] [--randomize] [--extend EXTEND] [--loglevel [{debug,info,warning,error,critical}]] [--logfile LOG_FILE] [--timeout TIMEOUT] spec

Observability experiments engine

positional arguments:
  spec                  Path to an oxn experiment specification to execute.

options:
  -h, --help            show this help message and exit
  --times TIMES         Run the experiment n times. Default is 1
  --report REPORT       Create an experiment report at the specified location. If the file exists, it will be overwritten. If it does not exist, it will be created.
  --accounting          Capture resource usage for oxn and the sue. Requires that the report option is set.Will increase the time it takes to run the experiment by about two seconds for each service in the sue.
  --randomize           Randomize the treatment execution order. Per default, treatments are executed in the order given in the experiment specification
  --extend EXTEND       Path to a treatment extension file. If specified, treatments in the file will be loaded into oxn.
  --loglevel [{debug,info,warning,error,critical}]
                        Set the log level. Choose between debug, info, warning, error, critical. Default is info
  --logfile LOG_FILE    Write logs to a file. If the file does not exist, it will be created.
  --timeout TIMEOUT     Timeout after which we stop trying to build the SUE. Default is 1m

```

2. Run an experiment and write the experiment report to disk 

```
oxn experiments/recommendation_pause_baseline.yml --report baseline_report.yml

```

### Running in kubernetes
#### Cluster Requirements
The cluster provides Persistent Volume Claims (PVCs) to store data over multiple pod restarts. For this, the cluster makes use of OpenEBS in the default given config of OXN. Install OpenEBS with the following command:

```bash
kubectl apply -f https://openebs.github.io/charts/openebs-operator.yaml
```

> You can also use other implementations of PVCs. Just make sure to change the values in the helm configs accordingly.

#### External Observability Stack
For the Prometheus and Grafana, we use the [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack) which deploys and configures Prometheus and Grafana in a ready to use state.

The following commands add the helm repository and install the kube-prometheus-stack in a specific namespace and apply custom configurations:
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install kube-prometheus prometheus-community/kube-prometheus-stack 
    --namespace oxn-external-monitoring 
    --create-namespace 
    --version 62.5.1 
    -f values_kube_prometheus.yaml
```

Kepler also provides a Helm chart. Therefore, the provision is straightforward. We [follow the instructions from the official documentation](https://sustainable-computing.io/installation/kepler-helm/) and execute the following commands. The Command deploys Kepler in the correct namespace and applies custom changes.

```bash
helm repo add kepler https://sustainable-computing-io.github.io/kepler-helm-chart
helm repo update

helm install kepler kepler/kepler \
    --namespace oxn-external-monitoring \
    --create-namespace \
    --set serviceMonitor.enabled=true \
    --set serviceMonitor.labels.release=kube-prometheus \
    -f values_kepler.yaml 
```

There is a preconfigured dashboard for Grafana. The dashboard is deployed from the OXN repository using the command:
```bash
GF_POD=$(
    kubectl get pod \
        -n oxn-external-monitoring \
        -l app.kubernetes.io/name=grafana \
        -o jsonpath="{.items[0].metadata.name}"
)
kubectl cp kepler_dashboard.json oxn-external-monitoring/$GF_POD:/tmp/dashboards/kepler_dashboard.json
```


#### System Under Experiment Setup
Deployment of the SUE follows also the instructions from the [official documentation](https://opentelemetry.io/docs/demo/kubernetes-deployment/) Deploy the SUE in an own namespace and apply a custom configuration file:

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update
helm install astronomy-shop open-telemetry/opentelemetry-demo 
    --namespace system-under-evaluation 
    --create-namespace
    -f values_opentelemetry_demo.yaml 
```

