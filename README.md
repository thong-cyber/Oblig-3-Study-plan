# Study Planner (web prototype)

A small Flask website that solves a common student problem: how many hours should I study today
so that every deadline is met? Add tasks with a due date, the hours they need and a priority, and
the app builds a daily plan, tracks your progress and warns you when a deadline can't be reached.

## Run it

```
1. Go in to folder (cd) with app.py
   Can check with ls
2. Create virtual envirorment 
   python3 -m venv .venv
   source .venv/bin/activate
      both in terminal
3. Install flask
   pip install -r requirements.txt
      In terminal
4. Start app
   python app.py
      in terminal
```

Then open http://127.0.0.1:5000

## How the scheduling works

For each day in the plan:

1. Every task gets the hours it needs to stay on track (remaining hours / days left, rounded up
   to 0.5h), nearest deadline first.
2. Any leftover hours go to the highest-priority task that still has work.

If a deadline can't be met with your daily hours, a warning explains how many hours are missing.

## Files

- `app.py` – Flask routes (add, log hours, remove, show plan)
- `planner.py` – storage (JSON file) and the scheduling algorithm
- `templates/index.html`, `static/style.css` – the page

Tasks are stored in `tasks.json` next to the app (ignored by git).
