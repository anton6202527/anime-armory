# n2d-batch 生产治理

- 状态：critical
- 任务数：2
- 重试率：0.5
- 死信：1

## 违规

- critical dead_letters: {'level': 'critical', 'kind': 'dead_letters', 'value': 1, 'threshold': 0}
- warn retry_rate: {'level': 'warn', 'kind': 'retry_rate', 'value': 0.5, 'threshold': 0.35}
- warn attempts: {'level': 'warn', 'kind': 'attempts', 'task_id': '001-image-rerun', 'value': 5, 'threshold': 3}

## Dead Letter

- 001-image-rerun 第1集 image command_failed: exit_code=1
