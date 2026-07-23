import json

import clickup


class FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.ok = 200 <= status < 300
        self.text = str(payload)

    def json(self):
        return self._payload


def test_creates_task_when_none_exists(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, params=None):
        return FakeResp(200, {"tasks": []})

    def fake_post(url, headers=None, data=None):
        calls["post_url"] = url
        calls["data"] = data
        return FakeResp(200, {"id": "abc", "url": "https://app.clickup.com/t/abc"})

    monkeypatch.setattr(clickup.requests, "get", fake_get)
    monkeypatch.setattr(clickup.requests, "post", fake_post)

    res = clickup.post_or_update_week_task(
        token="pk_x", list_id="123",
        name="Week of Jun 8 — Grade: A-", description="body")
    assert "/list/123/task" in calls["post_url"]
    assert res["url"].endswith("/t/abc")


def test_updates_existing_same_week(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, params=None):
        return FakeResp(200, {"tasks": [{"id": "old", "name": "Week of Jun 8 — Grade: B"}]})

    def fake_put(url, headers=None, data=None):
        calls["put_url"] = url
        return FakeResp(200, {"id": "old", "url": "https://app.clickup.com/t/old"})

    monkeypatch.setattr(clickup.requests, "get", fake_get)
    monkeypatch.setattr(clickup.requests, "put", fake_put)

    res = clickup.post_or_update_week_task(
        token="pk_x", list_id="123",
        name="Week of Jun 8 — Grade: A-", description="body")
    assert "/task/old" in calls["put_url"]


def test_prefix_matches_old_naming(monkeypatch):
    """A task saved as 'Week of Jun 08 — …' must still be found by the new
    'Week of Jun 08 to 14 — …' name, or every week would post a duplicate."""
    calls = {}

    monkeypatch.setattr(
        clickup.requests, "get",
        lambda url, headers=None, params=None: FakeResp(
            200, {"tasks": [{"id": "old", "name": "Week of Jun 08 — Grade: B"}]}))

    def fake_put(url, headers=None, data=None):
        calls["put_url"] = url
        return FakeResp(200, {"id": "old", "url": "https://app.clickup.com/t/old"})

    def fake_post(url, headers=None, data=None):
        calls["posted"] = True
        return FakeResp(200, {"id": "new"})

    monkeypatch.setattr(clickup.requests, "put", fake_put)
    monkeypatch.setattr(clickup.requests, "post", fake_post)

    clickup.post_or_update_week_task(
        token="pk_x", list_id="123",
        name="Week of Jun 08 to 14 — Grade: A-", description="body")
    assert "/task/old" in calls["put_url"]
    assert "posted" not in calls


def test_prefix_does_not_bleed_across_weeks():
    assert clickup._week_prefix("Week of Jul 13 to 19 — Grade: B-") == "Week of Jul 13"
    assert clickup._week_prefix("Week of Jun 29 to Jul 05 — Grade: B+") == "Week of Jun 29"


def test_create_assigns_when_id_given(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, params=None):
        return FakeResp(200, {"tasks": []})

    def fake_post(url, headers=None, data=None):
        calls["body"] = json.loads(data)
        return FakeResp(200, {"id": "abc", "url": "https://app.clickup.com/t/abc"})

    monkeypatch.setattr(clickup.requests, "get", fake_get)
    monkeypatch.setattr(clickup.requests, "post", fake_post)

    clickup.post_or_update_week_task(
        token="pk_x", list_id="123",
        name="Week of Jun 8 — Grade: A-", description="body",
        assignee_id=204022170)
    assert calls["body"]["assignees"] == [204022170]


