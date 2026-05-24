from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..constants import Ids
from ..errors import UiElementNotFound
from ..models import AnswerResult, Question


class PaperPage:
    def __init__(self, account):
        self.account = account
        self.device = account.device

    def read_visible_questions(self) -> list[Question]:
        tree = self.device.dump_tree()
        titles = tree.find_all_by_id(Ids.PAPER_TITLE)
        questions: list[Question] = []
        for index, title in enumerate(titles, start=1):
            row_parent = title.parent
            options: list[str] = []
            kind = "essay"
            if row_parent is not None:
                group = row_parent.find_descendant_by_id(Ids.PAPER_CHOICE_GROUP)
                if group is not None:
                    kind = "choice"
                    options = [node.text for node in group.descendants() if "RadioButton" in node.class_name]
            questions.append(Question(index=index, title=title.text, kind=kind, options=options))
        return questions

    def _answer_for(
        self,
        answers: str | Sequence[str] | Mapping[int | str, str],
        question: Question,
        fallback_index: int,
    ) -> str:
        if isinstance(answers, str):
            return answers
        if isinstance(answers, Mapping):
            return answers.get(question.index) or answers.get(question.title) or ""
        if fallback_index < len(answers):
            return str(answers[fallback_index])
        return ""

    def fill_visible_answers(
        self,
        answers: str | Sequence[str] | Mapping[int | str, str],
    ) -> int:
        if not self.device.execute:
            self.device.audit.record("dry_run_fill_answers", answers=answers)
            return 0

        questions = self.read_visible_questions()
        tree = self.device.dump_tree()
        essay_nodes = tree.find_all_by_id(Ids.PAPER_ESSAY)
        filled = 0
        with self.device.adb_keyboard():
            for idx, node in enumerate(essay_nodes):
                question = questions[idx] if idx < len(questions) else Question(idx + 1, "")
                answer = self._answer_for(answers, question, idx)
                if not answer:
                    continue
                self.device.tap(node, description=f"focus answer {idx + 1}")
                self.device.input_text(answer, clear=True, mutating=True)
                filled += 1
        return filled

    def set_public(self, public: bool) -> None:
        tree = self.device.dump_tree()
        switch = tree.find_by_id(Ids.PAPER_PUBLIC_SWITCH)
        if switch is None:
            return
        if switch.checked != public:
            self.device.tap(switch, description="toggle public answer", mutating=True)

    def submit(self) -> bool:
        tree = self.device.dump_tree()
        confirm = tree.find_by_id(Ids.PAPER_CONFIRM)
        if confirm is None:
            raise UiElementNotFound(Ids.PAPER_CONFIRM)
        return self.device.tap(confirm, description="submit paper", mutating=True)

    def answer_question(
        self,
        target: str,
        answers: str | Sequence[str] | Mapping[int | str, str],
        *,
        public: bool = False,
        submit: bool = False,
    ) -> AnswerResult:
        if not self.device.execute:
            self.device.audit.record(
                "dry_run_answer_question",
                target=target,
                answers=answers,
                public=public,
                submit=submit,
            )
            return AnswerResult(target=target, answered=False, submitted=False, dry_run=True)

        filled = self.fill_visible_answers(answers)
        self.set_public(public)
        submitted = self.submit() if submit else False
        return AnswerResult(
            target=target,
            answered=filled > 0,
            submitted=submitted,
            detail=f"filled_visible_answers={filled}",
        )
