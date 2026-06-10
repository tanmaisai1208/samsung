
df = pd.read_csv(csv_path)

# Clean column names
df.columns = [c.strip() for c in df.columns]

# Use DateTime column
if "DateTime" not in df.columns:
    raise KeyError("DateTime column not found")

df["datetime"] = pd.to_datetime(df["DateTime"], errors="coerce")

# Remove invalid timestamps
df = df.dropna(subset=["datetime"])

# Sort chronologically
df = df.sort_values("datetime")

print(f"Original rows: {len(df)}")

# Set datetime index
df = df.set_index("datetime")

# Create exact 1-hour grid
hourly_df = df.resample("1h").asfreq()

# Interpolate SoC
hourly_df["Soc"] = (
    hourly_df["Soc"]
    .astype(float)
    .interpolate(method="time")
)

print(f"Hourly rows after resampling: {len(hourly_df)}")

# Final series used for ACF and Hurst
soc = hourly_df["Soc"].dropna().values
