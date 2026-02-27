from dataclasses import dataclass
from typing import List

from util.config import ConfiguredProduct


@dataclass(frozen = True)
class ProductsResponse:
    products: List[ConfiguredProduct]
