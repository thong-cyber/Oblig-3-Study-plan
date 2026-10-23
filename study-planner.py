#!/usr/bin/env python3
"""Study Planner - spreads your study hours across the days before each deadline.

Usage examples:
  python study_planner.py add "Calculus exam" 2026-11-12 --hours 20 --priority 3
  python study_planner.py add "Essay draft" 2026-11-05 --hours 8
  python study_planner.py list
  python study_planner.py plan --per-day 3 --days 7
  python study_planner.py log "Calculus exam" 1.5
  python study_planner.py progress
  python study_planner.py remove "Essay draft"

Data is stored in ~/.study_planner.json (override with STUDY_PLANNER_FILE).
Standard library only, Python 3.8+.
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta

DATA_FILE = os.environ.get("STUDY_PLANNER_FILE", os.path.expanduser("~/.study_planner.json"))
BLOCK = 0.5  # scheduling granularity in hours


# ---------- storage ----------
def load():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def save(tasks):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


def parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{s}' is not a date in YYYY-MM-DD format")


def find(tasks, name):
    matches = [t for t in tasks if name.lower() in t["name"].lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        sys.exit(f"No task matches '{name}'.")
    sys.exit("Ambiguous name, matches: " + ", ".join(t["name"] for t in matches))


def remaining(t):
    return max(0.0, t["hours"] - t["done"])


# ---------- commands ----------
def cmd_add(args, tasks):
    if args.due < date.today():
        sys.exit("Due date is in the past.")
    tasks.append({"name": args.name, "due": args.due.isoformat(),
                  "hours": args.hours, "done": 0.0, "priority": args.priority})
    save(tasks)
    print(f"Added '{args.name}' ({args.hours}h, due {args.due}, priority {args.priority}).")


def cmd_list(args, tasks):
    if not tasks:
        print("No tasks yet. Add one with the 'add' command.")
        return
    today = date.today()
    print(f"{'Task':<28}{'Due':<12}{'Days':>5}{'Left h':>8}{'Prio':>6}")
    for t in sorted(tasks, key=lambda t: t["due"]):
        days = (date.fromisoformat(t["due"]) - today).days
        print(f"{t['name'][:27]:<28}{t['due']:<12}{days:>5}{remaining(t):>8.1f}{t['priority']:>6}")


def build_plan(tasks, per_day, horizon):
    """Rate-based scheduler.
    1. Each day, every task first gets the hours it needs to stay on track
       (remaining / days left, rounded up to 0.5h), nearest deadline first.
    2. Any hours still free go to the highest-priority task that still has work.
    """
    import math
    today = date.today()
    left = {t["name"]: remaining(t) for t in tasks}
    plan, warnings = {}, []
    for offset in range(horizon):
        day = today + timedelta(days=offset)
        budget, slots = per_day, {}
        live = [t for t in tasks if left[t["name"]] > 0 and date.fromisoformat(t["due"]) >= day]

        def give(t, hours):
            nonlocal budget
            h = min(hours, left[t["name"]], budget)
            if h <= 0:
                return
            slots[t["name"]] = slots.get(t["name"], 0) + h
            left[t["name"]] -= h
            budget -= h

        for t in sorted(live, key=lambda t: t["due"]):
            days_left = (date.fromisoformat(t["due"]) - day).days + 1
            need = math.ceil(left[t["name"]] / days_left / BLOCK) * BLOCK
            give(t, need)
        for t in sorted(live, key=lambda t: (-t["priority"], t["due"])):
            give(t, budget)
        plan[day] = slots
    for t in tasks:
        due = date.fromisoformat(t["due"])
        if left[t["name"]] > 0 and (due - today).days < horizon:
            warnings.append(f"'{t['name']}' is short by {left[t['name']]:.1f}h before {t['due']} "
                            f"- raise --per-day or reduce the scope.")
    return plan, warnings


def cmd_plan(args, tasks):
    active = [t for t in tasks if remaining(t) > 0 and date.fromisoformat(t["due"]) >= date.today()]
    if not active:
        print("Nothing to plan - all tasks are done or past due.")
        return
    plan, warnings = build_plan(active, args.per_day, args.days)
    for day, slots in plan.items():
        label = day.strftime("%a %d %b")
        if not slots:
            print(f"{label}: free day")
            continue
        items = ", ".join(f"{n} ({h:g}h)" for n, h in slots.items())
        print(f"{label}: {items}")
    for w in warnings:
        print("WARNING:", w)


def cmd_log(args, tasks):
    t = find(tasks, args.name)
    t["done"] = round(t["done"] + args.hours, 2)
    save(tasks)
    print(f"Logged {args.hours}h on '{t['name']}'. {remaining(t):.1f}h left.")


def cmd_progress(args, tasks):
    if not tasks:
        print("No tasks yet.")
        return
    for t in sorted(tasks, key=lambda t: t["due"]):
        pct = min(1.0, t["done"] / t["hours"]) if t["hours"] else 1.0
        bar = "#" * int(pct * 20)
        print(f"{t['name'][:24]:<25}[{bar:<20}] {pct:>4.0%}  ({t['done']:g}/{t['hours']:g}h)")


def cmd_remove(args, tasks):
    t = find(tasks, args.name)
    tasks.remove(t)
    save(tasks)
    print(f"Removed '{t['name']}'.")


def main():
    p = argparse.ArgumentParser(description="Deadline-aware study planner")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="add a task or exam")
    a.add_argument("name")
    a.add_argument("due", type=parse_date, help="YYYY-MM-DD")
    a.add_argument("--hours", type=float, required=True, help="total study hours needed")
    a.add_argument("--priority", type=int, choices=[1, 2, 3], default=2, help="1 low, 3 high")
    a.set_defaults(fn=cmd_add)

    sub.add_parser("list", help="show all tasks").set_defaults(fn=cmd_list)

    pl = sub.add_parser("plan", help="generate a daily schedule")
    pl.add_argument("--per-day", type=float, default=3.0, help="study hours available per day")
    pl.add_argument("--days", type=int, default=7, help="days to plan ahead")
    pl.set_defaults(fn=cmd_plan)

    lg = sub.add_parser("log", help="log hours studied")
    lg.add_argument("name")
    lg.add_argument("hours", type=float)
    lg.set_defaults(fn=cmd_log)

    sub.add_parser("progress", help="show progress bars").set_defaults(fn=cmd_progress)

    rm = sub.add_parser("remove", help="delete a task")
    rm.add_argument("name")
    rm.set_defaults(fn=cmd_remove)

    args = p.parse_args()
    args.fn(args, load())


if __name__ == "__main__":
    main()