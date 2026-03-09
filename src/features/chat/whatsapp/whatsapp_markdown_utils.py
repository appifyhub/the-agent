import re


def convert_for_whatsapp(text: str) -> str:
    """
    Convert standard markdown to WhatsApp markdown format.

    WhatsApp uses single-asterisk bold (*bold*) instead of standard double-asterisk (**bold**).
    Code blocks and inline code are protected to avoid converting their content.
    """
    if not text:
        return text

    CODE_PLACEHOLDER = "\x00CODE{}\x00"
    code_blocks: list[tuple[str, str]] = []

    def protect_code_block(match):
        content = match.group(1)
        idx = len(code_blocks)
        code_blocks.append((content, "```"))
        return CODE_PLACEHOLDER.format(idx)

    def protect_inline_code(match):
        content = match.group(1)
        idx = len(code_blocks)
        code_blocks.append((content, "`"))
        return CODE_PLACEHOLDER.format(idx)

    text = re.sub(r"```(.+?)```", protect_code_block, text, flags = re.DOTALL)
    text = re.sub(r"`([^`\n]+?)`", protect_inline_code, text)

    text = re.sub(r"\*\*([^*\n]+?)\*\*", r"*\1*", text)

    for idx, (content, delimiter) in enumerate(code_blocks):
        text = text.replace(CODE_PLACEHOLDER.format(idx), f"{delimiter}{content}{delimiter}")

    return text
