# Summer Automation

Summer Android app (`cn.imsummer.summer`) 的内部授权 QA 自动化 SDK。

它通过 ADB 控制一台已连接的 Android 手机，并读取 Android UIAutomator XML 来定位页面元素。默认不依赖截图，也不要求用户知道设备串口号。

## 快速开始

安装：

```powershell
python -m pip install -e .
```

只有一台手机连接时，直接这样用：

```python
from summer_automation import SummerAccount

with SummerAccount(execute=True) as account:
    friends = account.get_friend_list(limit=5)

    for friend in friends:
        print(friend.nickname, friend.school, friend.age)

    friends[0].send_message("你好，这是一条内部测试消息")
```

`SummerAccount()` 会自动选择当前唯一连接的 ADB 设备。只有同时连接多台手机时，才需要手动传 `serial`。

`get_friend_list()` 默认会跳过系统会话入口，例如 `收到答卷`、`答题记录`、`Summer小秘书`。如果你们还有新的系统入口，可以这样额外跳过：

```python
with SummerAccount(execute=True) as account:
    friends = account.get_friend_list(
        limit=5,
        skip_names={"系统通知", "活动助手"},
    )
```

## 手动输入中文

先在手机上手动点到某个输入框，然后让 SDK 输入中文：

```python
from summer_automation import SummerAccount

with SummerAccount(execute=True) as account:
    account.input_text("你好，这段文字会输入到当前焦点输入框", clear=True)
```

`clear=True` 会先清空当前输入框；如果想追加内容，用 `clear=False`。

## 读取好友和聊天

```python
from summer_automation import SummerAccount

with SummerAccount(execute=True) as account:
    friends = account.get_friend_list(limit=5)

    friend = friends[0]
    friend.send_message("你现在方便聊一下吗？")

    history = friend.read_history(limit=20)
    for message in history:
        print(message.direction, message.text)
```

默认只读取当前聊天页已经渲染出来的消息。要向上滚动加载更多历史记录：

```python
from summer_automation import SummerAccount

with SummerAccount(execute=True) as account:
    friend = account.get_friend_list(limit=1)[0]

    # 向上翻 20 页，尽量收集所有能被客户端加载出来的文本消息。
    history = friend.read_history(limit=None, max_pages=20)

    for message in history:
        print(message.direction, message.text)
```

说明：

- `max_pages` 是最多向上翻页次数，越大读得越多，也越慢。
- `limit=None` 表示返回本次翻页收集到的全部消息。
- 目前读取的是 UI 中可见/可加载的文本消息；图片、语音、撤回提示等非文本内容不会被完整结构化。

## 获取陌生人列表

默认读取当前可见列表：

```python
from summer_automation import SummerAccount

with SummerAccount(execute=True) as account:
    strangers = account.get_stranger_list(limit=10)

    for stranger in strangers:
        print(
            stranger.nickname,
            stranger.age,
            stranger.school,
            stranger.distance,
            stranger.bio,
        )
```

如果要向下滚动收集更多：

```python
with SummerAccount(execute=True) as account:
    strangers = account.get_stranger_list(limit=50, max_pages=8)
```

目前可从同学列表读取到这些字段：

- `nickname`
- `school`
- `age`
- `distance`
- `bio`

## 筛选陌生人

```python
from summer_automation import StrangerFilters, SummerAccount

filters = StrangerFilters(
    gender="female",
    relationship="single",
    active="today",
    has_photos=True,
    department="计算机",
)

with SummerAccount(execute=True) as account:
    strangers = account.get_stranger_list(
        filters=filters,
        limit=20,
        max_pages=5,
    )
```

已封装的筛选字段：

- `gender`: `"all"`, `"male"`, `"female"`
- `relationship`: `"all"`, `"single"`
- `active`: `"all"`, `"today"`
- `sexual_orientation`: `"all"`, `"opposite"`, `"same"`
- `has_photos`: `True` 或 `False`
- `department`: 学院或专业关键词

## VIP 筛选权限探测

如果要验证非 VIP 账号是否能绕过高级筛选，用受控的非 VIP 测试账号跑：

```python
from summer_automation import StrangerFilters, SummerAccount

filters = StrangerFilters(active="today", has_photos=True)

with SummerAccount(execute=True) as account:
    result = account.probe_filter_entitlement(filters)

    print(result.vip_blocked)
    print(result.applied)
    print(result.detail)
```

判断方式：

- `vip_blocked=True`: 页面或权限弹窗拦住了。
- `vip_blocked=False` 且 `applied=True`: 筛选看起来成功生效，需要进一步确认是否为权限绕过。
- `applied=False`: 没观察到列表变化，可能是被拦截，也可能是筛选条件刚好没有改变结果。

VIP 账号只能证明自动化链路可用，不能证明非 VIP 权限边界是否安全。

## 陌生人答题

```python
from summer_automation import SummerAccount

with SummerAccount(execute=True) as account:
    strangers = account.get_stranger_list(limit=5)
    stranger = strangers[0]

    questions = stranger.get_question()
    stranger.answer_question(
        answers=["这是一个认真填写的中文测试回答"] * len(questions),
        public=False,
        submit=False,
    )
```

建议先用 `submit=False` 观察填写效果，确认后再改成 `submit=True`。

## 多设备场景

如果同时连接了多台 Android 设备，自动选择会报错。这时先查设备：

```powershell
adb devices
```

然后显式指定：

```python
from summer_automation import SummerAccount

with SummerAccount(serial="YOUR_DEVICE_SERIAL", execute=True) as account:
    account.input_text("指定设备输入中文")
```

## CLI

CLI 主要用于 smoke test。只有一台设备时不需要传 `--serial`：

```powershell
summerbot device status
summerbot friends list --limit 5
summerbot input text --text "你好" --execute
summerbot messages send-top --limit 5 --text "你好" --execute
```

多设备时再加：

```powershell
summerbot --serial YOUR_DEVICE_SERIAL device status
```

## 安全默认值

- 默认 dry-run；只有 `execute=True` 或 `--execute` 才会执行输入、发送、提交等动作。
- 批量操作默认上限是 5。
- 中文输入时会临时切换到 ADBKeyboard，结束后恢复原输入法。
- 审计日志默认不记录消息正文。
- 只应在授权的内部 QA、靶场或测试账号环境中使用。
