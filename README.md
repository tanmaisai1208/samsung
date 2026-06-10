def main():
    base_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "Downloads",
            "raw"
        )
    )

    print(f"Base dir resolved: {base_dir}")

    csv_files = glob.glob(
        os.path.join(base_dir, "*.csv")
    )

    if not csv_files:
        print("No CSV files found.")
        return

    summary = []

    for csv_path in tqdm(csv_files, desc="Processing CSVs"):

        try:

            acf_img, hurst_img, H = process_file(csv_path)

            summary.append({
                "file": os.path.basename(csv_path),
                "acf": acf_img,
                "hurst": hurst_img,
                "H": H
            })

        except Exception as e:

            print(f"Failed on {csv_path}: {e}")

    print("\nSummary:")

    for item in summary:
        print(
            f"{item['file']} -> H = {item['H']:.4f}"
        )
