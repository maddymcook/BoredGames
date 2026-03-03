# mlflow server --port 8080 --backend-store-uri sqlite:///mlruns.db

import requests

import pandas as pd
from sklearn.datasets import fetch_california_housing

# ----------------------------
# Load dataset
# ----------------------------
housing = fetch_california_housing()

# Create features X and target y.
X = pd.DataFrame(housing.data, columns=housing.feature_names)
y = housing.target  # Median house value in $100,000s

host="http://127.0.0.1:5000"
model_name = 'california-housing'
model_version = '4'

data = {"features": X.iloc[0].to_dict()}

response = requests.post(f'{host}/{model_name}/version/{model_version}/predict', json=data, verify=False)

print(response.raise_for_status())

print(response.json())
