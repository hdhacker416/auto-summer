from __future__ import annotations

from collections.abc import Mapping, Sequence
import time

from ..constants import Ids
from ..errors import UiElementNotFound
from ..models import AnswerResult, FilterProbeResult, Question, Stranger, StrangerFilters


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
        filters: StrangerFilters | None = None,
    ) -> list[Stranger]:
        if open_tab:
            self.open()
        if filters is not None:
            self.apply_filters(filters)
        tree = self.device.dump_tree()
        return self._parse_visible_strangers(tree, limit=limit)

    def list_all(
        self,
        *,
        limit: int | None = None,
        max_pages: int = 5,
        filters: StrangerFilters | None = None,
    ) -> list[Stranger]:
        self.open()
        if filters is not None:
            self.apply_filters(filters)
        seen: set[tuple[str, str | None, str | None]] = set()
        strangers: list[Stranger] = []
        previous_signature: tuple[str, ...] | None = None
        stable_pages = 0
        for _ in range(max_pages):
            tree = self.device.dump_tree()
            visible = self._parse_visible_strangers(tree)
            signature = tuple(self._person_key(person)[0] for person in visible)
            for person in visible:
                key = self._person_key(person)
                if key in seen:
                    continue
                seen.add(key)
                strangers.append(person)
                if limit is not None and len(strangers) >= limit:
                    return strangers
            if signature == previous_signature:
                stable_pages += 1
                if stable_pages >= 2:
                    break
            else:
                stable_pages = 0
            previous_signature = signature
            self.device.swipe((600, 2260), (600, 760), description="scroll stranger list")
        return strangers

    def _person_key(self, stranger: Stranger) -> tuple[str, str | None, str | None]:
        return (stranger.nickname, stranger.school, stranger.age)

    def _parse_visible_strangers(self, tree, *, limit: int | None = None) -> list[Stranger]:
        strangers: list[Stranger] = []
        for node in tree.find_all_by_id(Ids.USER_NICKNAME):
            if not node.text:
                continue
            row = node.clickable_ancestor()
            if not row.bounds.is_visible():
                continue
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

    def open_filter_panel(self) -> None:
        self.open()
        tree = self.device.dump_tree()
        button = tree.find_by_id(Ids.FILTER_BUTTON)
        if button is None:
            raise UiElementNotFound(Ids.FILTER_BUTTON)
        self.device.tap(button, description="open stranger filters")
        time.sleep(1)

    def read_filter_state(self) -> dict[str, object]:
        tree = self.device.dump_tree()
        checked = [
            {"id": node.resource_id, "text": node.text}
            for node in tree.find_all(lambda node: "RadioButton" in node.class_name and node.checked)
        ]
        fields = {
            node.resource_id: node.text
            for node in tree.find_all(lambda node: node.resource_id in {Ids.FILTER_DEPARTMENT})
        }
        return {"checked": checked, "fields": fields, "visible_texts": tree.visible_texts()}

    def apply_filters(self, filters: StrangerFilters) -> None:
        self.open_filter_panel()

        selections: list[str] = []
        if filters.gender:
            selections.append(
                {
                    "all": Ids.FILTER_GENDER_ALL,
                    "male": Ids.FILTER_GENDER_MALE,
                    "female": Ids.FILTER_GENDER_FEMALE,
                }[filters.gender]
            )
        if filters.relationship:
            selections.append(
                {
                    "all": Ids.FILTER_RELATIONSHIP_ALL,
                    "single": Ids.FILTER_RELATIONSHIP_SINGLE,
                }[filters.relationship]
            )
        if filters.active:
            selections.append(
                {
                    "all": Ids.FILTER_ACTIVE_ALL,
                    "today": Ids.FILTER_ACTIVE_TODAY,
                }[filters.active]
            )
        if filters.sexual_orientation:
            selections.append(
                {
                    "all": Ids.FILTER_SEXUAL_ALL,
                    "opposite": Ids.FILTER_SEXUAL_OPPOSITE,
                    "same": Ids.FILTER_SEXUAL_SAME,
                }[filters.sexual_orientation]
            )
        if filters.has_photos is not None:
            selections.append(Ids.FILTER_PHOTOS_HAVE if filters.has_photos else Ids.FILTER_PHOTOS_ALL)

        for resource_id in selections:
            self._tap_filter_control(resource_id)

        if filters.department:
            self._set_department(filters.department)

        self._confirm_filter()

    def probe_filter_entitlement(self, filters: StrangerFilters) -> FilterProbeResult:
        self.open()
        before = self.list_visible(limit=10, open_tab=False)
        before_signature = [self._signature_text(person) for person in before]
        try:
            self.apply_filters(filters)
            tree = self.device.dump_tree()
            visible_texts = tree.visible_texts()
            blocked = self._looks_like_vip_block(visible_texts)
            after = self._parse_visible_strangers(tree, limit=10)
            after_signature = [self._signature_text(person) for person in after]
            applied = not blocked and after_signature != before_signature
            return FilterProbeResult(
                attempted=True,
                applied=applied,
                vip_blocked=blocked,
                before_count=len(before),
                after_count=len(after),
                before_signature=before_signature,
                after_signature=after_signature,
                visible_texts=visible_texts,
                detail="Filter appeared to apply." if applied else "No observable list change.",
            )
        except Exception as exc:
            tree = self.device.dump_tree()
            visible_texts = tree.visible_texts()
            return FilterProbeResult(
                attempted=True,
                applied=False,
                vip_blocked=self._looks_like_vip_block(visible_texts),
                before_count=len(before),
                before_signature=before_signature,
                visible_texts=visible_texts,
                detail=str(exc),
            )

    def _tap_filter_control(self, resource_id: str) -> None:
        tree = self.device.dump_tree()
        node = tree.find_by_id(resource_id)
        if node is None:
            self.device.swipe((600, 2300), (600, 900), description="scroll filter panel")
            tree = self.device.dump_tree()
            node = tree.find_by_id(resource_id)
        if node is None:
            raise UiElementNotFound(resource_id)
        if not node.checked:
            self.device.tap(node, description=f"select filter {resource_id}", mutating=True)

    def _set_department(self, department: str) -> None:
        tree = self.device.dump_tree()
        node = tree.find_by_id(Ids.FILTER_DEPARTMENT)
        if node is None:
            self.device.swipe((600, 2300), (600, 900), description="scroll to department filter")
            tree = self.device.dump_tree()
            node = tree.find_by_id(Ids.FILTER_DEPARTMENT)
        if node is None:
            raise UiElementNotFound(Ids.FILTER_DEPARTMENT)
        with self.device.adb_keyboard():
            self.device.tap(node, description="focus department filter")
            self.device.input_text(department, clear=True, mutating=True)

    def _confirm_filter(self) -> None:
        tree = self.device.dump_tree()
        confirm = tree.find_by_id(Ids.FILTER_CONFIRM) or tree.find_by_text("确定")
        if confirm is None:
            raise UiElementNotFound(Ids.FILTER_CONFIRM)
        self.device.tap(confirm, description="confirm filters", mutating=True)
        time.sleep(2)

    def _signature_text(self, stranger: Stranger) -> str:
        return "|".join(
            part or ""
            for part in (stranger.nickname, stranger.school, stranger.age, stranger.distance, stranger.bio)
        )

    def _looks_like_vip_block(self, texts: list[str]) -> bool:
        markers = ("VIP", "会员", "夏星人", "开通", "高级筛选", "购买")
        return any(any(marker in text for marker in markers) for text in texts)

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
