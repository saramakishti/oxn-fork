
from storage_client import LocalStorageHandler
from RWDGController import RWDGController
from storage_client import LocalStorageHandler
from TraceResponseVariable import TraceResponseVariable


def main():

     storage_handler = LocalStorageHandler("data")
     file_list = storage_handler.list_files_in_dir("experiment_data")
     
     response_variables = []
     for file in file_list:
          res_data = storage_handler.get_file_from_dir("experiment_data", file)
          response_variables.append(TraceResponseVariable(res_data, "experiment_data", file))
     
     con= RWDGController(response_variables, "experiment_data", 1, "blaaa")
     con._calc_adf_matrices_for_variables()

     for var in con.variables:
          print(var.adf_matrices.head())
     
     con.get_bounds_for_service_calls()

main()










