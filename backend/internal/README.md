### Connections and Workflow 
1. **Initialization**: 
* The application starts with `__main__.py`, which calls `main.py`. 
2. **Argument Parsing**: 
* `main.py` uses `argparser.py` to parse and validate command-line arguments. 
3. **Logging Setup**: 
* `main.py` calls `log.py` to initialize logging based on parsed arguments. 
4. **Engine Setup**: 
* `main.py` creates an instance of `Engine` from `engine.py`, passing the configuration paths and other parameters. 
5. **Context and Treatments**: 
* `engine.py` uses `context.py` to dynamically load user-defined treatments if specified. 
6. **Validation**: 
* Before running the experiment, `engine.py` validates the configuration using `validation.py`. 
7. **Orchestration**: 
* `engine.py` uses `orchestration.py` to set up the system under experiment (SUE) using Docker Compose. 
8. **Load Generation**: 
* During the experiment, `engine.py` uses `loadgen.py` to generate load on the services under test. 
9. **Observation**: 
* `engine.py` and `observer.py` work together to monitor and record response variables using `responses.py` and API interactions with Prometheus and Jaeger. 
10. **Treatments**: 
* `runner.py` manages the application of treatments from `treatments.py` during the experiment run. 
11. **Data Storage**: 
* Experiment data is stored and retrieved using `store.py` for persistent storage. 
12. **Reporting**: 
* After the experiment, `report.py` compiles the results and generates a report. 
13. **Pricing and Resource Utilization**: 
* `pricing.py` calculates resource usage and costs, which can be included in the final report.


