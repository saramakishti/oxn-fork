import unittest
from rwdg import WeightedAdjMatrix
import pandas as pd
import test_constants
class TestWeightedAdjMatrixMethods(unittest.TestCase):

     def setUp(self) -> None:
          self.weighted_adf_matrix = WeightedAdjMatrix(pd.read_csv("traceDeepLearning/test/playData/recommendation_traces_new_columns.csv"))
     
     def test_build_colum_names(self):
          self.assertFalse(self.weighted_adf_matrix._build_colum_names_for_adf_mat_df(), test_constants.TEST_BUILD_COLUMN_NAMES)


'''
To test if the adjency matrix is correct (at least "syntactically") we need to do two thing here:

- Since a trace is an acyclic directed graph of spans we in he adjency matrix must have one column with only zeros since the root span does not have any parents

'''