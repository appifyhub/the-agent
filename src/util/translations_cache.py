from typing import Dict

DEFAULT_LANGUAGE = "English"
DEFAULT_ISO_CODE = "en"


class TranslationsCache:
    __cache: Dict[str, str]

    def __init__(self):
        self.__cache = {}

    def save(self, value: str, language_name: str | None = None, language_iso_code: str | None = None) -> str:
        if language_name:
            self.__cache[language_name.upper()] = value
        if language_iso_code:
            self.__cache[language_iso_code.upper()] = value
        if language_name and language_iso_code:
            self.__cache[self.__key_of(language_name, language_iso_code)] = value
        if not language_name and not language_iso_code:
            self.__cache[DEFAULT_LANGUAGE.upper()] = value
            self.__cache[DEFAULT_ISO_CODE.upper()] = value
            self.__cache[self.__key_of(DEFAULT_LANGUAGE, DEFAULT_ISO_CODE)] = value
        return value

    def get(self, language_name: str | None = None, language_iso_code: str | None = None) -> str | None:
        if language_name and language_iso_code:
            return (
                self.__cache.get(self.__key_of(language_name, language_iso_code))
                or self.__cache.get(language_name.upper())
                or self.__cache.get(language_iso_code.upper())
            )
        if language_name:
            return self.__cache.get(language_name.upper())
        if language_iso_code:
            return self.__cache.get(language_iso_code.upper())
        return (
            self.__cache.get(self.__key_of(DEFAULT_LANGUAGE, DEFAULT_ISO_CODE))
            or self.__cache.get(DEFAULT_LANGUAGE.upper())
            or self.__cache.get(DEFAULT_ISO_CODE.upper())
        )

    @staticmethod
    def __key_of(language_name: str, language_iso_code: str) -> str:
        return f"{language_iso_code.upper()}/{language_name.upper()}"
