# Model size and inference time scaling analysis
import numpy as np, time, os, pickle
import matplotlib.pyplot as plt
from sklearn.multioutput import MultiOutputRegressor
from xgboost import XGBRegressor
from sklearn.metrics import r2_score

# Hyperparameters (same as final validation)
BEST_PARAMS = {
    "n_estimators": 25,
    "max_depth": 2,
    "learning_rate": 0.05,
    "subsample": 0.95,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "verbosity": 0,
}

n_features = 14 * 52  # 728 features per sample

samples_list = list(range(60, 366, 15))  # 60,75,...,365
sizes_kb = []
times_ms = []

for n in samples_list:
    # synthetic data
    X = np.random.randn(n, n_features)
    y = np.random.randn(n, 24)
    model = MultiOutputRegressor(XGBRegressor(**BEST_PARAMS), n_jobs=-1)
    model.fit(X, y)
    # serialize
    model_path = "tmp_model.bin"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    size_bytes = os.path.getsize(model_path)
    sizes_kb.append(size_bytes / 1024)
    # inference timing (single prediction)
    X_test = np.random.randn(1, n_features)
    start = time.time()
    _ = model.predict(X_test)
    elapsed = time.time() - start
    times_ms.append(elapsed * 1000)
    os.remove(model_path)

# Fit polynomial of degree 1,2,3 and pick best by R^2 for size
best_deg = None
best_r2 = -np.inf
best_coef = None
for deg in [1, 2, 3]:
    coeffs = np.polyfit(samples_list, sizes_kb, deg)
    pred = np.polyval(coeffs, samples_list)
    r2 = r2_score(sizes_kb, pred)
    if r2 > best_r2:
        best_r2 = r2
        best_deg = deg
        best_coef = coeffs

# Plot size vs samples with fitted polynomial
plt.figure(figsize=(8,5))
plt.scatter(samples_list, sizes_kb, color="steelblue", label="Measured size (KB)")
# smooth curve for plot
x_smooth = np.linspace(samples_list[0], samples_list[-1], 300)
plt.plot(x_smooth, np.polyval(best_coef, x_smooth), color="crimson", linewidth=2,
         label=f"Best fit degree {best_deg} (R²={best_r2:.3f})")
plt.title("Model size vs number of training samples (synthetic)")
plt.xlabel("Number of samples (days)")
plt.ylabel("Model size (KB)")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.5)
size_plot_path = os.path.join("results", "xgboost", "model_size_vs_samples.png")
plt.tight_layout()
plt.savefig(size_plot_path, dpi=150)
plt.close()

# Also plot inference time (no polynomial fit, just show trend)
plt.figure(figsize=(8,5))
plt.scatter(samples_list, times_ms, color="darkgreen", label="Inference time (ms)")
plt.title("Inference time vs number of training samples (synthetic)")
plt.xlabel("Number of samples (days)")
plt.ylabel("Single‑sample inference time (ms)")
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend()
time_plot_path = os.path.join("results", "xgboost", "inference_time_vs_samples.png")
plt.tight_layout()
plt.savefig(time_plot_path, dpi=150)
plt.close()

print(f"Best polynomial degree for size scaling: {best_deg} (R²={best_r2:.3f})")
print(f"Size plot saved to: {size_plot_path}")
print(f"Inference time plot saved to: {time_plot_path}")
