# eba-py

进程内、单写者、合作式的 EBA 运行时。

- 一次 request 交给每一台受理它的 Host 执行；调用方认领最先到的合法结果，后来的交付错误换不掉它。副作用是否幂等由应用负责，超时只结清本地这一次等待。
- 回调同步结束：定论由写下它的那一步直接送出；正文在各 Job 之间共享；一次 `advance` 的预算按每台 Host 单独计算。
- 一台运行时只有一位 `Caller`（actor id 固定为 `caller`），请求人身份由每次调用的 `from_` 承载。
- 队列满又押着回信时，新业务发布以 `MailboxFull` 拒绝；停着的回信让开之后，多余的才得到 `queue_full`；容量恢复后继续接收和开工。
- 结果投递失败只重试一次，第二次把原信埋没、关闭时交还，并在同一次推进里以 `delivery_failed` 结清它所回答的等待。
- 根回复被框架保存后就占用一次回复名额；同一主题只在同一个出箱组内按进入顺序发出。
- 钩子既不回信也不发起请求、账上也没有还在等的段时，框架替它补一份 `job_silent` 错误答复。
- 没人接住又没设期限的 request 把期限就地记为已过，交回空的结局；`Bus.publish` 返回 `None` 按已投递处理。

```text
PYTHONPATH=. python3 examples/order.py
PYTHONPATH=. python3 examples/bus.py
python3 -m mypy eba && python3 -m ruff check .
```

支持 3.11 起的每个 Python 系列（3.11、3.12、3.13、3.14）。
