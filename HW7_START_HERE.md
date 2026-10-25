# HW7 Start Here

This package extends the existing DATA 260 clinical-trials repository without copying the HW1-HW6 code. The implementation is organized under `code/hw7/` and keeps the earlier session files as historical code.

## Local run

```bash
cd ~/data260-8561
conda activate data260
python code/hw7/run_hw7.py
python verify_hw07.py
python code/web_application/migrate_hw7.py
python code/web_application/seed_hw7_users.py
```

The database migration must run against the existing MySQL database before starting the web API. It adds `users.username` and `users.role` and does not delete data.

## Role test accounts

All three seeded accounts use `Password8561!`: `reader8561`, `writer8561`, and `moderator8561`.

## Remaining evidence

The generated raw metrics and smoke-test JSON are in `reports/hw07/`. The final PDF still needs screenshots from the user's local terminal/browser because those screenshots must show the student's name and the real MySQL/Ollama run.
