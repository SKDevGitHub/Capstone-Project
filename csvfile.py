import pandas as pd
import os
import matplotlib.pyplot as plt

def load_and_merge_data(folder_path):
   #Combines the CSV files
    all_data = {}
    for filename in os.listdir(folder_path):
        if filename.endswith(".csv"):
            filepath = os.path.join(folder_path, filename)
            try:
                df = pd.read_csv(filepath)
                df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
                df.set_index('Date', inplace=True)
                df = df.drop(columns=['Adj Close'], errors='ignore')
                coin_name = os.path.splitext(filename)[0]
                all_data[coin_name] = df
            except FileNotFoundError:
                print(f"File not found: {filepath}")
            except pd.errors.ParserError:
                print(f"Error parsing CSV: {filepath}")
            except KeyError as e:
                print(f"KeyError: {e} in {filepath}")
    return all_data

def plot_closing_prices(data_dict):
   #PLOTS PRICES
    for coin_name, df in data_dict.items():
        plt.figure(figsize=(14, 6))
        plt.plot(df['Close'], label=f'{coin_name} Close Price')
        plt.title(f'{coin_name} Closing Price Over Time')
        plt.xlabel('Date')
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)
        plt.show()

folder_path = "/Users/skautt/Desktop/capstone/Capstone-Project/Meme Coin"
coin_data = load_and_merge_data(folder_path)

if coin_data:
    plot_closing_prices(coin_data)
else:
    print("No data loaded.")