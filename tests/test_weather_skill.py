import unittest
from unittest.mock import patch, MagicMock
import requests

from src.skills.weather_skill import get_weather

class TestWeatherSkill(unittest.TestCase):
    @patch('src.skills.weather_skill.requests.get')
    def test_get_weather_success(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.text = "London: ⛅️ +15°C"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        result = get_weather("London")

        # Assert
        mock_get.assert_called_once_with("https://wttr.in/London?format=3", timeout=5)
        self.assertEqual(result, "London: ⛅️ +15°C")

    @patch('src.skills.weather_skill.requests.get')
    def test_get_weather_with_spaces(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.text = "New York: 🌧️ +10°C"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        result = get_weather("New York")

        # Assert
        mock_get.assert_called_once_with("https://wttr.in/New+York?format=3", timeout=5)
        self.assertEqual(result, "New York: 🌧️ +10°C")

    @patch('src.skills.weather_skill.requests.get')
    def test_get_weather_network_error(self, mock_get):
        # Arrange
        mock_get.side_effect = requests.exceptions.RequestException("Connection refused")

        # Act
        result = get_weather("Tokyo")

        # Assert
        mock_get.assert_called_once_with("https://wttr.in/Tokyo?format=3", timeout=5)
        self.assertTrue("Sorry Aju, I couldn't check the weather for Tokyo right now!" in result)
        self.assertTrue("Connection refused" in result)

if __name__ == '__main__':
    unittest.main()
