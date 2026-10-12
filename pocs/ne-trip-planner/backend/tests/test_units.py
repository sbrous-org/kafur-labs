from app import plan as P
from app.bot import parse_output
from app.embeddings import hash_embed
from app.kb import detect_states


def test_parse_output_with_and_without_plan():
    r, ops = parse_output('Hi there [x].\n###PLAN\n{"ops":[{"op":"add","day":1,"title":"A"}]}')
    assert r == "Hi there [x]." and ops[0]["title"] == "A"
    assert parse_output("just text") == ("just text", [])
    assert parse_output("t\n###PLAN\nnot json at all")[1] == []


def test_plan_ops_validation():
    p, n, err = P.apply_ops(P.empty(), [
        {"op": "add", "day": 1, "title": "Kaziranga", "kb_id": "kaziranga"},
        {"op": "add", "day": 99, "title": "bad day"},
        {"op": "add", "day": 2, "title": "X", "kb_id": "made-up"},
        {"op": "add", "day": 1, "title": "dup", "kb_id": "kaziranga"},
    ], "Bot", valid_kb={"kaziranga"})
    assert n == 2 and len(err) == 2
    assert p["days"][1]["items"][0]["kb_id"] is None  # unknown kb ids are dropped, not trusted
    iid = p["days"][0]["items"][0]["id"]
    p2, n2, _ = P.apply_ops(p, [{"op": "add", "day": 1, "title": "x"}, {"op": "move", "id": iid, "day": 3}], "Ravi", human=True)
    assert n2 == 1 and any(d["n"] == 3 for d in p2["days"])  # humans cannot add; can move


def test_hash_embed_is_normalised_and_deterministic():
    a, b = hash_embed("tiger safari assam", 64), hash_embed("tiger safari assam", 64)
    assert a == b and abs(sum(x * x for x in a) - 1) < 1e-6


def test_state_detection():
    assert detect_states("we love Shillong and the Tawang monastery") == {"Meghalaya", "Arunachal Pradesh"}
