import pandas as pd
#testAlgos\recommendation_pause_baseline_50U.h5
# Load HDF5 file into a pandas DataFrame
df = pd.read_hdf('./testAlgos/recommendation_pause_baseline_50U.h5', 'experiments/recommendation_pause_baseline.yml/26a06c7e/frontend_traces')
print(df.head(30))  # Display first few rows in a human-readable format
print(df.columns)
##print(df.shape)
#print(df[df['packet_loss_treatment'] != 'NoTreatment'])

