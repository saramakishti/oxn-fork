

'''
Here I use the class coding to an interface for the bridge between local developement and dev. in the cloud
'''
from __future__ import annotations
from abc import ABC, abstractmethod
import os

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
     


