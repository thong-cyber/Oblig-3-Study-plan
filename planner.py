"""Core logic for the study planner: storage and the scheduling algorithm."""
import json
import math
import os
import uuid
from datetime import date, timedelta

DATA_FILE = os.environ.get(
    "STUDY_PLANNER_FILE", os.path.join(os.path.dirname(__file__), "tasks.json")
)
BLOCK = 0.5  # scheduling granularity in hours


# ---------- storage ----------
def load_tasks():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_tasks(tasks):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


def add_task(name, due, hours, priority):
    tasks = load_tasks()
    tasks.append({
        "id": uuid.uuid4().hex[:8],
        "name": name.strip(),
        "due": due.isoformat(),
        "hours": hours,
        "done": 0.0,
        "priority": priority,
    })
    save_tasks(tasks)


def log_hours(task_id, hours):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = round(t["done"] + hours, 2)
    save_tasks(tasks)


def delete_task(task_id):
    save_tasks([t for t in load_tasks() if t["id"] != task_id])


# ---------- helpers ----------
def remaining(t):
    return max(0.0, t["hours"] - t["done"])


def percent_done(t):
    return min(100, round(100 * t["done"] / t["hours"])) if t["hours"] else 100


def days_left(t, today=None):
    return (date.fromisoformat(t["due"]) - (today or date.today())).days


# ---------- scheduler ----------
def build_plan(tasks, per_day, horizon, today=None):
    """Rate-based scheduler.

    1. Each day every task first gets the hours it needs to stay on track
       (remaining / days left, rounded up to 0.5h), nearest deadline first.
    2. Any hours still free go to the highest-priority task with work left.

    Returns (plan, warnings). plan is a list of (day, [(task, hours), ...]).
    """
    today = today or date.today()
    active = [t for t in tasks if remaining(t) > 0 and date.fromisoformat(t["due"]) >= today]
    left = {t["id"]: remaining(t) for t in active}
    plan = []

    for offset in range(horizon):
        day = today + timedelta(days=offset)
        budget = per_day
        slots = {}
        live = [t for t in active if left[t["id"]] > 0 and date.fromisoformat(t["due"]) >= day]

        def give(t, hours):
            nonlocal budget
            h = min(hours, left[t["id"]], budget)
            if h <= 0:
                return
            slots[t["id"]] = slots.get(t["id"], 0) + h
            left[t["id"]] -= h
            budget -= h

        for t in sorted(live, key=lambda t: t["due"]):
            dl = (date.fromisoformat(t["due"]) - day).days + 1
            give(t, math.ceil(left[t["id"]] / dl / BLOCK) * BLOCK)
        for t in sorted(live, key=lambda t: (-t["priority"], t["due"])):
            give(t, budget)

        by_id = {t["id"]: t for t in active}
        plan.append((day, [(by_id[i], h) for i, h in slots.items()]))

    warnings = []
    for t in active:
        if left[t["id"]] > 0 and days_left(t, today) < horizon:
            warnings.append(
                f"“{t['name']}” is short by {left[t['id']]:g}h before {t['due']}. "
                "Increase your daily hours or reduce the scope."
            )
    return plan, warnings
