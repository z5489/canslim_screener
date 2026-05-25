import yfinance as yf
import pandas as pd
import numpy as np

def evaluate_criteria(symbol):
    try:
        t = yf.Ticker(symbol)
        info = t.info
        hist = t.history(period="3mo")
        inc = t.quarterly_income_stmt
        
        # 1. Price
        price = info.get('currentPrice')
        if price is None:
            price = info.get('regularMarketPrice')
        if price is None and not hist.empty:
            price = hist['Close'].iloc[-1]
            
        if price is None:
            raise ValueError("No price data available")

        # C1: Price vs 52W Low
        low_52w = info.get('fiftyTwoWeekLow')
        c1_passes = None
        c1_value = "N/A"
        if low_52w is not None and low_52w > 0:
            c1_ratio = (price / low_52w) - 1
            c1_passes = c1_ratio >= 0.70
            c1_value = f"+{c1_ratio * 100:.1f}%"

        # C2: Market Cap >= $300M
        mcap = info.get('marketCap')
        c2_passes = None
        c2_value = "N/A"
        if mcap is not None:
            c2_passes = mcap >= 300_000_000
            c2_value = f"${mcap / 1e6:.1f}M"

        # C3: EPS Growth YoY > 25%
        c3_passes = None
        c3_value = "N/A"
        if inc is not None and not inc.empty and 'Diluted EPS' in inc.index:
            inc_sorted = inc.reindex(sorted(inc.columns, reverse=True), axis=1)
            if len(inc_sorted.columns) >= 5:
                eps_curr = inc_sorted.loc['Diluted EPS'].iloc[0]
                eps_prev = inc_sorted.loc['Diluted EPS'].iloc[4]
                if pd.notna(eps_curr) and pd.notna(eps_prev) and eps_prev != 0:
                    eps_growth = (eps_curr - eps_prev) / abs(eps_prev)
                    c3_passes = eps_growth > 0.25
                    c3_value = f"+{eps_growth * 100:.1f}%"

        # C4: Avg Volume 60D > 500K
        avg_vol = info.get('averageVolume')
        if avg_vol is None and not hist.empty:
            avg_vol = hist['Volume'].tail(60).mean()
        c4_passes = None
        c4_value = "N/A"
        if avg_vol is not None:
            c4_passes = avg_vol > 500_000
            c4_value = f"{avg_vol / 1e3:.1f}K"

        # C5: Price vs SMA 50
        c5_passes = None
        c5_value = "N/A"
        if not hist.empty and len(hist) >= 50:
            closes = hist['Close'].tail(50)
            sma50 = closes.mean()
            c5_passes = price >= sma50
            c5_value = f"${price:.2f} / SMA ${sma50:.2f}"
        elif not hist.empty:
            closes = hist['Close']
            sma = closes.mean()
            c5_passes = price >= sma
            c5_value = f"${price:.2f} / SMA_short ${sma:.2f}"

        # C6: Volatility 1M > 3%
        c6_passes = None
        c6_value = "N/A"
        if not hist.empty:
            bars = hist.tail(21)
            valid_bars = bars[bars['Low'] > 0]
            if len(valid_bars) >= 15:
                vol_1m = ((valid_bars['High'] - valid_bars['Low']) / valid_bars['Low'] * 100).mean()
                c6_passes = vol_1m > 3.0
                c6_value = f"{vol_1m:.2f}%"

        # C7: Revenue Growth YoY > 25%
        c7_passes = None
        c7_value = "N/A"
        if inc is not None and not inc.empty and 'Total Revenue' in inc.index:
            inc_sorted = inc.reindex(sorted(inc.columns, reverse=True), axis=1)
            if len(inc_sorted.columns) >= 5:
                rev_curr = inc_sorted.loc['Total Revenue'].iloc[0]
                rev_prev = inc_sorted.loc['Total Revenue'].iloc[4]
                if pd.notna(rev_curr) and pd.notna(rev_prev) and rev_prev != 0:
                    rev_growth = (rev_curr - rev_prev) / abs(rev_prev)
                    c7_passes = rev_growth > 0.25
                    c7_value = f"+{rev_growth * 100:.1f}%"

        # C8: Float <= 150M
        float_shares = info.get('floatShares')
        c8_passes = None
        c8_value = "N/A"
        if float_shares is not None:
            c8_passes = float_shares <= 150_000_000
            c8_value = f"{float_shares / 1e6:.1f}M"

        # C9: US Market
        exchange = info.get('exchange')
        c9_passes = None
        c9_value = "Unknown"
        if exchange is not None:
            c9_passes = exchange in {'NMS', 'NYQ', 'NGM', 'NCM', 'ASE', 'PCX'}
            c9_value = exchange

        # Passes all?
        passes_list = [c1_passes, c2_passes, c3_passes, c4_passes, c5_passes, c6_passes, c7_passes, c8_passes, c9_passes]
        num_false = sum(1 for p in passes_list if p is False)
        num_none = sum(1 for p in passes_list if p is None)
        passes_all = (num_false == 0) and (num_none <= 2)

        return {
            "ticker": symbol,
            "name": info.get('longName', symbol),
            "price": price,
            "c1_price_vs_52w_low_passes": c1_passes,
            "c1_price_vs_52w_low_value": c1_value,
            "c2_market_cap_passes": c2_passes,
            "c2_market_cap_value": c2_value,
            "c3_eps_growth_passes": c3_passes,
            "c3_eps_growth_value": c3_value,
            "c4_avg_volume_passes": c4_passes,
            "c4_avg_volume_value": c4_value,
            "c5_price_vs_sma50_passes": c5_passes,
            "c5_price_vs_sma50_value": c5_value,
            "c6_volatility_1m_passes": c6_passes,
            "c6_volatility_1m_value": c6_value,
            "c7_revenue_growth_passes": c7_passes,
            "c7_revenue_growth_value": c7_value,
            "c8_float_passes": c8_passes,
            "c8_float_value": c8_value,
            "c9_us_market_passes": c9_passes,
            "c9_us_market_value": c9_value,
            "passes_all": passes_all,
            "error": ""
        }
    except Exception as e:
        return {
            "ticker": symbol,
            "name": symbol,
            "price": "N/A",
            "passes_all": False,
            "error": str(e)
        }

if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "TSLA", "INVALID_TICKER_123"]
    for t in tickers:
        print(f"\nEvaluating {t}...")
        res = evaluate_criteria(t)
        import pprint
        pprint.pprint(res)
