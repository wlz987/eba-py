# eba-py

Python 端口：进程内、单写者、合作式的 EBA 运行时。`python -m mypy eba` 与 `python -m ruff check .` 自查。

信任边界：Bus 上的 host 互信；`from_` 由发送者自填，不用于不可信插件或多租户隔离。
