

import pandas as pd
import constants
import itertools
import pprint
import numpy as np
from storage_client import LocalStorageHandler
from io import StringIO

'''
This class Takes in  a dataframe from with distributed tracing data and generates a dataframe
with adjency matrices for each trace that captures the average response times between services.
It is part of the RWDG Trace model and therefore part for the data wranglin for the Multilayer perceptron.
'''
class WeightedAdjMatrix:

     def __init__(self, data : pd.DataFrame) -> None:
          self.data = data
          self.service_names = constants.SERVICES
          self.columns_adj_matrix_table = self._build_colum_names_for_adf_mat_df()

     
     '''this is not dependent of the order of calls between the Microservices, so we can just iterate linearly over the dataframe
      each span represents a unit of work, if a microservice gets several requests within a trace there should be several spans -> we can go through linearly'''
     def _generate_adjacency_matrix_for_trace(self, single_trace_df : pd.DataFrame) -> list[list[tuple[int, float]]]:
          # this is the matrix that holds tuples for every (number requests , sum(request_times))
          adjency_matrix = [[(0, 0.0) for _ in range(len(self.service_names))] for _ in range(len(self.service_names))]
          for index , row in single_trace_df.iterrows():
               service_name = row[constants.SERVICE_NAME_COLUMN]
               '''
               ref_span_id can be N/A if and only if got provoked first
               '''
               ref_span_id = row[constants.REF_TYPE_SPAN_ID]
               if ref_span_id != constants.NOT_AVAILABLE:
                    out = self._find_service_name_for_spanID(ref_span_id=ref_span_id, single_trace_df=single_trace_df)
                    if out != "":
                         ref_service_name = out
                    else:
                         ref_service_name = constants.NOT_AVAILABLE
               else:     
                    ref_service_name = constants.NOT_AVAILABLE
               duration = row[constants.DURATION_COLUMN]
               # getting the corresponding index pairs for the matrix
               if ref_service_name == constants.NOT_AVAILABLE:
                    # make sure that the request that started the
                    row = 0
               else:
                    row = self.service_names[service_name]
               col = self.service_names[ref_service_name]
               # now insert into the adjency matrix
               if adjency_matrix[row][col][0] == -1:
                    adjency_matrix[row][col] = (1 , duration)
               else:
                    tuple_val = adjency_matrix[row][col]
                    adjency_matrix[row][col] = (tuple_val[0] +1, tuple_val[1] + duration)

          return adjency_matrix

     '''this method findes the span in the trace that got initialized first'''
     def _find_trace_ref_NA(self, single_trace_df : pd.DataFrame) :
          pass
     
     
     def _find_service_name_for_spanID(self, ref_span_id : str, single_trace_df : pd.DataFrame) -> str:
          # sometimes spans reference other trace ids in the  --> this slows down speed tremendiously!!! (maybe just leave it out and save time)
          for _, row in single_trace_df.iterrows():
               if row[constants.SPAN_ID_COLUMN] == ref_span_id:
                   return row[constants.SERVICE_NAME_COLUMN]
          
          return ""



     def _weight_adjency_matrix(self, tuple_adj_matrix : list[list[tuple[int, float]]]) -> list[list[float]]:

          result = [[0.0 for _ in range(len(self.service_names))] for _ in range(len(self.service_names))]

          for row_index, row  in enumerate(tuple_adj_matrix):
               for col_index , col in enumerate(row):
                    sum_req_times = tuple_adj_matrix[row_index][col_index][1]
                    number_reqs = tuple_adj_matrix[row_index][col_index][0]
                    if number_reqs > 0:
                         result[row_index][col_index] = sum_req_times / number_reqs

          return result
     
     '''
     Puts the adjancy matrices in a pandas dataframe with the following structure
     if this particular row is affected by a treatment or not and which treatment
     [trace ID, flattened_adjency matrix by row, ]
     '''
     def gen_adj_matrices_to_df(self) -> pd.DataFrame:
          rows = []
          group_df = self.data.groupby(constants.TRACE_ID_COLUMN)
          for group_name, group_data in group_df:
               tuple_list = self._generate_adjacency_matrix_for_trace(group_data)
               weighted_list = self._weight_adjency_matrix(tuple_list)
               flattened = np.array(weighted_list).flatten()
               rows.append(flattened)

          return pd.DataFrame(rows, columns=self.columns_adj_matrix_table)
     

     def _build_colum_names_for_adf_mat_df(self) -> list[str]:
          result = [constants.TRACE_ID_COLUMN]
          for out_key, out_val in constants.SERVICES.items():
               for in_key, in_val in constants.SERVICES.items():
                    if out_val != 0 and in_val != 0:
                         result.append(f"{out_val}_{in_val}")

          return result

     '''
     This function is creating the lower and upper bound for the performance anomaly detection per service tuple
     based on very simple "outlier detection". This could be up for discussion for improvements. For now I would leave it this way as stated in the paper.
     Here we use int as a val corresponding to the index in the flattened dataframe
     dict[m_n, [number of observations between MS m and n , average, variance ]]
     at another point in time we pool the variances with the assuption that the datasets are independent
     '''
     def get_bounds_for_service_calls(self , adjency_dataFrame : pd.DataFrame, std_amount : float) :
          pass#-> dict[str, [int, float, float]]:

class AdjMatrixController:


     @classmethod
     def create_adj_dataset(cls, exp_id ):
          storage_handler = GCloudStorageHandler(experiment_id=exp_id, bucket_name="3b932654-5863-9866-ae5f-0dcd4fa6a364-oxn_data_store")
          file_names = storage_handler.list_raw_datafiles_for_exp()
          if file_names:
               adjs_frames = []
               bounds = []
               for file in file_names:
                    file_content = storage_handler.get_file_from_dir(constants.RAW_DATASETS, file)
                    data_io = StringIO(file_content)
                    adj_obj = WeightedAdjMatrix(data=pd.read_csv(data_io))
                    adj_pd = adj_obj.gen_adj_matrices_to_df()
                    adj_json_bounds = adj_obj.get_bounds_for_service_calls(adjency_dataFrame=adj_pd)
                    adjs_frames.append(adj_pd)
                    bounds.append(adj_json_bounds)
               
               merged = pd.concat(adjs_frames)
               csv_buffer = StringIO()
               merged.to_csv(csv_buffer, index=False)
               csv_buffer.seek(0)
               storage_handler.write_file_to_directory(constants.MINED_DATASETS, f"{constants.ADJENCY_TOTAL_PRE}_{exp_id}.csv", csv_buffer.getvalue())

          else: 
               print(f"file_name list was empty....")

     '''
     This function is essentially for pooling the variances from the different trace_response variables together into one.
     I will take the formula for that from Wikipedia: 
     '''
     @classmethod
     def aggregate_json_bounds(cls, list_bounds):
          pass

               

if __name__ == "__main__":
     data = pd.read_csv('traceDeepLearning/test/playData/recommendation_traces.csv', na_values=[], keep_default_na=False)
     single_trace_df = data[data["trace_id"] == "f5f2a1389ef96b6c1323c9701261529d"]
     print(len(single_trace_df))
     obj = WeightedAdjMatrix(data=pd.read_csv('traceDeepLearning/test/playData/recommendation_traces.csv', na_values=[], keep_default_na=False))
     frame = obj._generate_adjacency_matrix_for_trace(single_trace_df=single_trace_df)
     print(frame)
     counter = 0
     for  x in range(len(frame)):
          for y in range(len(frame)):
               if frame[x][x][0] != 0 and frame[x][y][1] != 0.0:
                    counter += frame[x][x][0]
     
     print(counter)










    


