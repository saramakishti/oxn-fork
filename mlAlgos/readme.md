# Machine Learning Algorithms for Distributed Tracing Data

This is just for developing and keeping track of decisions we make throughout the process

# Constructing Experiments for the ML Data based in distributed tracing

     One of the questions that hunt me is how much data do we actually need?
     We inject faults into the recommendationservice for example -> do we need to collect data from all microservices in the SUE?

     I tried collecting dis. Traces from all Microservices these were the responses from Jaeger:

          [2024-11-27 14:17:25,161] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture accountingservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response
          [2024-11-27 14:17:25,226] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture adservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response
          [2024-11-27 14:17:25,271] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture checkoutservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response
          [2024-11-27 14:17:25,299] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture currencyservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response
          [2024-11-27 14:17:25,413] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture emailservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response
          [2024-11-27 14:17:25,472] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture frauddetectionservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response
          [2024-11-27 14:17:25,536] DESKTOP-BP9O4AV/INFO/oxn.observer: failed to capture paymentservice_traces, proceeding. Cannot concatenate dataframes: Jaeger sent an empty response

     
     Microservices I got data from:
          - frontend
          - frontend-proxy
          - recommendationservice
          - cartservice
     
     For right now these are the the microservices that are also provoked from Locust.... andd the tasks defined in the experiment.

     ==> we need to define very good experiments for the distributed tracing Algorithm adn especially locust tasks.


          


