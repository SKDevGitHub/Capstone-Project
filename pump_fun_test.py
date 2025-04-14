import asyncio
import websockets
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import ssl
import certifi
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import io

# Global dictionary to store data
data_dict = {}

async def subscribe():
    uri = "wss://pumpportal.fun/api/data"
    ssl_context = ssl.create_default_context(cafile=certifi.where())

    async with websockets.connect(uri, ssl=ssl_context) as websocket:
        print("WebSocket connection established.")
        payloads = [
            {"method": "subscribeNewToken"},
            {"method": "subscribeMigration"},
            {"method": "subscribeAccountTrade", "keys": ["AArPXm8JatJiuyEffuC1un2Sc835SULa4uQqDcaGpAjV"]},
            {"method": "subscribeTokenTrade", "keys": ["91WNez8D22NwBssQbkzjy4s2ipFrzpmn5hfvWVe2aY5p"]},
        ]
        for payload in payloads:
            await websocket.send(json.dumps(payload))
            print(f"Sent payload: {payload}")

        async for message in websocket:
            try:
                message_data = json.loads(message)
                await process_message(message_data)
            except json.JSONDecodeError:
                print(f"Error decoding JSON: {message}")

async def process_message(message_data):
    if 'method' in message_data:
        print(message_data) #print the message.
        if message_data['method'] in ['newToken', 'tokenTrade']:
            trade_data = message_data['data']
            symbol = trade_data.get('symbol', 'Unknown')
            price = trade_data.get('price', 0)
            timestamp = pd.to_datetime(trade_data.get('timestamp', 0), unit='s')

            if symbol not in data_dict:
                data_dict[symbol] = pd.DataFrame(columns=['Close'])
            new_row = pd.DataFrame({'Close': [price]}, index=[timestamp])
            data_dict[symbol] = pd.concat([data_dict[symbol], new_row])
            print(f"{message_data['method']}: {symbol}, price: {price}, time: {timestamp}")

def plot_and_save(symbol):
    if symbol in data_dict:
        df = data_dict[symbol]
        fig, ax = plt.subplots(figsize=(14, 6))

        if not df.empty:
            ax.plot(df['Close'], label=f'{symbol} Close Price')

            df['Price_Change'] = df['Close'].diff()
            mean_change = df['Price_Change'].mean()
            std_change = df['Price_Change'].std()
            pump_threshold = mean_change + (1.5 * std_change)
            dump_threshold = mean_change - (1.5 * std_change)
            pumps = df[df['Price_Change'] > pump_threshold]
            dumps = df[df['Price_Change'] < dump_threshold]

            ax.scatter(pumps.index, pumps['Close'], color='green', marker='^', s=100, label='Pump')
            ax.scatter(dumps.index, dumps['Close'], color='red', marker='v', s=100, label='Dump')

            ax.set_title(f'{symbol} Closing Price')
            ax.set_xlabel('Date')
            ax.set_ylabel('Price')
            ax.legend()
            ax.grid(True)

            # Save the plot to a BytesIO object
            buf = io.BytesIO()
            fig.savefig(buf, format='png')
            buf.seek(0)
            img = Image.open(buf)
            photo = ImageTk.PhotoImage(img)
            return photo
        else:
            return None
    else:
        return None

def search_and_display(symbol):
    photo = plot_and_save(symbol)
    if photo:
        img_label.config(image=photo)
        img_label.image = photo  # Keep a reference!
    else:
        img_label.config(text=f"No data for {symbol}")

async def main():
    global root, img_label
    root = tk.Tk()
    root.title("Pump.fun Graph Viewer")

    search_frame = tk.Frame(root)
    search_frame.pack(pady=10)

    search_label = tk.Label(search_frame, text="Enter Symbol:")
    search_label.pack(side=tk.LEFT)

    search_entry = tk.Entry(search_frame)
    search_entry.pack(side=tk.LEFT)

    search_button = tk.Button(search_frame, text="Search", command=lambda: search_and_display(search_entry.get()))
    search_button.pack(side=tk.LEFT)

    img_label = tk.Label(root)
    img_label.pack()

    asyncio.create_task(subscribe())
    root.mainloop()

if __name__ == "__main__":
    asyncio.run(main())