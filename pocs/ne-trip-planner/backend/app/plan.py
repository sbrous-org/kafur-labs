"""Shared itinerary: pure functions that validate and apply plan operations."""
import copy
import uuid

MAX_DAYS, MAX_ITEMS = 14, 60


def empty() -> dict:
    return {"days": []}


def _day(plan: dict, n: int, create: bool) -> dict | None:
    for d in plan["days"]:
        if d["n"] == n:
            return d
    if not create:
        return None
    d = {"n": n, "title": f"Day {n}", "items": []}
    plan["days"].append(d)
    plan["days"].sort(key=lambda x: x["n"])
    return d


def _find(plan: dict, item_id: str):
    for d in plan["days"]:
        for i, it in enumerate(d["items"]):
            if it["id"] == item_id:
                return d, i
    return None, None


def _clean(day_list: dict) -> None:
    day_list["days"] = [d for d in day_list["days"] if d["items"] or d.get("title", "") != f"Day {d['n']}"]


def apply_ops(plan: dict, ops: list, author: str, human: bool = False, valid_kb: set[str] | None = None) -> tuple[dict, int, list[str]]:
    """Return (new_plan, applied_count, errors). Humans may only remove/move; the bot may add/day_title too."""
    plan = copy.deepcopy(plan)
    applied, errors = 0, []
    for op in ops[:12] if isinstance(ops, list) else []:
        if not isinstance(op, dict):
            continue
        kind = op.get("op")
        try:
            if kind == "add" and not human:
                day = int(op["day"])
                title = str(op["title"]).strip()[:80]
                if not (1 <= day <= MAX_DAYS) or not title:
                    raise ValueError("bad day/title")
                if sum(len(d["items"]) for d in plan["days"]) >= MAX_ITEMS:
                    raise ValueError("plan full")
                kb_id = op.get("kb_id") if (valid_kb is None or op.get("kb_id") in valid_kb) else None
                if kb_id and any(it.get("kb_id") == kb_id for d in plan["days"] for it in d["items"]):
                    raise ValueError("already in plan")
                _day(plan, day, True)["items"].append(
                    {"id": uuid.uuid4().hex[:6], "title": title, "note": str(op.get("note", ""))[:200],
                     "kb_id": kb_id, "added_by": author})
            elif kind == "remove":
                d, i = _find(plan, str(op["id"]))
                if d is None:
                    raise ValueError("no such item")
                d["items"].pop(i)
            elif kind == "move":
                d, i = _find(plan, str(op["id"]))
                day = int(op["day"])
                if d is None or not (1 <= day <= MAX_DAYS):
                    raise ValueError("bad move")
                it = d["items"].pop(i)
                _day(plan, day, True)["items"].append(it)
            elif kind == "day_title" and not human:
                day = int(op["day"])
                if not (1 <= day <= MAX_DAYS):
                    raise ValueError("bad day")
                _day(plan, day, True)["title"] = str(op["title"]).strip()[:60] or f"Day {day}"
            else:
                raise ValueError(f"unsupported op {kind!r}")
            applied += 1
        except (KeyError, ValueError, TypeError) as e:
            errors.append(f"{kind}: {e}")
    _clean(plan)
    return plan, applied, errors


def to_text(plan: dict) -> str:
    if not plan["days"]:
        return "No plan yet."
    out = []
    for d in plan["days"]:
        out.append(f"Day {d['n']} - {d['title']}")
        for it in d["items"]:
            out.append(f"  - {it['title']}" + (f" ({it['note']})" if it["note"] else ""))
    return "\n".join(out)


def compact(plan: dict) -> str:
    """Compact representation for the prompt (small models like short context)."""
    if not plan["days"]:
        return "(empty)"
    return "\n".join(f"Day {d['n']} {d['title']}: " + "; ".join(f"{it['title']} [item:{it['id']}]" for it in d["items"])
                     for d in plan["days"])