def test_update_assigns_with_add_shape(monkeypatch):
    """PUT takes {'add': [...]}, not the plain list POST takes."""
    calls = {}

    def fake_get(url, headers=None, params=None):
        return FakeResp(200, {"tasks": [{"id": "old", "name": "Week of Jun 8 — Grade: B"}]})

    def fake_put(url, headers=None, data=None):
        calls["body"] = json.loads(data)
        return FakeResp(200, {"id": "old", "url": "https://app.clickup.com/t/old"})

    monkeypatch.setattr(clickup.requests, "get", fake_get)
    monkeypatch.setattr(clickup.requests, "put", fake_put)

    clickup.post_or_update_week_task(
        token="pk_x", list_id="123",
        name="Week of Jun 8 — Grade: A-", description="body",
        assignee_id=204022170)
    assert calls["body"]["assignees"] == {"add": [204022170]}


def test_no_assignee_id_omits_the_key(monkeypatch):
    calls = {}

    def fake_get(url, headers=None, params=None):
        return FakeResp(200, {"tasks": []})

    def fake_post(url, headers=None, data=None):
        calls["body"] = json.loads(data)
        return FakeResp(200, {"id": "abc", "url": "https://app.clickup.com/t/abc"})

    monkeypatch.setattr(clickup.requests, "get", fake_get)
    monkeypatch.setattr(clickup.requests, "post", fake_post)

    clickup.post_or_update_week_task(
        token="pk_x", list_id="123",
        name="Week of Jun 8 — Grade: A-", description="body")
    assert "assignees" not in calls["body"]


def test_create_sets_due_date(monkeypatch):
    """No due date means the task never appears on ClickUp Home."""
    calls = {}

    monkeypatch.setattr(clickup.requests, "get",
                        lambda url, headers=None, params=None: FakeResp(200, {"tasks": []}))

    def fake_post(url, headers=None, data=None):
        calls["body"] = json.loads(data)
        return FakeResp(200, {"id": "abc", "url": "https://app.clickup.com/t/abc"})

    monkeypatch.setattr(clickup.requests, "post", fake_post)

    clickup.post_or_update_week_task(
        token="pk_x", list_id="123",
        name="Week of Jun 8 — Grade: A-", description="body",
        due_date=1784822400000)
    assert calls["body"]["due_date"] == 1784822400000
    assert calls["body"]["due_date_time"] is False


def test_update_sets_due_date(monkeypatch):
    calls = {}

    monkeypatch.setattr(
        clickup.requests, "get",
        lambda url, headers=None, params=None: FakeResp(
            200, {"tasks": [{"id": "old", "name": "Week of Jun 8 — Grade: B"}]}))

    def fake_put(url, headers=None, data=None):
        calls["body"] = json.loads(data)
        return FakeResp(200, {"id": "old", "url": "https://app.clickup.com/t/old"})

    monkeypatch.setattr(clickup.requests, "put", fake_put)

    clickup.post_or_update_week_task(
        token="pk_x", list_id="123",
        name="Week of Jun 8 — Grade: A-", description="body",
        due_date=1784822400000)
    assert calls["body"]["due_date"] == 1784822400000


def test_no_due_date_omits_the_key(monkeypatch):
    calls = {}

    monkeypatch.setattr(clickup.requests, "get",
                        lambda url, headers=None, params=None: FakeResp(200, {"tasks": []}))

    def fake_post(url, headers=None, data=None):
        calls["body"] = json.loads(data)
        return FakeResp(200, {"id": "abc", "url": "https://app.clickup.com/t/abc"})

    monkeypatch.setattr(clickup.requests, "post", fake_post)

    clickup.post_or_update_week_task(
        token="pk_x", list_id="123",
        name="Week of Jun 8 — Grade: A-", description="body")
    assert "due_date" not in calls["body"]


def test_current_user_id(monkeypatch):
    monkeypatch.setattr(clickup.requests, "get",
                        lambda url, headers=None: FakeResp(200, {"user": {"id": 204022170}}))
    assert clickup.current_user_id("pk_x") == 204022170


def test_current_user_id_none_without_token():
    assert clickup.current_user_id("") is None


def test_missing_token_skips(monkeypatch):
    res = clickup.post_or_update_week_task(token="", list_id="123",
                                           name="x", description="y")
    assert res["skipped"] is True
