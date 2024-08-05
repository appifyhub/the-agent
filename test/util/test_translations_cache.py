import unittest

from util.translations_cache import TranslationsCache, DEFAULT_LANGUAGE, DEFAULT_ISO_CODE


class TranslationsCacheTest(unittest.TestCase):
    cache: TranslationsCache

    def setUp(self):
        self.cache = TranslationsCache()

    def test_save_and_get_with_language_name(self):
        self.assertEqual(self.cache.save("Hello", "English"), "Hello")
        self.assertEqual(self.cache.get("English"), "Hello")
        self.assertEqual(self.cache.get("ENGLISH"), "Hello")

    def test_save_and_get_with_iso_code(self):
        self.assertEqual(self.cache.save("Bonjour", language_iso_code = "FR"), "Bonjour")
        self.assertEqual(self.cache.get(language_iso_code = "FR"), "Bonjour")
        self.assertEqual(self.cache.get(language_iso_code = "fr"), "Bonjour")

    def test_save_and_get_with_both(self):
        self.assertEqual(self.cache.save("Hola", "Spanish", "ES"), "Hola")
        self.assertEqual(self.cache.get("Spanish", "ES"), "Hola")
        self.assertEqual(self.cache.get("SPANISH", "es"), "Hola")

    def test_save_and_get_default(self):
        self.assertEqual(self.cache.save("Hi"), "Hi")
        self.assertEqual(self.cache.get(), "Hi")
        self.assertEqual(self.cache.get(DEFAULT_LANGUAGE), "Hi")
        self.assertEqual(self.cache.get(language_iso_code = DEFAULT_ISO_CODE), "Hi")

    def test_get_nonexistent(self):
        self.assertIsNone(self.cache.get("German"))
        self.assertIsNone(self.cache.get(language_iso_code = "DE"))

    def test_get_priority(self):
        self.cache.save("Hello", "English", "EN")
        self.cache.save("Hi", "English")
        self.cache.save("Howdy", language_iso_code = "EN")
        self.assertEqual(self.cache.get("English", "EN"), "Hello")
        self.assertEqual(self.cache.get("English"), "Hi")
        self.assertEqual(self.cache.get(language_iso_code = "EN"), "Howdy")

    def test_multiple_instances(self):
        cache1 = TranslationsCache()
        cache2 = TranslationsCache()
        cache1.save("Hello", "English")
        self.assertIsNone(cache2.get("English"))

    def test_case_insensitivity(self):
        self.cache.save("Hello", "English", "EN")
        self.assertEqual(self.cache.get("ENGLISH", "en"), "Hello")
        self.assertEqual(self.cache.get("english", "EN"), "Hello")

    def test_overwrite(self):
        self.cache.save("Hello", "English")
        self.cache.save("Hi", "English")
        self.assertEqual(self.cache.get("English"), "Hi")

    def test_get_with_partial_match(self):
        self.cache.save("Hola", "Spanish", "ES")
        self.assertEqual(self.cache.get("Spanish"), "Hola")
        self.assertEqual(self.cache.get(language_iso_code = "ES"), "Hola")

    def test_get_default_priority(self):
        self.cache.save("Hello")
        self.cache.save("Hi", DEFAULT_LANGUAGE)
        self.cache.save("Hey", language_iso_code = DEFAULT_ISO_CODE)
        self.assertEqual(self.cache.get(), "Hello")
