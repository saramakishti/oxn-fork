
import pandas as pd

class TraceResponseVariable:

     def __init__(self, data : pd.DataFrame, experiment_id : str, service_name):
          self.data = data
          self.experiment_id = experiment_id
          self.service_name = service_name
          self.adf_matrices : pd.DateFrame = None #[traceID, flattended matrix, treatment yes / No, performance_anomaly yes / no]
          self.rss_strings : pd.DateFrame = None # [traceID, RSS String , treatment yes /no , workflow anomaly ]
          #self.mined_data : pd.DataFrame = None
     
     

