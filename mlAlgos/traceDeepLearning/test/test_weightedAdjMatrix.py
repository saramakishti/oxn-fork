import unittest
from rwdg import WeightedAdjMatrix
import pandas as pd

class TestWeightedAdjMatrixMethods(unittest.TestCase):

     def setUp(self) -> None:
          self.weighted_adf_matrix = WeightedAdjMatrix(pd.read_csv("traceDeepLearning/test/playData/recommendation_traces_new_columns.csv"))

     