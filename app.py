"""Flask web app for the study planner.  Run:  python app.py  ->  http://127.0.0.1:5000"""
from datetime import date

from flask import Flask, flash, redirect, render_template, request, url_for

import planner

app = Flask(__name__)
app.secret_key = "dev-only-change-me"  # needed for flash messages; fine for a local prototype


@app.template_filter("fmt")
def fmt(value):
    return f"{value:g}"


@app.route("/")
def index():
    per_day = request.args.get("per_day", 3, type=float)
    horizon = request.args.get("days", 7, type=int)
    per_day = min(max(per_day, 0.5), 16)
    horizon = min(max(horizon, 1), 30)

    tasks = sorted(planner.load_tasks(), key=lambda t: t["due"])
    plan, warnings = planner.build_plan(tasks, per_day, horizon)
    return render_template(
        "index.html",
        tasks=tasks, plan=plan, warnings=warnings,
        per_day=per_day, horizon=horizon, today=date.today(),
        remaining=planner.remaining, percent=planner.percent_done, days_left=planner.days_left,
    )


@app.post("/add")
def add():
    name = request.form.get("name", "").strip()
    try:
        due = date.fromisoformat(request.form.get("due", ""))
        hours = float(request.form.get("hours", ""))
        priority = int(request.form.get("priority", 2))
    except ValueError:
        flash("Please fill in all fields with valid values.", "error")
        return redirect(url_for("index"))

    if not name:
        flash("Task name cannot be empty.", "error")
    elif due < date.today():
        flash("The due date is in the past.", "error")
    elif not 0 < hours <= 500:
        flash("Hours must be between 0 and 500.", "error")
    elif priority not in (1, 2, 3):
        flash("Priority must be 1, 2 or 3.", "error")
    else:
        planner.add_task(name, due, hours, priority)
        flash(f"Added “{name}”.", "ok")
    return redirect(url_for("index"))


@app.post("/log/<task_id>")
def log(task_id):
    try:
        hours = float(request.form.get("hours", ""))
        if not 0 < hours <= 24:
            raise ValueError
    except ValueError:
        flash("Enter hours between 0 and 24.", "error")
    else:
        planner.log_hours(task_id, hours)
        flash(f"Logged {hours:g}h.", "ok")
    return redirect(url_for("index"))


@app.post("/delete/<task_id>")
def delete(task_id):
    planner.delete_task(task_id)
    flash("Task removed.", "ok")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
