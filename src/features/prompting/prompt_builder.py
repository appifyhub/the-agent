import enum

SECTION_BODY_DIVIDER = "\n"
SECTIONS_DIVIDER = "\n\n"


class PromptSection(enum.Enum):
    style = "Style"
    format = "Format"
    context = "Context"
    tone = "Tone"
    quirks = "Quirks"
    appendix = "Appendix"
    reminder = "Important Reminder"
    meta = "Metadata"


class PromptBuilder:
    __prompt: str

    def __init__(self, initial: str = ""):
        self.__prompt = initial

    def add_section(self, section: PromptSection, content: str) -> "PromptBuilder":
        section_body = f"[{section.value}]{SECTION_BODY_DIVIDER}{content}"
        new_prompt = f"{self.__prompt}{SECTIONS_DIVIDER}{section_body}".strip()
        return PromptBuilder(new_prompt)

    def append(self, builder: "PromptBuilder") -> "PromptBuilder":
        appendix = builder.build()
        new_prompt = f"{self.__prompt}{SECTIONS_DIVIDER}{appendix}".strip()
        return PromptBuilder(new_prompt)

    def build(self) -> str:
        return self.__prompt
