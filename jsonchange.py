import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QDate, QDateTime
from PyQt5.QtGui import QFont


class MessageProcessor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram Message Processor")
        self.setGeometry(100, 100, 600, 800)

        self.layout = QVBoxLayout(self)

        self.load_button = QPushButton("Load Telegram JSON File")
        self.load_button.clicked.connect(self.load_and_process_file)
        self.layout.addWidget(self.load_button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QVBoxLayout()
        container = QWidget()
        container.setLayout(self.scroll_content)
        self.scroll_area.setWidget(container)
        self.layout.addWidget(self.scroll_area)

    def parse_message_data(self, msg):
        """Parses a single message to extract date, coin, symbol, cap, and age."""
        if "date" in msg and "message" in msg:
            date_str = msg["date"]
            message_text = msg["message"]
            coin = "N/A"
            symbol = "N/A"
            cap = "N/A"
            age = "N/A"

            if message_text:
                lines = message_text.split('\n')
                for line in lines:
                    if "🔔" in line:
                        parts = line.split("|")
                        if len(parts) > 1:
                            coin_symbol = parts[0].replace("🔔", "").strip()
                            symbol_match = coin_symbol.split()
                            if symbol_match:
                                coin = symbol_match[0].strip()
                                if len(symbol_match) > 1:
                                    symbol = symbol_match[-1].strip()
                                else:
                                    symbol = coin
                    if "Marketcap:" in line:
                        cap = line.split(":")[-1].strip()
                    if "Age:" in line:
                        age = line.split(":")[-1].strip()

            try:
                datetime_obj = QDateTime.fromString(date_str, Qt.ISODate)
                if not datetime_obj.isValid():
                    datetime_obj = QDateTime.fromString(date_str, "yyyy-MM-dd hh:mm:ss")
                if datetime_obj.isValid():
                    return datetime_obj, coin, symbol, cap, age
                else:
                    print(f"Warning: Could not parse date: {date_str}")
                    return None
            except Exception as e:
                print(f"Error parsing date '{date_str}': {e}")
                return None
        return None

    def load_and_process_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open JSON", "", "JSON Files (*.json)")
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            messages = data if isinstance(data, list) else data.get("messages", [])
            processed_messages = []

            for msg in messages:
                print(msg)
                print("===" * 20)
                parsed_data = self.parse_message_data(msg)
                if parsed_data:
                    processed_messages.append(parsed_data)

            # Sort messages by date
            processed_messages.sort(key=lambda item: item[0], reverse = True)

            # Clear old content
            while self.scroll_content.count():
                child = self.scroll_content.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Display processed messages
            font = QFont()
            font.setPointSize(10)
            for date_obj, coin, symbol, cap, age in processed_messages:
                date_str_readable = date_obj.toString("yyyy-MM-dd hh:mm:ss")
                output_text = f"<b>Date:</b> {date_str_readable}<br>"
                output_text += f"<b>Coin:</b> {coin}, <b>Symbol:</b> {symbol}, <b>Cap:</b> {cap}, <b>Age:</b> {age}<br><br>"

                label = QLabel(output_text)
                label.setFont(font)
                label.setWordWrap(True)
                self.scroll_content.addWidget(label)

            # **Crucial Step: Create a container widget and set its layout, then set it as the scroll area's widget**
            container = QWidget()
            container.setLayout(self.scroll_content)
            self.scroll_area.setWidget(container)

            # Optional: Ensure scroll to top after loading new data
            self.scroll_area.verticalScrollBar().setValue(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    processor = MessageProcessor()
    processor.show()
    sys.exit(app.exec_())