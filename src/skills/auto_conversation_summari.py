import logging
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer
from src.core.database import Database
from src.core.nlp import NLP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def conversation_summarizer(conversation_history):
    """
    This module analyzes the conversation history stored in the database, 
    identifies key points and topics, and generates a brief summary that can be 
    displayed to the user.

    Args:
        conversation_history (list): A list of strings representing the conversation history.

    Returns:
        str: A brief summary of the conversation.

    Raises:
        Exception: If an error occurs during the summarization process.
    """
    try:
        # Initialize the NLP object
        nlp = NLP()

        # Initialize the lemmatizer
        lemmatizer = WordNetLemmatizer()

        # Initialize the stopwords
        stop_words = set(stopwords.words('english'))

        # Tokenize the conversation history into sentences
        sentences = sent_tokenize(' '.join(conversation_history))

        # Initialize a dictionary to store the word frequencies
        word_freq = {}

        # Iterate over each sentence
        for sentence in sentences:
            # Tokenize the sentence into words
            words = word_tokenize(sentence)

            # Iterate over each word
            for word in words:
                # Lemmatize the word
                word = lemmatizer.lemmatize(word.lower())

                # Check if the word is not a stopword
                if word not in stop_words:
                    # Increment the word frequency
                    if word in word_freq:
                        word_freq[word] += 1
                    else:
                        word_freq[word] = 1

        # Sort the word frequencies in descending order
        sorted_word_freq = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        # Initialize the summary
        summary = ''

        # Iterate over the top 10 word frequencies
        for word, freq in sorted_word_freq[:10]:
            # Append the word to the summary
            summary += word + ' '

        # Return the summary
        return summary.strip()

    except Exception as e:
        # Log the error
        logger.error(f'An error occurred during the summarization process: {str(e)}')
        return None

def __main__():
    # Initialize the database
    db = Database()

    # Retrieve the conversation history from the database
    conversation_history = db.get_conversation_history()

    # Generate the summary
    summary = conversation_summarizer(conversation_history)

    # Print the summary
    print(summary)

if __name__ == '__main__':
    __main__()