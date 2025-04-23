import asyncio
import websockets
import json
import ssl
import certifi
import platform
import traceback  # For detailed error tracing

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout, QLabel
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtCore import QTimer

from qasync import QEventLoop
from websockets import protocol

# Windows event loop fix
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class WebSocketDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pump.fun Real-time Data")
        self.setGeometry(100, 100, 800, 800)  # Increased height to accommodate search

        self.main_layout = QVBoxLayout()

        # Real-time Data Section
        self.realtime_label = QLabel("Real-time Feed:")
        self.main_layout.addWidget(self.realtime_label)
        self.realtime_text_edit = QTextEdit()
        self.realtime_text_edit.setReadOnly(True)
        self.main_layout.addWidget(self.realtime_text_edit)

        # Search Section
        self.search_group = QWidget()
        self.search_layout = QHBoxLayout()
        self.search_label = QLabel("Search Symbol:")
        self.search_layout.addWidget(self.search_label)
        self.search_input = QLineEdit()
        self.search_layout.addWidget(self.search_input)
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.handle_search)
        self.search_layout.addWidget(self.search_button)
        self.search_group.setLayout(self.search_layout)
        self.main_layout.addWidget(self.search_group)

        # Search Results Section
        self.search_results_label = QLabel("Search Results:")
        self.main_layout.addWidget(self.search_results_label)
        self.search_results_text_edit = QTextEdit()
        self.search_results_text_edit.setReadOnly(True)
        self.main_layout.addWidget(self.search_results_text_edit)

        self.setLayout(self.main_layout)

        self.websocket = None
        self.is_connected = False
        self.connection_task = None
        self.subscribed_tokens = set()  # Keep track of subscribed tokens for search
        self.known_coins = {}  # Key will be the mint address, value will be coin info
        self.searched_symbol = None

        print("WebSocketDisplay initialized. Attempting to connect...")
        self.connect_websocket()

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_connection)
        self.timer.start(5000)
        print("Connection check timer started (every 5 seconds)")

    async def connect_websocket_async(self):
        uri = "wss://pumpportal.fun/api/data"
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        while True:  # Keep trying to connect
            print(f"Attempting to connect to WebSocket URI: {uri}")
            websocket_attempt = None  # Local variable for the current connection attempt
            try:
                print("About to call websockets.connect()")
                websocket_attempt = await websockets.connect(uri, ssl=ssl_context)
                self.websocket = websocket_attempt  # Assign to the class attribute only on success
                print("websockets.connect() call successful.")
                print("WebSocket connection established successfully.")
                self.is_connected = True
                await self.subscribe_initial()  # Subscribe to initial streams
                try:
                    async for message in self.websocket:
                        print("Received message from WebSocket.")
                        try:
                            message_data = json.loads(message)
                            print("Message received and parsed successfully.")
                            self.process_realtime_message(message_data)
                        except json.JSONDecodeError:
                            print(f"Error decoding JSON from message: {message}")
                            self.realtime_text_edit.append(f"Error decoding JSON: {message}")
                except websockets.exceptions.ConnectionClosedOK:
                    print("WebSocket connection closed by the server.")
                    # No break here, we want to reconnect
                except websockets.exceptions.ConnectionClosedError as e:
                    print(f"WebSocket connection closed unexpectedly: {e}")
                    # No break here, we want to reconnect
                except asyncio.CancelledError:
                    print("WebSocket task was cancelled.")
                    break  # Break out of the outer while loop
                except Exception as e:
                    print("An unexpected error occurred while processing messages:")
                    traceback.print_exc()
                    break  # Break out of the outer while loop
            except websockets.exceptions.InvalidStatusCode as e:
                print(f"WebSocket connection failed with status code: {e.status_code}")
            except ConnectionRefusedError as e:
                print(f"Connection refused: {e}")
            except Exception as e:
                print("An unexpected error occurred during initial WebSocket connection:")
                traceback.print_exc()
            finally:
                print("Exiting WebSocket connection attempt (inner loop).")
                self.is_connected = False
                if websocket_attempt:
                    await websocket_attempt.close()
                self.websocket = None
                print("Waiting 5 seconds before attempting reconnection...")
                await asyncio.sleep(5)
                print("Attempting to reconnect...")

    def connect_websocket(self):
        print("Attempting to start WebSocket connection task.")
        self.connection_task = asyncio.create_task(self.connect_websocket_async())
        print("WebSocket connection task started.")

    async def subscribe_initial(self):
        if self.websocket and self.websocket.state == protocol.State.OPEN:
            print("Sending initial subscription payloads to WebSocket...")
            initial_payloads = [
                {"method": "subscribeNewToken"},
                {"method": "subscribeMigration"},
            ]
            for payload in initial_payloads:
                print(f"Sending initial payload: {payload}")
                await self.websocket.send(json.dumps(payload))
        else:
            print("WebSocket is not open, cannot send initial subscription payloads.")

    async def subscribe_token_trade(self, symbol):
        if self.websocket and self.websocket.state == protocol.State.OPEN and symbol not in self.subscribed_tokens:
            payload = {"method": "subscribeTokenTrade", "keys": [symbol]}
            print(f"Sending subscription request for symbol: {symbol}")
            await self.websocket.send(json.dumps(payload))
            self.subscribed_tokens.add(symbol)

    async def unsubscribe_token_trade(self, symbol):
        if self.websocket and self.websocket.state == protocol.State.OPEN and symbol in self.subscribed_tokens:
            payload = {"method": "unsubscribeTokenTrade", "keys": [symbol]}
            print(f"Sending unsubscription request for symbol: {symbol}")
            await self.websocket.send(json.dumps(payload))
            self.subscribed_tokens.discard(symbol)

    def process_realtime_message(self, message_data):
        formatted_text = ""
        if "txType" in message_data and message_data["txType"] == "create":
            mint = message_data.get("mint")
            if mint and mint not in self.known_coins:
                coin_info = {
                    "name": message_data.get("name", "N/A"),
                    "symbol": message_data.get("symbol", "N/A"),
                    "solAmount": message_data.get("solAmount", "N/A"),
                    "marketCapSol": message_data.get("marketCapSol", "N/A"),
                    "signature": message_data.get("signature", "N/A"),
                    # Add other relevant fields
                }
                self.known_coins[mint] = coin_info
                print(f"New coin saved: {coin_info['name']} ({coin_info['symbol']}) - {mint}")

        if "signature" in message_data and "name" in message_data and "symbol" in message_data and "solAmount" in message_data and "marketCapSol" in message_data:
            name = message_data.get("name", "N/A")
            symbol = message_data.get("symbol", "N/A")
            sol_amount = message_data.get("solAmount", "N/A")
            market_cap_sol = message_data.get("marketCapSol", "N/A")
            signature = message_data.get("signature", "N/A")

            formatted_text += f"Name: {name}\n"
            formatted_text += f"Symbol: {symbol}\n"
            formatted_text += f"SOL Amount: {sol_amount:.2f}\n"
            formatted_text += f"Market Cap (SOL): {market_cap_sol:.2f}\n"
            formatted_text += f"Signature: {signature}\n\n"
            self.realtime_text_edit.append(formatted_text)
            if self.searched_symbol and symbol.upper() == self.searched_symbol:
                self.display_search_results(message_data)
        elif "message" in message_data:
            self.realtime_text_edit.append(f"Status: {message_data['message']}\n\n")

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
        symbol = self.search_input.text().strip().upper()
        if symbol:
            print(f"Search initiated for symbol: {symbol}")
            asyncio.create_task(self.search_token_data(symbol))

    def check_connection(self):
        if not self.websocket or self.websocket.state != protocol.State.OPEN:
            print("WebSocket disconnected or not open. Reconnecting...")
            self.is_connected = False
            self.connect_websocket()
        else:
            print("WebSocket is still open.")

    def closeEvent(self, event: QCloseEvent):
        print("Closing PyQt window...")
        if self.websocket and self.websocket.state == protocol.State.OPEN:
            print("Closing WebSocket connection...")
            asyncio.create_task(self.websocket.close())
        event.accept()
        QApplication.quit()

async def main_async():
    print("Starting main event loop...")
    app = QApplication([])
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = WebSocketDisplay()
    window.show()

    with loop:
        await loop.run_forever()

if __name__ == "__main__":
    print("Running the program...")
    asyncio.run(main_async())