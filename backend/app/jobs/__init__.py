"""Background jobs — chạy trong tiến trình FastAPI qua BackgroundTasks.

Quy mô thesis (≤1500 rows) KHÔNG dùng Celery/queue ngoài scope (plan 09 §3.1):
một worker tuần tự là đủ.
"""
