import pytest
from PyQt5.QtCore import QDateTime, Qt
from jsonchange import MessageProcessor

@pytest.fixture
def processor(qtbot):
    widget = MessageProcessor()
    qtbot.addWidget(widget)
    return widget


def test_parse_message_data_valid(processor):
    msg = {
        "date": "2024-10-10T15:30:00",
        "message": "🔔 CoinA COA | Marketcap: $1.2M | Age: 2 hours\nMarketcap: $1.2M\nAge: 2 hours"
    }

    result = processor.parse_message_data(msg)
    assert result is not None
    datetime_obj, coin, symbol, cap, age = result

    assert isinstance(datetime_obj, QDateTime)
    assert datetime_obj.isValid()
    assert coin == "CoinA"
    assert symbol == "COA"
    assert cap == "$1.2M"
    assert age == "2 hours"


def test_parse_message_data_missing_fields(processor):
    msg = {
        "date": "2024-10-10T15:30:00",
        "message": "No actual coin info here."
    }

    result = processor.parse_message_data(msg)
    assert result is not None
    _, coin, symbol, cap, age = result
    assert coin == "N/A"
    assert symbol == "N/A"
    assert cap == "N/A"
    assert age == "N/A"


def test_parse_message_data_invalid_date(processor):
    msg = {
        "date": "invalid-date-string",
        "message": "🔔 CoinX XYZ | Marketcap: $100K | Age: 5 minutes"
    }

    result = processor.parse_message_data(msg)
    assert result is None  # Should return None for unparseable date


def test_parse_message_data_no_date(processor):
    msg = {
        "message": "🔔 CoinX XYZ | Marketcap: $100K | Age: 5 minutes"
    }

    result = processor.parse_message_data(msg)
    assert result is None


def test_parse_message_data_no_message(processor):
    msg = {
        "date": "2024-10-10T15:30:00"
    }

    result = processor.parse_message_data(msg)
    assert result is None
