#%%

import json
import requests
import pandas as pd

MODES = "tube,dlr,overground,elizabeth-line,tram,bus"

#%%

# Fetching data from TFL API

tfl_data = requests.get(f"https://api.tfl.gov.uk/Line/Mode/{MODES}/Disruption").json()

print(len(tfl_data))
print(tfl_data[0].keys())


# %%

# Exploring the data structure and the keys

tfl_data_1st_row = tfl_data[0].keys()

all_keys = set()
for k in tfl_data:
    if k != tfl_data_1st_row:
        all_keys.update(k.keys())
print(all_keys)

# %%

# Counting the number of records that have each key
key_counts = {}
for record in tfl_data:
    for key in record.keys():
        if key in key_counts:
            key_counts[key] += 1
        else:            
            key_counts[key] = 1
print(json.dumps(key_counts, indent=2))


# %%

# Identifying optional keys that are not present in all records

optional_keys = [k for k in key_counts if key_counts[k] < len(tfl_data)]
print(optional_keys)

# %%

# Converting the data to a DataFrame for further exploration

df = pd.DataFrame(tfl_data)
print(df.info())
print(df.shape)
print(df.head())

# %%

# Checking for missing values in the DataFrame
print(df.isna().sum())
# %%

# Exploring the data types of the columns in the DataFrame to check for lists and dictionaries

{col: set(df[col].map(type)) for col in df.columns}


