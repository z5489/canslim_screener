import pandas as pd
import os

def split_master():
    csv_path = "data/master.csv"
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} does not exist.")
        return

    master = pd.read_csv(csv_path)
    tickers = master["Ticker"].dropna().unique().tolist()
    
    # Filter out tickers containing a slash
    tickers = [t for t in tickers if '/' not in str(t)]
    print(f"Total tickers in master watchlist: {len(tickers)}")

    # Split round-robin into 6 batches
    batches = [[] for _ in range(6)]
    for idx, ticker in enumerate(tickers):
        batches[idx % 6].append(ticker)

    # Ensure output data directory exists
    os.makedirs("data", exist_ok=True)

    for i, batch in enumerate(batches):
        batch_num = i + 1
        batch_df = pd.DataFrame({"Ticker": batch})
        out_path = f"data/batch_{batch_num}_tickers.csv"
        batch_df.to_csv(out_path, index=False)
        print(f"Batch {batch_num}: {len(batch)} tickers written to {out_path} ({', '.join(batch)})")

if __name__ == "__main__":
    split_master()
