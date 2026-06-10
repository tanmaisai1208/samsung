def process_file(csv_path: str, max_lag: int = 100):
    df = pd.read_csv(csv_path)

    # Clean column names
    df.columns = [c.strip() for c in df.columns]

    # Use dt column (NOT timestamp)
    if "dt" not in df.columns:
        raise KeyError("dt column not found")

    # Convert dt to datetime
    df["datetime"] = pd.to_datetime(df["dt"], errors="coerce")

    # Remove invalid timestamps
    df = df.dropna(subset=["datetime"])

    # Sort chronologically
    df = df.sort_values("datetime")

    # Set datetime index
    df = df.set_index("datetime")

    # Create regular 1-hour grid
    hourly_df = df.resample("1h").asfreq()

    # Interpolate battery level
    hourly_df["batteryLevel"] = (
        hourly_df["batteryLevel"]
        .astype(float)
        .interpolate(method="time")
    )

    # Fill categorical columns
    if "batteryStatus" in hourly_df.columns:
        hourly_df["batteryStatus"] = hourly_df["batteryStatus"].ffill()

    if "day" in hourly_df.columns:
        hourly_df["day"] = hourly_df["day"].ffill()

    # Use hourly SoC for analysis
    soc = hourly_df["batteryLevel"].dropna().values

    print(f"Original rows: {len(df)}")
    print(f"Hourly rows: {len(hourly_df)}")
