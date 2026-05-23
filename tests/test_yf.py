import yfinance as yf
import pandas as pd

def test():
    symbol = "AAPL"
    t = yf.Ticker(symbol)
    
    print("\n--- Income Stmt Index ---")
    try:
        inc = t.quarterly_income_stmt
        print(inc.index.tolist())
        print("\nColumns (Dates):", inc.columns.tolist())
        
        # Check for Total Revenue
        if "Total Revenue" in inc.index:
            print("Total Revenue row:")
            print(inc.loc["Total Revenue"])
        else:
            # Let's find anything matching "revenue"
            rev_matches = [x for x in inc.index if "revenue" in x.lower()]
            print("Revenue matches:", rev_matches)

        # Check for EPS or Net Income
        eps_matches = [x for x in inc.index if "eps" in x.lower() or "earnings" in x.lower() or "diluted" in x.lower()]
        print("EPS/Earnings/Diluted matches in index:", eps_matches)
        for m in eps_matches:
            print(f"\n{m}:")
            print(inc.loc[m])
            
    except Exception as e:
        print("Error getting quarterly_income_stmt:", e)

if __name__ == "__main__":
    test()
