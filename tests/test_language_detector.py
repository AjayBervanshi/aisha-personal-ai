import unittest
from src.core.language_detector import detect_language

class TestLanguageDetector(unittest.TestCase):
    def test_empty_string(self):
        lang, conf = detect_language("")
        self.assertEqual(lang, "English")
        self.assertEqual(conf, 1.0)

    def test_whitespace_only(self):
        lang, conf = detect_language("   \n\t  ")
        self.assertEqual(lang, "English")
        self.assertEqual(conf, 1.0)

    def test_mixed_script_hindi(self):
        # Mixed Hindi (Devanagari) and English words
        lang, conf = detect_language("मैं बहुत खुश हूं today")
        self.assertEqual(lang, "Hindi")
        self.assertGreater(conf, 0.5)

    def test_mixed_script_marathi(self):
        # Mixed Marathi (Devanagari) and English
        lang, conf = detect_language("मी आज खूप खुश आहे for this")
        self.assertEqual(lang, "Marathi")
        self.assertGreater(conf, 0.5)

    def test_numbers_only(self):
        lang, conf = detect_language("12345 67890")
        self.assertEqual(lang, "English")
        self.assertEqual(conf, 0.9)

    def test_hinglish(self):
        lang, conf = detect_language("bhai ye kya ho raha hai")
        self.assertEqual(lang, "Hinglish")
        self.assertGreater(conf, 0.5)

    def test_marathi_specific(self):
        lang, conf = detect_language("तुझं नाव काय आहे")
        self.assertEqual(lang, "Marathi")
        self.assertGreater(conf, 0.5)

if __name__ == '__main__':
    unittest.main()
