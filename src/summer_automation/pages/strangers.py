from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..constants import Ids
from ..errors import UiElementNotFound
from ..models import AnswerResult, Question, Stranger


class StrangersPage:
    def __init__(self, account):
        self.account = account
        self.device = account.device

    def open(self) -> None:
        self.account.main.open_tab("同学")

    def list_visible(
        self,
        *,
        limit: int | None = None,
        open_tab: bool = True,
    ) -> list[Stranger]:
        if open_tab:
            self.open()
        tree = self.device.dump_tree()
        strangers: list[Stranger] = []
        for node in tree.find_all_by_id(Ids.USER_NICKNAME):
            if not node.text:
                continue
            row = node.clickable_ancestor()
            school = row.find_descendant_by_id(Ids.USER_SCHOOL)
            age = row.find_descendant_by_id(Ids.USER_AGE)
            distance = row.find_descendant_by_id(Ids.USER_DISTANCE)
            bio = row.find_descendant_by_id(Ids.USER_BIO)
            strangers.append(
                Stranger(
                    nickname=node.text,
                    account=self.account,
                    source="nearby",
                    row_bounds=row.bounds,
                    school=school.text if school else None,
                    age=age.text if age else None,
                    distance=distance.text if distance else None,
                    bio=bio.text if bio else None,
                )
            )
            if limit is not None and len(strangers) >= limit:
                break
        return strangers

    def open_profile(self, stranger: Stranger) -> None:
        self.open()
        tree = self.device.dump_tree()
        for node in tree.find_all_by_id(Ids.USER_NICKNAME):
            if node.text == stranger.nickname:
                self.device.tap(node.clickable_ancestor(), description=f"open stranger {stranger.nickname}")
                return
        if stranger.row_bounds is not None:
            x, y = stranger.row_bounds.center
            self.device.tap(x, y, description=f"open stranger {stranger.nickname} from saved bounds")
            return
        raise UiElementNotFound(f"stranger row for {stranger.nickname}")

    def _open_paper_from_profile(self) -> None:
        tree = self.device.dump_tree()
        if tree.find_by_id(Ids.PAPER_LIST):
            return
        candidates = []
        for label in ("答题", "试卷", "加好友", "申请加好友", "我要答题"):
            candidates.extend(tree.find_all_by_text(label, exact=False))
        for node in candidates:
            target = node.clickable_ancestor()
            if target.bounds.is_visible():
                self.device.tap(target, description=f"open paper via {node.text}")
                self.device.wait_for(
                    lambda: self.device.dump_tree().find_by_id(Ids.PAPER_LIST) is not None,
                    description="paper page",
                )
                return
        raise UiElementNotFound("paper entry on stranger profile")

    def get_questions(self, stranger: Stranger) -> list[Question]:
        self.open_profile(stranger)
        self._open_paper_from_profile()
        return self.account.paper.read_visible_questions()

    def answer_question(
        self,
        stranger: Stranger,
        *,
        answers: str | Sequence[str] | Mapping[int | str, str],
        public: bool = False,
        submit: bool = False,
    ) -> AnswerResult:
        self.open_profile(stranger)
        self._open_paper_from_profile()
        return self.account.paper.answer_question(
            stranger.nickname,
            answers,
            public=public,
            submit=submit,
        )
