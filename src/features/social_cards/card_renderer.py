import resvg_py

from features.social_cards.card_layout import card_width_from_text
from features.social_cards.card_template import build_svg
from features.social_cards.theme import ThemeColors
from features.web_browsing.twitter_status_fetcher import TweetData
from util.config import config


def render(
    tweet: TweetData,
    theme: ThemeColors,
    profile_bytes: bytes | None = None,
    media_bytes: list[bytes] | None = None,
    short_url: str | None = None,
) -> bytes:
    media = media_bytes or []
    card_width = card_width_from_text(tweet.text)
    svg = build_svg(
        tweet = tweet,
        theme = theme,
        card_width = card_width,
        profile_bytes = profile_bytes,
        media_bytes = media,
        short_url = short_url,
    )
    return resvg_py.svg_to_bytes(
        svg_string = svg,
        font_files = [config.font_path],
        skip_system_fonts = True,
    )
