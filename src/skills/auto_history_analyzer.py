import logging
import matplotlib.pyplot as plt
from collections import Counter
from datetime import datetime
from typing import Dict, List
import seaborn as sns
import pandas as pd
from aisha_brain import get_user_history

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HistoryAnalyzer:
    """
    The HistoryAnalyzer class is designed to process user history data from the aisha_brain module.
    It calculates metrics such as average conversation length, most common user inputs, and conversation trends over time.
    The class provides a simple API for retrieving these metrics, allowing for easy integration with existing functionality.
    It also includes data visualization capabilities to help illustrate the insights and statistics it provides.

    Attributes:
        user_history (List[Dict]): A list of dictionaries containing user conversation history.
        conversation_lengths (List[int]): A list of conversation lengths.
        most_common_inputs (List[str]): A list of the most common user inputs.
        conversation_trends (Dict[str, int]): A dictionary of conversation trends over time.

    Methods:
        calculate_metrics: Calculates the average conversation length, most common user inputs, and conversation trends.
        visualize_data: Generates informative and engaging plots to illustrate the insights and statistics.
    """

    def __init__(self, user_history: List[Dict]):
        self.user_history = user_history
        self.conversation_lengths = []
        self.most_common_inputs = []
        self.conversation_trends = {}

    def calculate_metrics(self):
        try:
            for conversation in self.user_history:
                conversation_length = len(conversation['inputs'])
                self.conversation_lengths.append(conversation_length)
                for input in conversation['inputs']:
                    self.most_common_inputs.append(input)
                conversation_date = conversation['date']
                if conversation_date in self.conversation_trends:
                    self.conversation_trends[conversation_date] += 1
                else:
                    self.conversation_trends[conversation_date] = 1
            average_conversation_length = sum(self.conversation_lengths) / len(self.conversation_lengths)
            most_common_inputs = Counter(self.most_common_inputs).most_common(10)
            logging.info(f'Average conversation length: {average_conversation_length}')
            logging.info(f'Most common user inputs: {most_common_inputs}')
            logging.info(f'Conversation trends: {self.conversation_trends}')
            return average_conversation_length, most_common_inputs, self.conversation_trends
        except Exception as e:
            logging.error(f'Error calculating metrics: {e}')

    def visualize_data(self):
        try:
            plt.figure(figsize=(10, 6))
            sns.set_style('whitegrid')
            sns.lineplot(x=list(self.conversation_trends.keys()), y=list(self.conversation_trends.values()))
            plt.title('Conversation Trends Over Time')
            plt.xlabel('Date')
            plt.ylabel('Number of Conversations')
            plt.show()
            plt.figure(figsize=(10, 6))
            sns.set_style('whitegrid')
            sns.histplot(self.conversation_lengths, bins=10)
            plt.title('Conversation Length Distribution')
            plt.xlabel('Conversation Length')
            plt.ylabel('Frequency')
            plt.show()
        except Exception as e:
            logging.error(f'Error visualizing data: {e}')

def main():
    user_history = get_user_history()
    analyzer = HistoryAnalyzer(user_history)
    average_conversation_length, most_common_inputs, conversation_trends = analyzer.calculate_metrics()
    analyzer.visualize_data()

if __name__ == '__main__':
    main()