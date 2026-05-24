import unittest

from summer_automation.constants import Ids
from summer_automation.pages.messages import MessagesPage
from summer_automation.ui_tree import UiTree


class _FakeMain:
    def open_tab(self, label: str) -> None:
        self.label = label


class _FakeDevice:
    def __init__(self, tree: UiTree):
        self._tree = tree

    def dump_tree(self) -> UiTree:
        return self._tree


class _FakeAccount:
    def __init__(self, tree: UiTree):
        self.main = _FakeMain()
        self.device = _FakeDevice(tree)


class MessagesPageTests(unittest.TestCase):
    def test_system_chat_entries_are_skipped(self):
        xml = f"""<?xml version='1.0' encoding='UTF-8'?>
        <hierarchy>
          <node text="" resource-id="" class="android.widget.FrameLayout" clickable="false" bounds="[0,0][100,300]">
            <node text="" resource-id="" class="android.widget.LinearLayout" clickable="true" bounds="[0,0][100,80]">
              <node text="收到答卷/答题记录" resource-id="{Ids.MESSAGE_NICKNAME}" class="android.widget.TextView" clickable="false" bounds="[10,10][80,30]" />
            </node>
            <node text="" resource-id="" class="android.widget.LinearLayout" clickable="true" bounds="[0,80][100,160]">
              <node text="Summer小秘书" resource-id="{Ids.MESSAGE_NICKNAME}" class="android.widget.TextView" clickable="false" bounds="[10,90][80,110]" />
            </node>
            <node text="" resource-id="" class="android.widget.LinearLayout" clickable="true" bounds="[0,160][100,240]">
              <node text="测试用户A" resource-id="{Ids.MESSAGE_NICKNAME}" class="android.widget.TextView" clickable="false" bounds="[10,170][80,190]" />
            </node>
          </node>
        </hierarchy>
        """
        page = MessagesPage(_FakeAccount(UiTree.from_xml(xml)))

        friends = page.list_recent_chats(limit=5, open_tab=False)

        self.assertEqual([friend.nickname for friend in friends], ["测试用户A"])


if __name__ == "__main__":
    unittest.main()
