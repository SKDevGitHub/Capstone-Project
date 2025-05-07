# test_simple_qt.py
from PyQt5.QtWidgets import QApplication, QLabel
import pytest

@pytest.fixture
def app(qtbot):
    app = QApplication([])
    yield app
    app.quit()

def test_simple_label(app, qtbot):
    label = QLabel("Hello")
    assert label.text() == "Hello"