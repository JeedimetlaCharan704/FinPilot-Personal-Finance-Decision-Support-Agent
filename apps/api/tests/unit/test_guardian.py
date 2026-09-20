"""Unit tests for the Subscription Guardian (Phase 7).

Hermetic (DB mocked). Covers: detection math, data-sourcing (never
fabricated), signal logic, API endpoints, idempotent drafting, approve /
reject behavior, the "never re-propose resolved actions" rule, no external
side effects, LLM grounding and deterministic fallback.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import db
from app.llm import LLMError
from app.llm.validation import (
    TOOL_ALLOWED_ARGS, is_ungrounded, validate_intent, validate_tool_plan,
)
from app.main import app
from app.schemas import AgentAnalyzeResponse
from app.services import guardian, intents, orchestrator, tools

client = TestClient(app)

USER = {"id": "user-1", "email": "demo@finpilot.in", "display_name": "Demo", "currency": "INR"}

# Recurring payment table (from the seed) mirrored for the mock.
RECURRING = [
    {"id": "r1", "merchant": "Netflix", "description": "Netflix",
     "amount": 649, "frequency": "monthly", "next_payment_date": "2026-07-10",
     "status": "active", "category_id": "cat_subs"},
    {"id": "r2", "merchant": "Landlord", "description": "House rent",
     "amount": 15000, "frequency": "monthly", "next_payment_date": "2026-07-03",
     "status": "active", "category_id": "cat_rent"},
    {"id": "r3", "merchant": "BESCOM", "description": "Electricity bill",
     "amount": 2600, "frequency": "monthly", "next_payment_date": "2026-07-07",
     "status": "active", "category_id": "cat_util"},
]

CATEGORIES = [
    {"id": "cat_subs", "name": "Subscriptions", "category_type": "discretionary"},
    {"id": "cat_rent", "name": "Rent", "category_type": "essential"},
    {"id": "cat_util", "name": "Utilities", "category_type": "essential"},
]

# Transaction history. Netflix: 499 x3 then 649 x2 (confirmed increase).
# BESCOM varies every month (never confirmed). Landlord stable at 15000.
TXN = [
    {"transaction_date": "2026-01-03", "amount": 15000, "transaction_type": "expense", "merchant": "Landlord"},
    {"transaction_date": "2026-02-03", "amount": 15000, "transaction_type": "expense", "merchant": "Landlord"},
    {"transaction_date": "2026-03-03", "amount": 15000, "transaction_type": "expense", "merchant": "Landlord"},
    {"transaction_date": "2026-04-03", "amount": 15000, "transaction_type": "expense", "merchant": "Landlord"},
    {"transaction_date": "2026-05-03", "amount": 15000, "transaction_type": "expense", "merchant": "Landlord"},
    {"transaction_date": "2026-06-03", "amount": 15000, "transaction_type": "expense", "merchant": "Landlord"},
    {"transaction_date": "2026-01-07", "amount": 2200, "transaction_type": "expense", "merchant": "BESCOM"},
    {"transaction_date": "2026-02-07", "amount": 2600, "transaction_type": "expense", "merchant": "BESCOM"},
    {"transaction_date": "2026-03-07", "amount": 2400, "transaction_type": "expense", "merchant": "BESCOM"},
    {"transaction_date": "2026-04-07", "amount": 2500, "transaction_type": "expense", "merchant": "BESCOM"},
    {"transaction_date": "2026-05-07", "amount": 2300, "transaction_type": "expense", "merchant": "BESCOM"},
    {"transaction_date": "2026-06-07", "amount": 2565, "transaction_type": "expense", "merchant": "BESCOM"},
    {"transaction_date": "2026-01-10", "amount": 499, "transaction_type": "expense", "merchant": "Netflix"},
    {"transaction_date": "2026-02-10", "amount": 499, "transaction_type": "expense", "merchant": "Netflix"},
    {"transaction_date": "2026-03-10", "amount": 499, "transaction_type": "expense", "merchant": "Netflix"},
    {"transaction_date": "2026-04-10", "amount": 649, "transaction_type": "expense", "merchant": "Netflix"},
    {"transaction_date": "2026-05-10", "amount": 649, "transaction_type": "expense", "merchant": "Netflix"},
]

_write_calls: list[str] = []


def _reset_mocks(monkeypatch):
    _write_calls.clear()
    monkeypatch.setattr("app.db.get_user_by_id",
                        lambda uid: USER if uid == "user-1" else None)
    monkeypatch.setattr("app.db.fetch_recurring",
                        lambda uid, status="active": RECURRING if status == "active" else [])
    monkeypatch.setattr("app.db.fetch_transactions",
                        lambda uid, start_date=None, end_date=None, limit=None, columns="": list(TXN))
    monkeypatch.setattr("app.db.list_categories", lambda: list(CATEGORIES))
    monkeypatch.setattr("app.db.list_action_drafts",
                        lambda uid, status=None, limit=50: list(_DRAFTS))
    monkeypatch.setattr("app.db.get_action_draft",
                        lambda aid: next((a for a in _DRAFTS if a["id"] == aid), None))

    def _update_status(aid, status):
        for a in _DRAFTS:
            if a["id"] == aid:
                a["status"] = status
        _write_calls.append(("update_action_status", aid, status))

    monkeypatch.setattr("app.db.update_action_status", _update_status)

    def _create_draft(user_id, action_type, title, description="", payload=None):
        existing = next((a for a in _DRAFTS if a["title"] == title and a["status"] == "draft"), None)
        if existing:
            return existing["id"]
        aid = f"draft-{len(_DRAFTS) + 1}"
        _DRAFTS.append({"id": aid, "title": title, "description": description,
                        "status": "draft", "action_type": action_type, "payload_json": payload or {}})
        _write_calls.append(("create_action_draft", action_type, title))
        return aid

    monkeypatch.setattr("app.db.create_action_draft", _create_draft)


_DRAFTS: list[dict] = []


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    _DRAFTS.clear()
    _reset_mocks(monkeypatch)


# --- 1 + 4: module exists, functions exposed, data sourced from the DB ----

def test_guardian_module_has_detection_and_draft_api():
    assert callable(guardian.detect)
    assert callable(guardian.create_draft)
    assert callable(guardian.summarize)


def test_detect_reads_recurring_and_transactions(mock_db, monkeypatch):
    seen = {}

    def rec(uid, status="active"):
        seen["recurring"] = True
        return RECURRING

    def txns(uid, start_date=None, end_date=None, limit=None, columns=""):
        seen["transactions"] = True
        return list(TXN)

    monkeypatch.setattr("app.db.fetch_recurring", rec)
    monkeypatch.setattr("app.db.fetch_transactions", txns)
    out = guardian.detect("user-1")
    assert seen.get("recurring") is True
    assert seen.get("transactions") is True
    assert "items" in out and "summary" in out


# --- 3 + 5: policy is documented in the response object --------------------

def test_detect_documents_no_execute_no_cancel_no_contact(mock_db):
    out = guardian.detect("user-1")
    policy = out["policy"]
    assert policy["executes"] is False
    assert policy["cancels"] is False
    assert policy["contacts"] is False
    assert any("action_drafts.status" in m for m in policy["mutations"])


# --- 6 + 7 + 8 + 9: the Netflix 499 -> 649 detection -----------------------

def test_detect_netflix_price_increase(mock_db):
    out = guardian.detect("user-1")
    nf = next(i for i in out["items"] if i["merchant"] == "Netflix")
    assert nf["previous_amount"] == 499
    assert nf["current_amount"] == 649
    assert nf["increase_amount"] == 150
    assert nf["increase_percent"] == 30.06            # 150 / 499 = 30.06%
    assert nf["annual_increase"] == 1800              # 150 * 12
    assert nf["monthly_cost"] == 649
    assert nf["annual_cost"] == 7788                  # 649 * 12
    assert nf["signal"] == "PRICE_INCREASE"
    assert "RECURRING_COST" in nf["additional_signals"]
    assert nf["frequency"] == "monthly"
    assert nf["payment_count"] == 5
    assert nf["latest_payment_date"] == "2026-05-10"
    assert nf["latest_payment_amount"] == 649
    assert nf["previous_payment_date"] == "2026-04-10"
    assert nf["evidence_refs"], "evidence refs must be present"


def test_detect_netflix_is_the_only_flagged_item(mock_db):
    out = guardian.detect("user-1")
    assert out["summary"]["changed_count"] == 1
    assert out["summary"]["items_total"] == 1
    assert out["summary"]["signals"]["PRICE_INCREASE"] == 1
    assert [i["merchant"] for i in out["items"]] == ["Netflix"]


# --- 10: no fabricated data (detection follows the DB, never hardcodes) ----

def test_detect_uses_actual_db_amounts_not_hardcoded(mock_db, monkeypatch):
    # A different history -> a different, data-driven result.
    other = [
        {"transaction_date": "2026-01-10", "amount": 299, "transaction_type": "expense", "merchant": "Spotify"},
        {"transaction_date": "2026-02-10", "amount": 299, "transaction_type": "expense", "merchant": "Spotify"},
        {"transaction_date": "2026-03-10", "amount": 399, "transaction_type": "expense", "merchant": "Spotify"},
        {"transaction_date": "2026-04-10", "amount": 399, "transaction_type": "expense", "merchant": "Spotify"},
    ]
    rec = [
        {"id": "r9", "merchant": "Spotify", "description": "Spotify", "amount": 399,
         "frequency": "monthly", "next_payment_date": "2026-07-15", "status": "active",
         "category_id": "cat_subs"},
    ]
    monkeypatch.setattr("app.db.fetch_recurring", lambda uid, status="active": rec)
    monkeypatch.setattr("app.db.fetch_transactions",
                        lambda uid, start_date=None, end_date=None, limit=None, columns="": other)
    out = guardian.detect("user-1")
    item = out["items"][0]
    assert item["merchant"] == "Spotify"
    assert item["previous_amount"] == 299
    assert item["current_amount"] == 399
    assert item["increase_amount"] == 100
    assert item["increase_percent"] == round(100 / 299 * 100, 2)


def test_detect_one_off_price_change_is_not_flagged(mock_db, monkeypatch):
    # Only ONE payment at the new price -> not confirmed -> no PRICE_INCREASE.
    hist = [
        {"transaction_date": "2026-01-10", "amount": 499, "transaction_type": "expense", "merchant": "Netflix"},
        {"transaction_date": "2026-02-10", "amount": 499, "transaction_type": "expense", "merchant": "Netflix"},
        {"transaction_date": "2026-03-10", "amount": 499, "transaction_type": "expense", "merchant": "Netflix"},
        {"transaction_date": "2026-04-10", "amount": 649, "transaction_type": "expense", "merchant": "Netflix"},
    ]
    monkeypatch.setattr("app.db.fetch_transactions",
                        lambda uid, start_date=None, end_date=None, limit=None, columns="": hist)
    out = guardian.detect("user-1")
    nf = next(i for i in out["items"] if i["merchant"] == "Netflix")
    assert nf["signal"] != "PRICE_INCREASE"
    assert nf["previous_amount"] is None


def test_detect_fluctuating_utility_bill_never_counts_as_increase(mock_db):
    # BESCOM changes every month but the change is never confirmed.
    b = next((i for i in guardian.detect("user-1")["items"]
              if i["merchant"] == "BESCOM"), None)
    assert b is None, "essential utility bills are not review targets"


def test_detect_flat_price_series_has_no_increase(mock_db, monkeypatch):
    hist = [
        {"transaction_date": "2026-01-10", "amount": 499, "transaction_type": "expense", "merchant": "Netflix"},
        {"transaction_date": "2026-02-10", "amount": 499, "transaction_type": "expense", "merchant": "Netflix"},
    ]
    monkeypatch.setattr("app.db.fetch_transactions",
                        lambda uid, start_date=None, end_date=None, limit=None, columns="": hist)
    nf = next(i for i in guardian.detect("user-1")["items"]
              if i["merchant"] == "Netflix")
    assert nf["signal"] != "PRICE_INCREASE"
    assert nf["previous_amount"] is None
    assert nf["increase_amount"] == 0


def test_detect_no_transactions_no_crash(mock_db, monkeypatch):
    monkeypatch.setattr("app.db.fetch_transactions",
                        lambda uid, start_date=None, end_date=None, limit=None, columns="": [])
    out = guardian.detect("user-1")
    assert out["summary"]["changed_count"] == 0
    assert not any(i["signal"] == "PRICE_INCREASE" for i in out["items"])
    # Netflix still appears as a RECURRING_COST item even with no history
    assert len(out["items"]) == 1
    assert out["items"][0]["merchant"] == "Netflix"
    assert out["items"][0]["signal"] == "RECURRING_COST"


# --- guard intent routing ----------------------------------------------------

def test_guardian_intent_routes_to_guardian_tools():
    info = intents.classify("Why did my Netflix subscription go up?")
    assert info["intent"] == "guardian"
    assert "guardian_detect" in info["tools"]

    info2 = intents.classify("Which of my subscriptions went up?")
    assert info2["intent"] == "guardian"

    info3 = intents.classify("What subscriptions am I paying for?")
    assert info3["intent"] == "subscriptions", "plain listing stays subscriptions"


# --- tool registry + LLM allowlist -------------------------------------------

def test_guardian_detect_tool_registered():
    assert "guardian_detect" in tools.TOOLS
    assert "guardian_detect" in TOOL_ALLOWED_ARGS
    assert TOOL_ALLOWED_ARGS["guardian_detect"] == frozenset()


def test_guardian_detect_tool_executes(mock_db):
    out = tools.execute_tool("guardian_detect", "user-1", {})
    assert out["summary"]["changed_count"] == 1


def test_llm_plan_accepts_guardian_detect():
    plan = validate_tool_plan({"intent": "guardian",
                               "tools": [{"name": "guardian_detect", "arguments": {}},
                                         {"name": "get_recurring_payments", "arguments": {}}]})
    assert plan is not None
    assert [t.name for t in plan.tools] == ["guardian_detect", "get_recurring_payments"]


def test_llm_cannot_pass_arguments_to_guardian_detect():
    plan = validate_tool_plan({"intent": "guardian",
                               "tools": [{"name": "guardian_detect", "arguments": {"merchant": "Netflix"}}]})
    assert plan is None


def test_llm_guardian_intent_valid():
    out = validate_intent({"intent": "guardian", "confidence": 0.9})
    assert out is not None and out.intent == "guardian"


def test_guardian_answer_grounding_blocks_invented_figures():
    grounding = "499 649 150 1800 7788 Netflix month"
    assert is_ungrounded("Netflix went from Rs 499 to Rs 649 per month.", grounding) is False
    assert is_ungrounded("Netflix now costs Rs 9,999 per month.", grounding) is True


# --- draft creation + idempotency (STEP 11) ----------------------------------

def test_api_draft_endpoint_creates_draft(mock_db):
    r = client.post("/api/guardian/draft", json={"user_id": "user-1", "merchant": "Netflix"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "draft"
    assert body["title"] == "Review Netflix price increase"
    assert "499" in body["description"] and "649" in body["description"]
    assert "1800" in body["description"]
    assert _write_calls and _write_calls[-1][0] == "create_action_draft"


def test_api_draft_endpoint_idempotent(mock_db):
    a = client.post("/api/guardian/draft", json={"user_id": "user-1", "merchant": "Netflix"}).json()
    b = client.post("/api/guardian/draft", json={"user_id": "user-1", "merchant": "Netflix"}).json()
    assert a["action_id"] == b["action_id"]
    assert a["status"] == b["status"] == "draft"
    draft_writes = [c for c in _write_calls if c[0] == "create_action_draft"]
    assert len(draft_writes) == 1


def test_api_draft_unknown_merchant_rejected(mock_db):
    r = client.post("/api/guardian/draft", json={"user_id": "user-1", "merchant": "NotAThing"})
    assert r.status_code == 422


def test_api_draft_unknown_user_404(mock_db):
    r = client.post("/api/guardian/draft", json={"user_id": "nobody", "merchant": "Netflix"})
    assert r.status_code == 404


# --- approve / reject, and the never-re-propose rule (STEP 12 + 13) ----------

def test_approved_action_is_never_reproposed(mock_db):
    first = client.post("/api/guardian/draft", json={"user_id": "user-1", "merchant": "Netflix"}).json()
    r = client.post(f"/api/actions/{first['action_id']}/approve")
    assert r.status_code == 200 and r.json()["status"] == "approved"

    second = client.post("/api/guardian/draft", json={"user_id": "user-1", "merchant": "Netflix"}).json()
    assert second["action_id"] == first["action_id"]
    assert second["status"] == "approved"
    assert second.get("previously_resolved") is True
    draft_writes = [c for c in _write_calls if c[0] == "create_action_draft"]
    assert len(draft_writes) == 1, "no new draft may be created for a resolved action"


def test_rejected_action_is_never_reproposed(mock_db):
    first = client.post("/api/guardian/draft", json={"user_id": "user-1", "merchant": "Netflix"}).json()
    r = client.post(f"/api/actions/{first['action_id']}/reject")
    assert r.status_code == 200 and r.json()["status"] == "rejected"

    second = client.post("/api/guardian/draft", json={"user_id": "user-1", "merchant": "Netflix"}).json()
    assert second["status"] == "rejected"
    assert second.get("previously_resolved") is True
    draft_writes = [c for c in _write_calls if c[0] == "create_action_draft"]
    assert len(draft_writes) == 1


def test_draft_can_still_be_created_after_review_of_another_merchant(mock_db):
    client.post("/api/guardian/draft", json={"user_id": "user-1", "merchant": "Netflix"})
    # A different flagged merchant still gets its own independent draft.
    rec = RECURRING + [{"id": "r9", "merchant": "Spotify", "description": "Spotify",
                        "amount": 399, "frequency": "monthly", "next_payment_date": "2026-07-15",
                        "status": "active", "category_id": "cat_subs"}]
    tx = list(TXN) + [
        {"transaction_date": "2026-01-15", "amount": 299, "transaction_type": "expense", "merchant": "Spotify"},
        {"transaction_date": "2026-02-15", "amount": 299, "transaction_type": "expense", "merchant": "Spotify"},
        {"transaction_date": "2026-03-15", "amount": 399, "transaction_type": "expense", "merchant": "Spotify"},
        {"transaction_date": "2026-04-15", "amount": 399, "transaction_type": "expense", "merchant": "Spotify"},
    ]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("app.db.fetch_recurring", lambda uid, status="active": rec)
    monkeypatch.setattr("app.db.fetch_transactions",
                        lambda uid, start_date=None, end_date=None, limit=None, columns="": tx)
    try:
        r = client.post("/api/guardian/draft", json={"user_id": "user-1", "merchant": "Spotify"})
        assert r.status_code == 200
        assert r.json()["title"] == "Review Spotify price increase"
    finally:
        monkeypatch.undo()


# --- endpoints -----------------------------------------------------------------

def test_api_detect_endpoint_returns_policy(mock_db):
    r = client.get("/api/guardian/detect", params={"user_id": "user-1"})
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["changed_count"] == 1
    assert body["items"][0]["merchant"] == "Netflix"
    assert body["policy"]["executes"] is False


def test_api_detect_unknown_user_404(mock_db):
    r = client.get("/api/guardian/detect", params={"user_id": "nobody"})
    assert r.status_code == 404


def test_api_summary_endpoint(mock_db):
    r = client.get("/api/guardian/summary", params={"user_id": "user-1"})
    assert r.status_code == 200
    body = r.json()
    assert body["changed_count"] == 1
    assert body["items"][0]["merchant"] == "Netflix"
    assert body["items"][0]["current_amount"] == 649


# --- 14: no external side effects ----------------------------------------------

def test_detect_and_draft_have_no_external_side_effects(mock_db):
    client.get("/api/guardian/detect", params={"user_id": "user-1"})
    client.post("/api/guardian/draft", json={"user_id": "user-1", "merchant": "Netflix"})
    writes = _write_calls
    assert writes, "draft creation must be the only write"
    for call in writes:
        assert call[0] in ("create_action_draft", "update_action_status"), \
            f"unexpected write call: {call}"
    # No user contact, no transaction mutation, no recurring mutation exists.
    assert not hasattr(guardian, "cancel")
    assert not hasattr(guardian, "contact")
    assert not hasattr(guardian, "execute")


# --- orchestrator: deterministic answers + fallback -----------------------------

def _orchestrator_fakes(monkeypatch):
    monkeypatch.setattr("app.db.get_user_by_id", lambda uid: USER if uid == "user-1" else None)
    monkeypatch.setattr("app.db.create_agent_run", lambda uid, q, intent=None: "run-g")
    monkeypatch.setattr("app.db.create_agent_tool_call", lambda run_id, tool, args: f"call-{tool}")
    monkeypatch.setattr("app.db.complete_agent_tool_call", lambda *a, **k: None)
    monkeypatch.setattr("app.db.complete_agent_run", lambda *a, **k: None)
    monkeypatch.setattr("app.db.create_action_draft",
                        lambda user_id, action_type, title, description="", payload=None: f"draft-{title[:8]}")

    def fake_tool(tool_name, user_id, args):
        if tool_name == "guardian_detect":
            return guardian.detect(user_id)
        if tool_name == "get_recurring_payments":
            return {"payment_count": 1, "monthly_committed": 649,
                    "annualized_recurring_cost": 7788, "payments": [
                        {"merchant": "Netflix", "amount": 649, "frequency": "monthly",
                         "monthly_commitment": 649, "next_payment_date": "2026-07-10"}]}
        if tool_name == "get_monthly_summary":
            return {"has_data": True, "year": 2026, "month": 5, "period_label": "May 2026",
                    "income": 65000, "expenses": 39000, "net": 26000, "savings_rate": 40.0,
                    "committed": 30649, "category_breakdown": [], "largest_expenses": [],
                    "month_over_month": {}, "insights": [], "transactions_analyzed": 55}
        return {}

    monkeypatch.setattr("app.services.orchestrator.tools.execute_tool", fake_tool)
    return fake_tool


def test_orchestrator_guardian_run_deterministic(monkeypatch):
    _orchestrator_fakes(monkeypatch)
    monkeypatch.setattr("app.services.orchestrator.get_provider", lambda: None)
    resp = orchestrator.run_agent("user-1", "Why did my Netflix subscription go up?")
    assert isinstance(resp, AgentAnalyzeResponse)
    assert resp.intent == "guardian"
    assert resp.mode == "deterministic"
    assert "Netflix" in resp.answer and "499" in resp.answer and "649" in resp.answer
    assert "1,800" in resp.answer
    assert any("1,800" in a.title or "price increase" in a.title
               for a in resp.recommended_actions)


def test_orchestrator_guardian_llm_failure_falls_back(monkeypatch):
    _orchestrator_fakes(monkeypatch)

    class Boom:
        configured = True

        def classify(self, question):
            raise LLMError("provider down")

        def plan(self, question, intent):
            raise LLMError("provider down")

    monkeypatch.setattr("app.services.orchestrator.get_provider", lambda: Boom())
    resp = orchestrator.run_agent("user-1", "Why did my Netflix subscription go up?")
    assert resp.intent == "guardian"
    assert resp.mode == "deterministic"
    assert "649" in resp.answer


def test_build_response_guardian_no_changes(mock_db, monkeypatch):
    results = {
        "guardian_detect": {
            "items": [], "summary": {"items_total": 0, "changed_count": 0},
        },
        "get_recurring_payments": {},
        "get_monthly_summary": {},
    }
    payload = orchestrator.build_response("guardian", "any changes?", results)
    assert payload["answer"]
    assert "no price changes" in payload["answer"].lower() or "no recurring" in payload["answer"].lower()