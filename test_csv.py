import pytest
import os
import pandas as pd
from unittest.mock import patch
from csvfile import load_and_merge_data, plot_closing_prices
import matplotlib.pyplot as plt  # needed for mocking plt.show


# === Fixtures ===

@pytest.fixture
def mock_folder_path():
    return "test_folder"

@pytest.fixture
def mock_data():
    return {
        'CoinA': pd.DataFrame({
            'Date': ['2021-01-01', '2021-01-02', '2021-01-03'],
            'Close': [100, 200, 300],
            'Adj Close': [100, 200, 300]
        }),
        'CoinB': pd.DataFrame({
            'Date': ['2021-01-01', '2021-01-02', '2021-01-03'],
            'Close': [50, 150, 250],
            'Adj Close': [50, 150, 250]
        }),
    }


# === Tests ===

def test_load_and_merge_data(mock_folder_path, mock_data):
    with patch("os.listdir") as mock_listdir, patch("pandas.read_csv") as mock_read_csv:
        mock_listdir.return_value = ["CoinA.csv", "CoinB.csv"]

        def read_csv_side_effect(file_path):
            coin_name = os.path.splitext(os.path.basename(file_path))[0]
            df = mock_data[coin_name].copy()
            df['Date'] = pd.to_datetime(df['Date'])
            return df

        mock_read_csv.side_effect = read_csv_side_effect

        result = load_and_merge_data(mock_folder_path)

        assert "CoinA" in result
        assert "CoinB" in result
        assert isinstance(result["CoinA"], pd.DataFrame)
        assert result["CoinA"].shape == (3, 1)  # 'Close' only after drop


def test_load_and_merge_data_no_csv(mock_folder_path):
    with patch("os.listdir") as mock_listdir:
        mock_listdir.return_value = []  # No files
        result = load_and_merge_data(mock_folder_path)
        assert result == {}


def test_load_and_merge_data_file_error(mock_folder_path):
    with patch("os.listdir") as mock_listdir, patch("pandas.read_csv") as mock_read_csv:
        mock_listdir.return_value = ["CoinA.csv"]
        mock_read_csv.side_effect = FileNotFoundError  # Simulate read failure
        result = load_and_merge_data(mock_folder_path)
        assert result == {}


def test_plot_closing_prices(mock_data):
    with patch("matplotlib.pyplot.show") as mock_show:
        plot_closing_prices(mock_data)
        assert mock_show.called
