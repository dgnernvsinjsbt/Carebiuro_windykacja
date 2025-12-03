import pandas as pd
import numpy as np

print("Testing imports...")
print("Pandas version:", pd.__version__)
print("Numpy version:", np.__version__)

# Load data
print("\nLoading data...")
data = pd.read_csv('fartcoin_15m_3months.csv')
print(f"Loaded {len(data)} rows")
print(data.head())
