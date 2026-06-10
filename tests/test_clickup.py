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


def test_missing_token_skips(monkeypatch):
    res = clickup.post_or_update_week_task(token="", list_id="123",
                                           name="x", description="y")
    assert res["skipped"] is True
