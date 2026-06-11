dsocdt_series = df_hourly["dSocdt"].values.astype(float)

print(f"  Total hourly rows : {len(df_hourly)}")
print(f"  Samples used      : {len(dsocdt_series)}")

if len(dsocdt_series) < MAX_LAG + 1:
