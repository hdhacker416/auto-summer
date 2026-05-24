import unittest
from unittest.mock import patch

from summer_automation.adb import Adb
from summer_automation.constants import Ids
from summer_automation.errors import DeviceSelectionError
from summer_automation.models import Message
from summer_automation.pages.chat import ChatPage
from summer_automation.ui_tree import Bounds, UiTree


class UiTreeTests(unittest.TestCase):
    def test_bounds_center(self):
        self.assertEqual(Bounds.parse("[10,20][30,60]").center, (20, 40))

    def test_find_nodes_and_clickable_ancestor(self):
        xml = f"""<?xml version='1.0' encoding='UTF-8'?>
        <hierarchy>
          <node text="" resource-id="" class="android.widget.FrameLayout" clickable="false" bounds="[0,0][100,100]">
            <node text="" resource-id="" class="android.widget.LinearLayout" clickable="true" bounds="[0,10][100,40]">
              <node text="测试用户A" resource-id="{Ids.MESSAGE_NICKNAME}" class="android.widget.TextView" clickable="false" bounds="[10,12][80,30]" />
            </node>
          </node>
        </hierarchy>
        """
        tree = UiTree.from_xml(xml)
        node = tree.require_by_id(Ids.MESSAGE_NICKNAME)

        self.assertEqual(node.text, "测试用户A")
        self.assertEqual(node.clickable_ancestor().bounds.center, (50, 25))

    def test_resolve_single_device(self):
        with patch.object(Adb, "list_devices", return_value=["DEVICE123"]):
            self.assertEqual(Adb.resolve_serial(), "DEVICE123")

    def test_resolve_requires_explicit_serial_for_multiple_devices(self):
        with patch.object(Adb, "list_devices", return_value=["A", "B"]):
            with self.assertRaises(DeviceSelectionError):
                Adb.resolve_serial()

    def test_merge_older_chat_page_uses_overlap(self):
        current = [
            Message("第二条", "incoming"),
            Message("第三条", "outgoing"),
        ]
        older = [
            Message("第一条", "incoming"),
            Message("第二条", "incoming"),
        ]

        merged = ChatPage._merge_older_page(current, older)

        self.assertEqual(
            [(message.direction, message.text) for message in merged],
            [
                ("incoming", "第一条"),
                ("incoming", "第二条"),
                ("outgoing", "第三条"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
