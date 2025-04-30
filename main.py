import asyncio
import websockets
import json
import ssl
import certifi
import platform
import os
import pandas as pd
import traceback
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QComboBox, QFileDialog
)
from PyQt5.QtCore import QTimer

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from qasync import QEventLoop

# Windows compatibility
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.figure = Figure(figsize=(8, 4))
        self.ax = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)

    def plot(self, df, coin_name, threshold_multiplier=0.5):
        self.ax.clear()
        self.ax.plot(df['Close'], label=f'{coin_name} Close Price')

        # Calculate price changes
        df['Price_Change'] = df['Close'].diff()

        # Compute mean and standard deviation of price changes
        mean_change = df['Price_Change'].mean()
        std_change = df['Price_Change'].std()

        # Define thresholds
        pump_threshold = mean_change + (threshold_multiplier * std_change)
        dump_threshold = mean_change - (threshold_multiplier * std_change)

        # Identify pumps and dumps
        pumps = df[df['Price_Change'] > pump_threshold]
        dumps = df[df['Price_Change'] < dump_threshold]

        # Plot markers
        self.ax.scatter(pumps.index, pumps['Close'], color='red', marker='v', s=100, label='Dump (Price Drop)')
        self.ax.scatter(dumps.index, dumps['Close'], color='green', marker='^', s=100, label='Pump (Price Spike)')

        self.ax.set_title(f'{coin_name} Closing Price with Significant Pumps & Dumps')
        self.ax.set_xlabel('Date')
        self.ax.set_ylabel('Price')
        self.ax.legend()
        self.ax.grid(True)
        self.draw()


class WebSocketDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pump.fun Real-time + Historical Graphs")
        self.setGeometry(100, 100, 1000, 900)

        self.websocket = None
        self.is_connected = False
        self.connection_task = None
        self.subscribed_tokens = set()
        self.known_coins = {}
        self.searched_symbol = None

        self.csv_data = {}

        # --- LAYOUT SETUP ---
        self.layout = QVBoxLayout(self)

        # Top Section (Real-time Feed + Search)
        self.realtime_label = QLabel("Real-time Feed:")
        self.realtime_text_edit = QTextEdit()
        self.realtime_text_edit.setReadOnly(True)

        self.search_layout = QHBoxLayout()
        self.search_label = QLabel("Search Symbol:")
        self.search_input = QLineEdit()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.handle_search)

        self.search_layout.addWidget(self.search_label)
        self.search_layout.addWidget(self.search_input)
        self.search_layout.addWidget(self.search_button)

        self.search_results_text_edit = QTextEdit()
        self.search_results_text_edit.setReadOnly(True)

        self.layout.addWidget(self.realtime_label)
        self.layout.addWidget(self.realtime_text_edit)
        self.layout.addLayout(self.search_layout)
        self.layout.addWidget(self.search_results_text_edit)

        # Bottom Section (Historical Data)
        self.plot_label = QLabel("Historical Data:")
        self.load_button = QPushButton("Load CSV Folder")
        self.load_button.clicked.connect(self.load_csv_folder)

        self.coin_selector = QComboBox()
        self.coin_selector.currentIndexChanged.connect(self.update_plot)

        self.plot_canvas = PlotCanvas(self)

        self.layout.addWidget(self.plot_label)
        self.layout.addWidget(self.load_button)
        self.layout.addWidget(self.coin_selector)
        self.layout.addWidget(self.plot_canvas)

        # Start WebSocket
        self.connect_websocket()

        # Timer for reconnection
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_connection)
        self.timer.start(5000)

    # WebSocket logic...

    def connect_websocket(self):
        self.connection_task = asyncio.create_task(self.connect_websocket_async())

    async def connect_websocket_async(self):
        uri = "wss://pumpportal.fun/api/data"
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        while True:
            try:
                self.websocket = await websockets.connect(uri, ssl=ssl_context)
                self.is_connected = True
                await self.subscribe_initial()
                async for message in self.websocket:
                    try:
                        message_data = json.loads(message)
                        self.process_realtime_message(message_data)
                    except json.JSONDecodeError:
                        self.realtime_text_edit.append(f"Error decoding JSON: {message}")
            except Exception:
                traceback.print_exc()
            finally:
                self.is_connected = False
                await asyncio.sleep(5)

    async def subscribe_initial(self):
        if self.websocket:
            payloads = [
                {"method": "subscribeNewToken"},
                {"method": "subscribeMigration"}
            ]
            for p in payloads:
                await self.websocket.send(json.dumps(p))

    async def subscribe_token_trade(self, symbol):
        if self.websocket and symbol not in self.subscribed_tokens:
            payload = {"method": "subscribeTokenTrade", "keys": [symbol]}
            await self.websocket.send(json.dumps(payload))
            self.subscribed_tokens.add(symbol)

    async def unsubscribe_token_trade(self, symbol):
        if self.websocket and symbol in self.subscribed_tokens:
            payload = {"method": "unsubscribeTokenTrade", "keys": [symbol]}
            await self.websocket.send(json.dumps(payload))
            self.subscribed_tokens.discard(symbol)

    def process_realtime_message(self, data):
        if "txType" in data and data["txType"] == "create":
            mint = data.get("mint")
            if mint and mint not in self.known_coins:
                self.known_coins[mint] = data

        if all(k in data for k in ["name", "symbol", "solAmount", "marketCapSol", "signature"]):
            name = data["name"]
            symbol = data["symbol"]
            sol_amount = data["solAmount"]
            market_cap_sol = data["marketCapSol"]
            sig = data["signature"]

            formatted = f"Name: {name}\nSymbol: {symbol}\nSOL: {sol_amount:.2f}\nCap: {market_cap_sol:.2f}\nSig: {sig}\n"
            self.realtime_text_edit.append(formatted)

            if self.searched_symbol and symbol.upper() == self.searched_symbol:
                self.display_search_results(data)

    def display_search_results(self, data):
        self.search_results_text_edit.clear()
        if data and "signature" in data and "name" in data and "symbol" in data and "solAmount" in data and "marketCapSol" in data:
            name = data.get("name", "N/A")
            symbol = data.get("symbol", "N/A")
            sol_amount = data.get("solAmount", "N/A")
            market_cap_sol = data.get("marketCapSol", "N/A")
            signature = data.get("signature", "N/A")

            results_text = f"--- Search Results for {symbol.upper()} ---\n"
            results_text += f"Name: {name}\n"
            results_text += f"Symbol: {symbol}\n"
            results_text += f"SOL Amount: {sol_amount:.2f}\n"
            results_text += f"Market Cap (SOL): {market_cap_sol:.2f}\n"
            results_text += f"Signature: {signature}\n\n"
            self.search_results_text_edit.append(results_text)
        else:
            self.search_results_text_edit.append(f"No information found for symbol: {self.search_input.text().upper()}\n")

    async def search_token_data(self, symbol):
        symbol = symbol.upper()
        found_coins = [info for mint, info in self.known_coins.items() if info.get("symbol") == symbol]

        self.search_results_text_edit.clear()
        if found_coins:
            self.search_results_text_edit.append(f"--- Found {len(found_coins)} previously seen coins with symbol {symbol} ---\n")
            for coin in found_coins:
                results_text = f"Name: {coin.get('name', 'N/A')}\n"
                results_text += f"Symbol: {coin.get('symbol', 'N/A')}\n"
                results_text += f"SOL Amount: {coin.get('solAmount', 'N/A'):.2f}\n"
                results_text += f"Market Cap (SOL): {coin.get('marketCapSol', 'N/A'):.2f}\n"
                results_text += f"Signature: {coin.get('signature', 'N/A')}\n\n"
                self.search_results_text_edit.append(results_text)
        else:
            self.search_results_text_edit.append(f"No previously seen coins found with symbol: {symbol}\n")

        await self.unsubscribe_token_trade(symbol)
        await self.subscribe_token_trade(symbol)
        if not found_coins:
            self.search_results_text_edit.append("Waiting for real-time updates for this symbol...\n")
        self.searched_symbol = symbol

    def handle_search(self):
        symbol = self.search_input.text().strip()
        if symbol:
            asyncio.create_task(self.search_token_data(symbol))

    def check_connection(self):
        if not self.websocket or self.websocket.close:
            self.connect_websocket()

    def load_csv_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with CSVs")
        if folder:
            self.csv_data = self.load_and_merge_data(folder)
            self.coin_selector.clear()
            self.coin_selector.addItems(self.csv_data.keys())

    def load_and_merge_data(self, folder_path):
        all_data = {}
        for filename in os.listdir(folder_path):
            if filename.endswith(".csv"):
                try:
                    df = pd.read_csv(os.path.join(folder_path, filename))
                    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
                    df.set_index('Date', inplace=True)
                    df.drop(columns=['Adj Close'], errors='ignore', inplace=True)
                    coin_name = os.path.splitext(filename)[0]
                    all_data[coin_name] = df
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        return all_data

    def update_plot(self):
        coin = self.coin_selector.currentText()
        if coin and coin in self.csv_data:
            self.plot_canvas.plot(self.csv_data[coin], coin)


async def main():
    app = QApplication([])
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = WebSocketDisplay()
    window.show()

    with loop:
        await loop.run_forever()


if __name__ == "__main__":
    asyncio.run(main())