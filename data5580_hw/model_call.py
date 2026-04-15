import json
import urllib.request

from sklearn.datasets import fetch_california_housing

BASE = "http://127.0.0.1:5000"
MODEL_NAME = "california-housing"  # MLflow-registered name
MODEL_VERSION = "1"             # version string your gateway accepts

data = fetch_california_housing(as_frame=True)
row = data.frame.iloc[0]
features = row.drop("MedHouseVal").to_dict()

payload = json.dumps({"features": features}).encode("utf-8")
req = urllib.request.Request(
    f"{BASE}/{MODEL_NAME}/version/{MODEL_VERSION}/predict",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    print(resp.status, resp.read().decode())