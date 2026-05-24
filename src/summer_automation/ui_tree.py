from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .errors import UiElementNotFound


@dataclass(frozen=True)
class Bounds:
    left: int
    top: int
    right: int
    bottom: int

    @classmethod
    def parse(cls, value: str) -> "Bounds":
        match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", value or "")
        if not match:
            raise ValueError(f"Invalid bounds: {value!r}")
        return cls(*(int(part) for part in match.groups()))

    @property
    def center(self) -> tuple[int, int]:
        return ((self.left + self.right) // 2, (self.top + self.bottom) // 2)

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def width(self) -> int:
        return self.right - self.left

    def is_visible(self) -> bool:
        return self.width > 0 and self.height > 0


@dataclass
class UiNode:
    attrs: dict[str, str]
    parent: "UiNode | None" = None
    children: list["UiNode"] = field(default_factory=list)

    @property
    def text(self) -> str:
        return self.attrs.get("text", "")

    @property
    def resource_id(self) -> str:
        return self.attrs.get("resource-id", "")

    @property
    def class_name(self) -> str:
        return self.attrs.get("class", "")

    @property
    def content_desc(self) -> str:
        return self.attrs.get("content-desc", "")

    @property
    def bounds(self) -> Bounds:
        return Bounds.parse(self.attrs.get("bounds", "[0,0][0,0]"))

    @property
    def center(self) -> tuple[int, int]:
        return self.bounds.center

    def attr_bool(self, name: str) -> bool:
        return self.attrs.get(name) == "true"

    @property
    def clickable(self) -> bool:
        return self.attr_bool("clickable")

    @property
    def checked(self) -> bool:
        return self.attr_bool("checked")

    @property
    def focused(self) -> bool:
        return self.attr_bool("focused")

    def walk(self) -> Iterable["UiNode"]:
        yield self
        for child in self.children:
            yield from child.walk()

    def descendants(self) -> list["UiNode"]:
        return [node for child in self.children for node in child.walk()]

    def find_descendant_by_id(self, resource_id: str) -> "UiNode | None":
        for node in self.descendants():
            if node.resource_id == resource_id:
                return node
        return None

    def find_descendants_by_id(self, resource_id: str) -> list["UiNode"]:
        return [node for node in self.descendants() if node.resource_id == resource_id]

    def clickable_ancestor(self) -> "UiNode":
        node: UiNode | None = self
        while node is not None:
            if node.clickable and node.bounds.is_visible():
                return node
            node = node.parent
        return self

    def to_summary(self) -> dict[str, str]:
        return {
            "text": self.text,
            "resource_id": self.resource_id,
            "class_name": self.class_name,
            "bounds": self.attrs.get("bounds", ""),
        }


class UiTree:
    def __init__(self, root: UiNode, raw_xml: str):
        self.root = root
        self.raw_xml = raw_xml

    @classmethod
    def from_xml(cls, xml_text: str) -> "UiTree":
        element = ET.fromstring(xml_text)

        def build(el: ET.Element, parent: UiNode | None = None) -> UiNode:
            node = UiNode(dict(el.attrib), parent=parent)
            node.children = [build(child, parent=node) for child in list(el)]
            return node

        return cls(build(element), xml_text)

    @classmethod
    def from_file(cls, path: str | Path) -> "UiTree":
        text = Path(path).read_text(encoding="utf-8")
        return cls.from_xml(text)

    def walk(self) -> Iterable[UiNode]:
        return self.root.walk()

    def find_all(self, predicate: Callable[[UiNode], bool]) -> list[UiNode]:
        return [node for node in self.walk() if predicate(node)]

    def find_first(self, predicate: Callable[[UiNode], bool]) -> UiNode | None:
        for node in self.walk():
            if predicate(node):
                return node
        return None

    def require_first(self, predicate: Callable[[UiNode], bool], description: str) -> UiNode:
        node = self.find_first(predicate)
        if node is None:
            raise UiElementNotFound(description)
        return node

    def find_by_id(self, resource_id: str) -> UiNode | None:
        return self.find_first(lambda node: node.resource_id == resource_id)

    def require_by_id(self, resource_id: str) -> UiNode:
        return self.require_first(
            lambda node: node.resource_id == resource_id,
            f"resource-id={resource_id}",
        )

    def find_all_by_id(self, resource_id: str) -> list[UiNode]:
        return self.find_all(lambda node: node.resource_id == resource_id)

    def find_by_text(self, text: str, *, exact: bool = True) -> UiNode | None:
        if exact:
            return self.find_first(lambda node: node.text == text)
        return self.find_first(lambda node: text in node.text)

    def find_all_by_text(self, text: str, *, exact: bool = True) -> list[UiNode]:
        if exact:
            return self.find_all(lambda node: node.text == text)
        return self.find_all(lambda node: text in node.text)

    def visible_texts(self) -> list[str]:
        return [node.text for node in self.walk() if node.text and node.bounds.is_visible()]
