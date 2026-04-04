import logging
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.sentiment import SentimentIntensityAnalyzer
from collections import defaultdict
from string import punctuation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def conversation_summarizer(conversation_history, max_summary_length=50):
    """
    This module utilizes natural language processing techniques to analyze conversation histories 
    and produce summaries that capture key points and main ideas.

    Args:
        conversation_history (list): A list of strings representing the conversation history.
        max_summary_length (int): The maximum number of words in the summary.

    Returns:
        str: A summary of the conversation.

    Raises:
        ValueError: If the conversation history is empty.
        TypeError: If the conversation history is not a list.
    """
    if not conversation_history:
        logger.error("Conversation history is empty")
        raise ValueError("Conversation history is empty")
    if not isinstance(conversation_history, list):
        logger.error("Conversation history must be a list")
        raise TypeError("Conversation history must be a list")

    try:
        # Initialize the lemmatizer and sentiment analyzer
        lemmatizer = WordNetLemmatizer()
        sia = SentimentIntensityAnalyzer()

        # Initialize the stop words
        stop_words = set(stopwords.words('english') + list(punctuation))

        # Tokenize the conversation history
        tokens = [word_tokenize(sentence) for sentence in conversation_history]

        # Remove stop words and lemmatize the tokens
        filtered_tokens = [[lemmatizer.lemmatize(word.lower()) for word in sentence if word.lower() not in stop_words] for sentence in tokens]

        # Calculate the sentiment scores for each sentence
        sentiment_scores = [sia.polarity_scores(sentence) for sentence in conversation_history]

        # Calculate the keyword frequencies
        keyword_freq = defaultdict(int)
        for sentence in filtered_tokens:
            for word in sentence:
                keyword_freq[word] += 1

        # Rank the sentences based on keyword frequency and sentiment score
        ranked_sentences = []
        for i, sentence in enumerate(conversation_history):
            keyword_score = sum(keyword_freq[word] for word in filtered_tokens[i])
            sentiment_score = sentiment_scores[i]['compound']
            ranked_sentences.append((sentence, keyword_score + sentiment_score))

        # Sort the ranked sentences
        ranked_sentences.sort(key=lambda x: x[1], reverse=True)

        # Generate the summary
        summary = []
        for sentence, _ in ranked_sentences:
            if len(' '.join(summary)) + len(sentence) <= max_summary_length:
                summary.append(sentence)

        return ' '.join(summary)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

def main():
    conversation_history = [
        "Hello, how are you?",
        "I'm good, thanks. How about you?",
        "I'm good too. What's up?",
        "Not much, just got back from a trip.",
        "That sounds fun. Where did you go?",
        "I went to the beach. It was really nice.",
        "I'm jealous. I've been wanting to go to the beach.",
        "You should go. It's really relaxing."
    ]
    print(conversation_summarizer(conversation_history))

if __name__ == "__main__":
    main()