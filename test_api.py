# test_api.py - Direct API Function & Database Integration Tests
import os
import sys
import time

# Ensure UTF-8 output on Windows
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import db
import main
from main import (
    ReactionRequest, CommentRequest, SubscriptionRequest,
    UserActivityRequest, FeedbackRequest, TranslationRequest,
    post_reaction, get_reactions_summary, post_comment, list_comments,
    post_subscription, get_subscriptions, cancel_subscription,
    post_user_activity, get_user_activity_data, post_feedback,
    get_analytics, get_topic_detail, list_topics
)

def test_full_service_loop():
    user_id = f"test-citizen-uuid-{int(time.time() * 1000)}"

    print("--- 1. Database Init & Topics ---")
    topic = get_topic_detail("shinagawa-childcare-2026-001")
    assert topic.municipality.name == "品川区"
    assert len(topic.lifecycle) == 5
    initial_agree = topic.reactions["agree"]
    print(f"[OK] Topic fetched. Initial agree count: {initial_agree}")

    print("--- 2. Post Reaction (Agree) ---")
    req = ReactionRequest(
        user_id=user_id,
        topic_id="shinagawa-childcare-2026-001",
        assembly_id="shinagawa-ward",
        statement_id="",
        reaction_type="agree"
    )
    res = post_reaction(req)
    assert res["status"] == "success"
    assert res["data"]["user_reaction"] == "agree"
    print("[OK] Reaction posted and saved to DB")

    print("--- 3. Toggle / Update Reaction (Change to Concern) ---")
    req = ReactionRequest(
        user_id=user_id,
        topic_id="shinagawa-childcare-2026-001",
        assembly_id="shinagawa-ward",
        statement_id="",
        reaction_type="concern"
    )
    res = post_reaction(req)
    assert res["status"] == "success"
    assert res["data"]["user_reaction"] == "concern"
    print("[OK] Reaction successfully updated without duplication")

    print("--- 4. Toggle Reaction Cancellation ---")
    req_cancel = ReactionRequest(
        user_id=user_id,
        topic_id="shinagawa-childcare-2026-001",
        assembly_id="shinagawa-ward",
        statement_id="",
        reaction_type="concern"
    )
    res_cancel = post_reaction(req_cancel)
    assert res_cancel["status"] == "success"
    assert res_cancel["data"]["user_reaction"] is None
    print("[OK] Reaction toggled off correctly")

    print("--- 5. Statement-level Reaction (Struggling) ---")
    req_s = ReactionRequest(
        user_id=user_id,
        topic_id="shinagawa-childcare-2026-001",
        assembly_id="shinagawa-ward",
        statement_id="shinagawa-morisawa-01",
        reaction_type="struggling"
    )
    res_s = post_reaction(req_s)
    assert res_s["status"] == "success"
    assert res_s["data"]["user_reaction"] == "struggling"
    print("[OK] Statement level reaction persisted")

    print("--- 6. Post Citizen Comment ---")
    c_req = CommentRequest(
        user_id=user_id,
        user_name="品川区在住ママ",
        topic_id="shinagawa-childcare-2026-001",
        assembly_id="shinagawa-ward",
        statement_id="shinagawa-morisawa-01",
        comment_text="給食費とおむつ支援は本当に助かるので継続を強く希望します！"
    )
    c_res = post_comment(c_req)
    assert c_res["status"] == "success"
    assert c_res["data"]["comment_text"] == "給食費とおむつ支援は本当に助かるので継続を強く希望します！"
    print("[OK] Citizen comment saved to DB")

    print("--- 7. Subscribe to Update Notification ---")
    s_req = SubscriptionRequest(
        user_id=user_id,
        assembly_id="shinagawa-ward",
        theme="child",
        email="user@example.com",
        notify_type="browser"
    )
    s_res = post_subscription(s_req)
    assert s_res["status"] == "success"
    assert s_res["data"]["is_active"] is True
    print("[OK] Notification subscription persisted in DB")

    subs_res = get_subscriptions(user_id=user_id)
    assert subs_res["status"] == "success"
    assert len(subs_res["data"]) >= 1
    print(f"[OK] Retrieved {len(subs_res['data'])} active subscriptions for user")

    print("--- 8. Admin Analytics reflecting live DB reactions ---")
    analytics_res = get_analytics("shinagawa-ward")
    assert analytics_res["status"] == "success"
    live_reactions = analytics_res["data"]["ebpm_citizen_data"]["live_db_reactions"]
    print(f"[OK] Live DB Reactions for Shinagawa Ward in EBPM Analytics: {live_reactions}")
    assert live_reactions["total_reactions"] > 0

    print("--- 9. User Activity & History ---")
    act_req = UserActivityRequest(
        user_id=user_id,
        topic_id="shinagawa-childcare-2026-001",
        last_assembly_id="shinagawa-ward",
        last_theme="child"
    )
    post_user_activity(act_req)

    user_data = get_user_activity_data(user_id=user_id)
    assert user_data["status"] == "success"
    assert "shinagawa-childcare-2026-001" in user_data["activity"]["viewed_topics"]
    assert len(user_data["reactions"]) >= 1
    print("[OK] User state and activity verified successfully")

    print("--- 10. Post Feedback / Report ---")
    f_req = FeedbackRequest(
        user_id=user_id,
        category="feedback",
        content="発言の要旨がわかりやすく助かります。他の市区町村も増やしてください。",
        assembly_id="shinagawa-ward"
    )
    f_res = post_feedback(f_req)
    assert f_res["status"] == "success"
    print("[OK] Feedback saved to DB")

    print("\n=============================================")
    print("ALL BACKEND INTEGRATION TESTS PASSED 100%!")
    print("=============================================\n")

if __name__ == "__main__":
    test_full_service_loop()
