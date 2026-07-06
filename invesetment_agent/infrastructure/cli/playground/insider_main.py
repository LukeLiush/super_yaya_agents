import datetime

import pandas as pd
import yfinance as yf
from edgar import Company, set_identity
from edgar.entity import EntityFilings
from edgar.ownership import Form4

ticker = "TSLA"
tsla = yf.Ticker(ticker)

# all insider transactions
insiders = tsla.insider_transactions

# only buys (if available)
# buys = tsla.insider_purchases
# print(buys.columns)
print(insiders.to_string())
print(insiders.columns.tolist())

print("########### insider data  2 ############")
set_identity("user@example.com")
company = Company(ticker)
today = datetime.datetime.today()
# Pull the widest window once (90 days) and bucket in memory
start = (today - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
end = today.strftime("%Y-%m-%d")
filings: EntityFilings = company.get_filings(form="4", filing_date=(start, end))
dataframes = []
for filing in filings:
    f4: Form4 = filing.obj()
    df = f4.to_dataframe()
    dataframes.append(df)
combined_df = pd.concat(dataframes, ignore_index=True)
print(combined_df.to_string())
print(combined_df.columns.tolist())
