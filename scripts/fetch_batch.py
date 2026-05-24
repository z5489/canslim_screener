import yfinance as yf
import pandas as pd
import numpy as np
import json
import argparse
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import time
import random

def safe_float(val):
    if val is None or pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def safe_bool(val):
    if val is None or pd.isna(val):
        return None
    return bool(val)

def evaluate_criteria(symbol, max_retries=3):
    for attempt in range(max_retries):
        try:
            t = yf.Ticker(symbol)
            info = t.info
            hist = t.history(period="3mo")
            inc = t.quarterly_income_stmt
            
            # Determine current price with fallbacks
            price = safe_float(info.get('currentPrice'))
            if price is None:
                price = safe_float(info.get('regularMarketPrice'))
            if price is None and not hist.empty:
                price = safe_float(hist['Close'].iloc[-1])
                
            if price is None:
                raise ValueError("No price data available")
    
            # C1: Price vs 52W Low (Current price >= 52W low * 1.70)
            low_52w = safe_float(info.get('fiftyTwoWeekLow'))
            c1_passes = None
            c1_value = "N/A"
            if low_52w is not None and low_52w > 0:
                c1_ratio = (price / low_52w) - 1
                c1_passes = c1_ratio >= 0.70
                c1_value = f"+{c1_ratio * 100:.1f}%"
    
            # C2: Market Cap >= $300M
            mcap = safe_float(info.get('marketCap'))
            c2_passes = None
            c2_value = "N/A"
            if mcap is not None:
                c2_passes = mcap >= 300_000_000
                c2_value = f"${mcap / 1e6:.1f}M"
    
            # C3: EPS Growth YoY > 25% (using Diluted EPS from quarterly income statement)
            c3_passes = None
            c3_value = "N/A"
            if inc is not None and not inc.empty and 'Diluted EPS' in inc.index:
                inc_sorted = inc.sort_index(axis=1, ascending=False)
                if len(inc_sorted.columns) >= 5:
                    eps_curr = safe_float(inc_sorted.loc['Diluted EPS'].iloc[0])
                    eps_prev = safe_float(inc_sorted.loc['Diluted EPS'].iloc[4])
                    if eps_curr is not None and eps_prev is not None and eps_prev != 0:
                        eps_growth = (eps_curr - eps_prev) / abs(eps_prev)
                        c3_passes = eps_growth > 0.25
                        c3_value = f"+{eps_growth * 100:.1f}%"
    
            # C4: Avg Volume 60D > 500K
            avg_vol = safe_float(info.get('averageVolume'))
            if avg_vol is None and not hist.empty:
                avg_vol = safe_float(hist['Volume'].tail(60).mean())
            c4_passes = None
            c4_value = "N/A"
            if avg_vol is not None:
                c4_passes = avg_vol > 500_000
                c4_value = f"{avg_vol / 1e3:.1f}K"
    
            # C5: Price vs SMA 50 (Current price >= SMA 50)
            c5_passes = None
            c5_value = "N/A"
            if not hist.empty and len(hist) >= 50:
                closes = hist['Close'].tail(50)
                sma50 = safe_float(closes.mean())
                if sma50 is not None:
                    c5_passes = price >= sma50
                    c5_value = f"${price:.2f} / SMA ${sma50:.2f}"
            elif not hist.empty:
                closes = hist['Close']
                sma = safe_float(closes.mean())
                if sma is not None:
                    c5_passes = price >= sma
                    c5_value = f"${price:.2f} / SMA_short ${sma:.2f}"
    
            # C6: Volatility 1M > 3%
            c6_passes = None
            c6_value = "N/A"
            if not hist.empty:
                bars = hist.tail(21)
                valid_bars = bars[bars['Low'] > 0]
                if len(valid_bars) >= 15:
                    vol_series = (valid_bars['High'] - valid_bars['Low']) / valid_bars['Low'] * 100
                    vol_1m = safe_float(vol_series.mean())
                    if vol_1m is not None:
                        c6_passes = vol_1m > 3.0
                        c6_value = f"{vol_1m:.2f}%"
    
            # C7: Revenue Growth YoY > 25% (using Total Revenue from quarterly income statement)
            c7_passes = None
            c7_value = "N/A"
            if inc is not None and not inc.empty and 'Total Revenue' in inc.index:
                inc_sorted = inc.sort_index(axis=1, ascending=False)
                if len(inc_sorted.columns) >= 5:
                    rev_curr = safe_float(inc_sorted.loc['Total Revenue'].iloc[0])
                    rev_prev = safe_float(inc_sorted.loc['Total Revenue'].iloc[4])
                    if rev_curr is not None and rev_prev is not None and rev_prev != 0:
                        rev_growth = (rev_curr - rev_prev) / abs(rev_prev)
                        c7_passes = rev_growth > 0.25
                        c7_value = f"+{rev_growth * 100:.1f}%"
    
            # C8: Float <= 150M shares
            float_shares = safe_float(info.get('floatShares'))
            c8_passes = None
            c8_value = "N/A"
            if float_shares is not None:
                c8_passes = float_shares <= 150_000_000
                c8_value = f"{float_shares / 1e6:.1f}M"
    
            # C9: US Market (Exchange in NMS, NYQ, NGM, NCM, ASE, PCX)
            exchange = info.get('exchange')
            c9_passes = None
            c9_value = "Unknown"
            if exchange is not None:
                c9_passes = exchange in {'NMS', 'NYQ', 'NGM', 'NCM', 'ASE', 'PCX'}
                c9_value = exchange
    
            # Evaluate passes_all
            passes_list = [c1_passes, c2_passes, c3_passes, c4_passes, c5_passes, c6_passes, c7_passes, c8_passes, c9_passes]
            passes_all = all(p is True for p in passes_list)
    
            return {
                "ticker": symbol,
                "name": info.get('longName', symbol),
                "price": price,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "c1_price_vs_52w_low_passes": safe_bool(c1_passes),
                "c1_price_vs_52w_low_value": c1_value,
                "c2_market_cap_passes": safe_bool(c2_passes),
                "c2_market_cap_value": c2_value,
                "c3_eps_growth_passes": safe_bool(c3_passes),
                "c3_eps_growth_value": c3_value,
                "c4_avg_volume_passes": safe_bool(c4_passes),
                "c4_avg_volume_value": c4_value,
                "c5_price_vs_sma50_passes": safe_bool(c5_passes),
                "c5_price_vs_sma50_value": c5_value,
                "c6_volatility_1m_passes": safe_bool(c6_passes),
                "c6_volatility_1m_value": c6_value,
                "c7_revenue_growth_passes": safe_bool(c7_passes),
                "c7_revenue_growth_value": c7_value,
                "c8_float_passes": safe_bool(c8_passes),
                "c8_float_value": c8_value,
                "c9_us_market_passes": safe_bool(c9_passes),
                "c9_us_market_value": c9_value,
                "passes_all": passes_all,
                "error": ""
            }
        except Exception as e:
            error_msg = str(e).lower()
            if attempt < max_retries - 1 and ("too many requests" in error_msg or "rate limit" in error_msg or "429" in error_msg):
                sleep_time = 90 + random.uniform(1, 5)
                print(f"Rate limited on {symbol}. Retrying in {sleep_time:.1f}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(sleep_time)
                continue
    
            return {
                "ticker": symbol,
                "name": symbol,
                "price": None,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "c1_price_vs_52w_low_passes": False,
                "c1_price_vs_52w_low_value": "N/A",
                "c2_market_cap_passes": False,
                "c2_market_cap_value": "N/A",
                "c3_eps_growth_passes": False,
                "c3_eps_growth_value": "N/A",
                "c4_avg_volume_passes": False,
                "c4_avg_volume_value": "N/A",
                "c5_price_vs_sma50_passes": False,
                "c5_price_vs_sma50_value": "N/A",
                "c6_volatility_1m_passes": False,
                "c6_volatility_1m_value": "N/A",
                "c7_revenue_growth_passes": False,
                "c7_revenue_growth_value": "N/A",
                "c8_float_passes": False,
                "c8_float_value": "N/A",
                "c9_us_market_passes": False,
                "c9_us_market_value": "Unknown",
                "passes_all": False,
                "error": str(e)
            }

def run(batch_num, output_path):
    master_path = "data/master.csv"
    if not os.path.exists(master_path):
        raise FileNotFoundError(f"Missing watchlist at {master_path}")
        
    master = pd.read_csv(master_path)
    tickers = master["Ticker"].dropna().unique().tolist()
    
    # Filter out tickers containing a slash (e.g. preferred shares)
    tickers = [t for t in tickers if '/' not in str(t)]
    
    # Round-robin split: batch_num is 1-indexed (1 to 6)
    batches = [tickers[i::6] for i in range(6)]
    batch_tickers = batches[batch_num - 1]
    
    print(f"Starting fetch for Batch {batch_num} ({len(batch_tickers)} tickers)...")
    
    # Run fetch in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(evaluate_criteria, batch_tickers))
        
    # Ensure parent directories exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"Batch {batch_num} fetched successfully. Output written to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch Momentum Stock criteria for a batch of tickers")
    parser.add_argument("--batch", type=int, required=True, help="Batch index (1-6)")
    parser.add_argument("--output", type=str, required=True, help="Output path for batch JSON")
    args = parser.parse_args()
    
    if args.batch < 1 or args.batch > 6:
        raise ValueError("Batch must be between 1 and 6 inclusive")
        
    run(args.batch, args.output)
