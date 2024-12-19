

'''
Here I use the class coding to an interface for the bridge between local developement and dev. in the cloud
'''
from __future__ import annotations
from abc import ABC, abstractmethod
import os
import constants
import pandas as pd
from pathlib import Path

class StorageHandler(ABC):

     @abstractmethod
     def list_files_in_dir(self, dir_name) -> list[str]:
          '''
          This class lists all Filenames in a directory
          '''
     
     @abstractmethod
     def write_file_to_directory(self, dir_name, file_name, file_content) -> None:
          '''
          writes File to directory given the name and the content
        '''
     @abstractmethod
     def get_file_from_dir(self, dir_name, file_name):
          '''
          retrieves file from directory
          '''
     
# TODO add rel_path offset in all functions
class LocalStorageHandler(StorageHandler):

     def __init__(self, base_path) -> None:
          super().__init__()
          self.base_path = base_path
     
     def list_files_in_dir(self, experiment_id) -> list[str]:
          try:
               dir_path = Path(self.base_path) / Path(experiment_id)
               print(dir_path)
               files = os.listdir(dir_path)
               return files
          except FileNotFoundError:
               print(f"Error: Directory '{dir_path}' not found.")
               return []
     
     def write_file_to_directory(self, dir_name, file_name, file_content: pd.DataFrame) -> None:
          try:
               os.makedirs(dir_name, exist_ok=True)
               file_path = os.path.join(dir_name, file_name)
               file_content.to_csv(file_path, index=False)
          except Exception as e:
               print(f"Error: Could not write file '{file_name}' to '{dir_name}'. {e}")

     
     def get_file_from_dir(self, experiment_id, response_variable_name) -> pd.DataFrame | None:
          try:
               file_path = Path(self.base_path) / Path(experiment_id) / Path(response_variable_name )
               print(file_path)
               df = pd.read_csv(file_path)
               df
               return df
          except FileNotFoundError:
               print(f"Error: File for : '{response_variable_name}' not found in directory '{experiment_id}'.")
               return None
          except pd.errors.EmptyDataError:
               print(f"Error: File '{response_variable_name}' is empty or has invalid data.")
               return None
          except Exception as e:
               print(f"Error: Could not retrieve or parse file '{response_variable_name}' from '{experiment_id}'. {e}")
               return None
     
     def get_service_names(self):
          return 


if __name__ == "__main__":
     shandler = LocalStorageHandler("data")
     file_list = shandler.list_files_in_dir("experiment_data")
     for f in file_list:
          data = shandler.get_file_from_dir("experiment_data", f)
          if data is not None:
               print(data.head(5))



# TODO add OXN storage client

'''
class GCloudStorageHandler(StorageHandler):
     # bucket name comes from terraform script
     def __init__(self, experiment_id, bucket_name) -> None:
          super().__init__()
          self.experiment_id = experiment_id
          self.client_instance = storage.client()
          self.bucket_name = bucket_name

     
     def list_raw_datafiles_for_exp(self) -> list[str] | None:
          try:
               bucket = self.client_instance.bucket(self.bucket_name)
               blobs = bucket.list_blobs(prefix=f"{self.experiment_id}/{constants.RAW_DATASETS}")
               result = []
               for b in blobs:
                    result.append(b.name)
               return result
          except Exception as e:
              print(f"problem when listing the files for bucket {self.bucket_name} and experiment {self.experiment_id} : {e.__str__}")
              
     #In this case dirname raw_data, transformed_data or eval_data
   
     def get_file_from_dir(self, dir_name, file_name):
          try:
               bucket = self.client_instance.bucket(self.bucket_name)
               full_name = f"{self.experiment_id}/{dir_name}/{file_name}"
               blob = bucket.blob(full_name)     
               file_content = blob.download_as_string().decode('utf-8')
               return file_content
          except Exception as e:
               print(f"problem when downloading blob from storage : {e.__str__}")
     
     def write_file_to_directory(self, dir_name, file_name, file_content) -> None:
          try:
               bucket = self.client_instance.bucket(self.bucket_name)
               full_blob_name = f"{dir_name}/{file_name}"
               blob = bucket.blob(full_blob_name)
               blob.upload_from_string(file_content)
          except Exception as e:
               print(f"problem when uploading the file to storag : {e.__str__}")

'''