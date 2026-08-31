"""SM AgentOps 领域测试：智能体注册、启停、运行记录、成本告警与统计。"""

import pytest
from fastapi.testclient import TestClient

from app import base
from app.main import VERSION, app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(base, "internal_api_key", lambda: "TEST")
    monkeypatch.setenv("SM_AGENTOPS_TOKEN_THRESHOLD", "100")  # 低阈值确保触发告警
    base.reset_state()
    from app.main import _init as init_db
    init_db()
    with TestClient(app) as c:
        c.headers["X-Internal-Token"] = "TEST"
        yield c


def _agent(client, name="support-bot"):
    return client.post("/api/agentops/agents", json={"name": name, "model": "doubao-pro", "owner": "AI平台部"}).json()["id"]


def test_health_and_version(client):
    r = client.get("/health", headers={"X-Request-Id": "suite-test"})
    assert r.status_code == 200
    assert r.json()["version"] == VERSION


def test_agent_crud(client):
    _agent(client)
    assert client.post("/api/agentops/agents", json={"name": "support-bot", "model": "mm"}).status_code == 409
    assert client.get("/api/agentops/agents").json()["total"] == 1


def test_start_stop(client):
    agent_id = _agent(client)
    assert client.post(f"/api/agentops/agents/{agent_id}/start").json()["status"] == "running"
    assert client.post(f"/api/agentops/agents/{agent_id}/stop").json()["status"] == "idle"
    assert client.post("/api/agentops/agents/nope/start").status_code == 404


def test_run_and_alert(client):
    agent_id = _agent(client)
    run = client.post("/api/agentops/runs", json={"agent_id": agent_id, "task": "生成日报"}).json()
    assert run["status"] == "success"
    assert run["tokens_used"] > 0
    assert client.get(f"/api/agentops/agents/{agent_id}/runs").json()["total"] == 1
    # 阈值 100 → tokens 大概率 > 100 → 触发告警
    alerts = client.get("/api/agentops/alerts").json()
    assert alerts["total"] >= 1


def test_run_missing_agent(client):
    assert client.post("/api/agentops/runs", json={"agent_id": "no-such-agent", "task": "tt"}).status_code == 404


def test_stats(client):
    agent_id = _agent(client)
    client.post("/api/agentops/runs", json={"agent_id": agent_id, "task": "任务"})
    stats = client.get("/api/agentops/stats").json()
    assert stats["agents"] == 1
    assert stats["runs"] == 1
    assert stats["total_tokens"] > 0


def test_manifest_and_crypto(client):
    assert client.get("/api/integration/manifest").json()["version"] == VERSION
    enc = client.post("/api/crypto/encrypt", json={"value": "x"}).json()["ciphertext"]
    assert client.post("/api/crypto/decrypt", json={"value": enc}).json()["plaintext"] == "x"


def test_write_requires_auth(client):
    del client.headers["X-Internal-Token"]
    assert client.post("/api/agentops/agents", json={"name": "a", "model": "m"}).status_code == 401
