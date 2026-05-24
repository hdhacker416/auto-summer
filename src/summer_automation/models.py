from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Mapping, Sequence

from .ui_tree import Bounds

if TYPE_CHECKING:
    from .account import SummerAccount


@dataclass
class Message:
    text: str
    direction: str = "unknown"
    timestamp: str | None = None


@dataclass
class Question:
    index: int
    title: str
    kind: str = "essay"
    options: list[str] = field(default_factory=list)


@dataclass
class SendResult:
    target: str
    text: str
    sent: bool
    verified: bool = False
    dry_run: bool = False
    detail: str = ""


@dataclass
class AnswerResult:
    target: str
    answered: bool
    submitted: bool = False
    dry_run: bool = False
    detail: str = ""


@dataclass
class Person:
    nickname: str
    account: "SummerAccount"
    source: str = "unknown"
    row_bounds: Bounds | None = None
    stable_id: str | None = None
    school: str | None = None
    age: str | None = None
    distance: str | None = None
    bio: str | None = None


@dataclass
class Friend(Person):
    def send_message(self, text: str) -> SendResult:
        return self.account.messages.send_message(self, text)

    def read_history(self, limit: int = 50) -> list[Message]:
        return self.account.messages.read_history(self, limit=limit)

    def receive_messages(self, since: str | None = None, limit: int = 50) -> list[Message]:
        return self.account.messages.receive_messages(self, since=since, limit=limit)


@dataclass
class Stranger(Person):
    def get_question(self) -> list[Question]:
        return self.account.strangers.get_questions(self)

    def answer_question(
        self,
        answers: str | Sequence[str] | Mapping[int | str, str],
        *,
        public: bool = False,
        submit: bool = False,
    ) -> AnswerResult:
        return self.account.strangers.answer_question(
            self,
            answers=answers,
            public=public,
            submit=submit,
        )
