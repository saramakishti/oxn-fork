""" 
Purpose: Defines configuration constants.
Functionality: Contains static settings like storage file names.
Connection: Referenced throughout the application for consistent configuration values.

 """
import os


STORAGE_NAME = "store.h5"
TRIE_NAME = "trie.pickle"
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schemas', 'experiment_schema.json')
STORAGE_DIR = os.path.join(os.path.dirname(__file__), 'data')