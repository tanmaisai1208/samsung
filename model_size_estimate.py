# Model size and inference time estimation for XGBoost pipeline
import numpy as np, time, os, pickle
from sklearn.multioutput import MultiOutputRegressor
from xgboost import XGBRegressor

# Hyperparameters as used in final validation
BEST_PARAMS = {
    "n_estimators": 25,
    "max_depth": 2,
    "learning_rate": 0.05,
    "subsample": 0.95,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "verbosity": 0,
}

# Synthetic data generation
# Each training sample uses 14 days * 52 features = 728 features
n_features = 14 * 52
n_samples = 73  # actual number of days from largest wide CSV
X = np.random.randn(n_samples, n_features)
# Target is 24‑hour dSocdt vector per sample
y = np.random.randn(n_samples, 24)

# Train model
model = MultiOutputRegressor(XGBRegressor(**BEST_PARAMS), n_jobs=-1)
model.fit(X, y)

# Serialize model to get size (pickle)
model_path = "model_pickle.bin"
with open(model_path, "wb") as f:
    pickle.dump(model, f)
size_bytes = os.path.getsize(model_path)
size_kb = size_bytes / 1024
size_mb = size_kb / 1024

# Inference timing (single prediction)
X_test = np.random.randn(1, n_features)
start = time.time()
_ = model.predict(X_test)
elapsed = time.time() - start

print(f"Model pickle size: {size_kb:.2f} KB ({size_mb:.3f} MB)")
print(f"Single‑sample inference time: {elapsed*1000:.2f} ms")
