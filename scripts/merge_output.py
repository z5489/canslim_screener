import pandas as pd
import json
import os
import argparse
import glob
import re
from datetime import datetime, timezone

def run(batch_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    # Get today's date in YYYY-MM-DD in UTC
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_file = os.path.join(output_dir, f"output_{today}.csv")
    
    print(f"Reading batch data from {batch_path}...")
    with open(batch_path, "r") as f:
        batch_data = json.load(f)
        
    # Convert list of dicts to DataFrame
    batch_df = pd.DataFrame(batch_data)
    
    # Ensure column order aligns with expected schema
    schema_cols = [
        "ticker", "name", "price", "fetched_at",
        "c1_price_vs_52w_low_passes", "c1_price_vs_52w_low_value",
        "c2_market_cap_passes", "c2_market_cap_value",
        "c3_eps_growth_passes", "c3_eps_growth_value",
        "c4_avg_volume_passes", "c4_avg_volume_value",
        "c5_price_vs_sma50_passes", "c5_price_vs_sma50_value",
        "c6_volatility_1m_passes", "c6_volatility_1m_value",
        "c7_revenue_growth_passes", "c7_revenue_growth_value",
        "c8_float_passes", "c8_float_value",
        "c9_us_market_passes", "c9_us_market_value",
        "passes_all", "error"
    ]
    
    # If some columns are missing (e.g. error row), fill them with default None or N/A
    for col in schema_cols:
        if col not in batch_df.columns:
            batch_df[col] = None
            
    # Keep only the schema columns in the specified order
    batch_df = batch_df[schema_cols]
    
    if os.path.exists(out_file):
        print(f"Merging into existing output file: {out_file}...")
        existing_df = pd.read_csv(out_file)
        # Ensure existing DataFrame also has all schema columns
        for col in schema_cols:
            if col not in existing_df.columns:
                existing_df[col] = None
        existing_df = existing_df[schema_cols]
        
        merged_df = pd.concat([existing_df, batch_df], ignore_index=True)
        # Keep the last one for any duplicate ticker (newly fetched data takes precedence)
        merged_df = merged_df.drop_duplicates(subset=["ticker"], keep="last")
    else:
        print(f"Creating new daily output file: {out_file}...")
        merged_df = batch_df
        
    # Sort by ticker for readability
    merged_df = merged_df.sort_values(by="ticker")
    
    # Save back to CSV
    merged_df.to_csv(out_file, index=False)
    print(f"Merged output saved. Row count: {len(merged_df)}")
    
    # Dynamically scan output directory to build manifest.json
    print("Rebuilding manifest.json...")
    csv_pattern = os.path.join(output_dir, "output_*.csv")
    csv_files = glob.glob(csv_pattern)
    
    dates = []
    for filepath in csv_files:
        filename = os.path.basename(filepath)
        match = re.search(r"output_(\d{4}-\d{2}-\d{2})\.csv", filename)
        if match:
            dates.append(match.group(1))
            
    # Sort dates descending (newest first)
    dates = sorted(list(set(dates)), reverse=True)
    
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump({"dates": dates}, f, indent=2)
        
    print(f"Manifest written to {manifest_path} with dates: {dates}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge batch JSON data into daily output CSV")
    parser.add_argument("--batch", type=str, required=True, help="Path to batch JSON file")
    parser.add_argument("--output-dir", type=str, required=True, help="Directory containing daily outputs")
    args = parser.parse_args()
    
    run(args.batch, args.output_dir)
