# Summer Automation

Internal, authorized QA automation SDK for the Summer Android app (`cn.imsummer.summer`).

The SDK controls a connected Android device through ADB and reads Android UIAutomator XML. It is designed for controlled testing environments where the test account, device, app, and target users are authorized.

## Features

- Account-level API: `SummerAccount`
- Friend objects: send messages and read visible chat history
- Stranger objects: read visible paper questions and fill answers
- Reliable Chinese text input through ADBKeyboard + UTF-8 Base64
- Dry-run by default for mutating actions
- Optional JSONL audit logging with message content redacted by default

## Install

```powershell
python -m pip install -e .
```

## Python API

```python
from summer_automation import SummerAccount

with SummerAccount(serial="YOUR_DEVICE_SERIAL", execute=True) as account:
    friends = account.get_friend_list(limit=5)

    friend = friends[0]
    friend.send_message("你好，这是一条内部测试消息")

    history = friend.read_history(limit=20)
```

If exactly one Android device is connected, `serial` can be omitted:

```python
with SummerAccount(execute=True) as account:
    account.input_text("你好", clear=True)
```

Manual text input into the currently focused phone field:

```python
from summer_automation import SummerAccount

with SummerAccount(serial="YOUR_DEVICE_SERIAL", execute=True) as account:
    account.input_text("你好，这段文字会输入到当前焦点输入框", clear=True)
```

Collect more than the currently visible stranger rows by scrolling:

```python
from summer_automation import SummerAccount

with SummerAccount(execute=True) as account:
    strangers = account.get_stranger_list(limit=50, max_pages=8)

    for stranger in strangers:
        print(stranger.nickname, stranger.age, stranger.school, stranger.distance, stranger.bio)
```

Apply supported filters in an authorized QA account:

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
    strangers = account.get_stranger_list(filters=filters, limit=20, max_pages=5)
```

Probe whether a non-VIP account can apply a VIP-gated filter:

```python
from summer_automation import StrangerFilters, SummerAccount

filters = StrangerFilters(active="today", has_photos=True)

with SummerAccount(execute=True) as account:
    result = account.probe_filter_entitlement(filters)
    print(result.vip_blocked, result.applied, result.detail)
```

Run this probe with a controlled non-VIP account. A VIP test account can verify
the automation path, but it cannot prove the non-VIP authorization boundary.

Stranger/paper flow:

```python
from summer_automation import SummerAccount

with SummerAccount(serial="YOUR_DEVICE_SERIAL", execute=True) as account:
    strangers = account.get_stranger_list(limit=5)
    stranger = strangers[0]

    questions = stranger.get_question()
    stranger.answer_question(
        answers=["这是一个认真填写的中文测试回答"] * len(questions),
        public=False,
        submit=False,
    )
```

## CLI

The package also includes a CLI for QA smoke tests:

```powershell
summerbot --serial YOUR_DEVICE_SERIAL device status
summerbot --serial YOUR_DEVICE_SERIAL friends list --limit 5
summerbot --serial YOUR_DEVICE_SERIAL input text --text "你好" --execute
summerbot --serial YOUR_DEVICE_SERIAL messages send-top --limit 5 --text "你好" --execute
```

## Safety Defaults

- Mutating actions are dry-run unless `execute=True` or `--execute` is used.
- Batch operations have a default limit of 5.
- The original input method is restored after text automation.
- Audit logs avoid storing message history content by default.
- This project should be used only in authorized internal QA environments.
