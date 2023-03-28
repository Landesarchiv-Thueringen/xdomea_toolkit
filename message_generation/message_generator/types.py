from dataclasses import dataclass
from enum import Enum


@dataclass
class XdomeaRegexConfig:
    xdomea_0501_message_name: str
    xdomea_0503_message_name: str


class XdomeaEvaluation(str, Enum):
    ARCHIVE = 'A'
    DISCARD = 'V'
