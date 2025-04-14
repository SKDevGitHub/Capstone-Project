# Downloading data of confirmed Pump-and-Dumps

1. Put Coin Ticker, Group Pumping, Date of Pump (Y-M-D), Time of Pump (Hr:Min), Exchange that hosts coin of confirmed pumps into pump_telegram.csv
2. Run downloader.py. Command Line arguments; Exchange, Days before pump (optional, default=7), Days after pump (optional, default=7) 
    - Note: Can only download from one exchange at time
    - Note: Generates .csv files of data for each confirmed pump

# TODO

- Add more exchanges (currently works for binance, kucoin, and coinbase)
- Gather confirm Pumps from telegram channels

# Once we're confident we've found enough data

- Use data to train model from papers