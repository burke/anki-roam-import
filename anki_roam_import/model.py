from dataclasses import dataclass
from typing import Any, List, Optional, Union

# PyCharm doesn't infer well with:
# JsonData = Union[None, bool, str, float, int, List['JsonData'], Dict[str, 'JsonData']]
JsonData = Any


@dataclass
class RoamBlock:
    parts: List['RoamPart']
    source: str
    uid: str
    page_id: str
    page_title: str
    created: str
    updated: str


RoamPart = Union[
    str,
    'Cloze',
    'Math',
    'CodeBlock',
    'CodeInline',
    'RoamColonCommand',
    'RoamCurlyCommand',
]


@dataclass
class Cloze:
    parts: List['ClozePart']
    hint: Optional[str] = None
    number: Optional[int] = None


ClozePart = Union[str, 'Math', 'CodeBlock', 'CodeInline']


@dataclass
class Math:
    content: str


@dataclass
class CodeBlock:
    content: str


@dataclass
class CodeInline:
    content: str


@dataclass
class RoamColonCommand:
    command: str
    content: str


@dataclass
class RoamCurlyCommand:
    content: str


@dataclass
class AnkiNote:
    text: str
    roam_text: str
    roam_source: str
    roam_graph: str
    roam_page_title: str
    roam_page_id: str
    roam_block_id: str
    roam_block_created: str
    roam_block_updated: str
