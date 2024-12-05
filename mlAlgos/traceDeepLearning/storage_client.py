

'''
Here I use the class coding to an interface for the bridge between local developement and dev. in the cloud
'''
from __future__ import annotations
from abc import ABC, abstractmethod
import os
from google.cloud import storage
import constants

class StorageHandler(ABC):

     @abstractmethod
     def list_raw_datafiles_for_exp(self, dir_name) -> list[str]:
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

     def __init__(self, rel_path=None) -> None:
          super().__init__()
          self.rel_path = rel_path if rel_path is not None  else ""
     
     def list_files_in_dir(self, dir_name) -> list[str]:
          try:
               files = os.listdir(dir_name)
               file_list = [f for f in files if os.path.isfile(os.path.join(dir_name, f))]
               return file_list
          except FileNotFoundError:
               print(f"Error: Directory '{dir_name}' not found.")
               return []
     
     def write_file_to_directory(self, dir_name, file_name, file_content) -> None:
        try:
            os.makedirs(dir_name, exist_ok=True)
            file_path = os.path.join(dir_name, file_name)
            with open(file_path, 'w') as file:
                file.write(file_content)

        except Exception as e:
            print(f"Error: Could not write file '{file_name}' to '{dir_name}'. {e}")
     
     def get_file_from_dir(self, dir_name, file_name):
        try:
            file_path = os.path.join(dir_name, file_name)
            with open(file_path, 'r') as file:
                content = file.read()
            return content
        except FileNotFoundError:
            print(f"Error: File '{file_name}' not found in directory '{dir_name}'.")
            return None
        except Exception as e:
            print(f"Error: Could not retrieve file '{file_name}' from '{dir_name}'. {e}")
            return None
     

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
              
     '''
     In this case dirname raw_data, transformed_data or eval_data
     '''
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

