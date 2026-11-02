# Screenshot checklist

Use the exact labels below in the report. Every terminal screenshot must show
`Haozhe Wang` or the terminal prompt containing `haozhewang`.

1. `P1_01_docker_ps.png` - Kafka, worker, and FastAPI running.
2. `P1_02_worker_fastapi_ready.png` - worker ready and FastAPI on port 8461.
3. `P1_03_create_trial.png` - CREATE_TRIAL request, UUID, success, correlation ID.
4. `P1_04_get_trial.png` - GET_TRIAL request, returned entity, correlation ID.
5. `P1_05_full_rpc_sequence.png` - client → request topic → worker → response topic → client.
6. `P2_01_agents_running.png` - Planner, Writer, Reviewer, sender terminals.
7. `P2_02_agent_pipeline.png` - inbox → tasks → drafts → final.
8. `P3_01_duplicate_before_after.png` - replay and idempotent result.
9. `P3_02_consumer_death_before_after.png` - kill, restart, redelivery, commit.
10. `P3_03_poison_before_after.png` - retries, DLQ, later message.
11. `P3_04_ordering_before_after.png` - no key versus entity key.
12. `P4_01_verification_tag.png` - verification output and `hw8` tag.

## Part 3 commands

- Duplicate: `python replay_request.py`; repeat with `IDEMPOTENCY_ENABLED=0` for the before-fix run.
- Consumer death: start Writer with `WRITER_PAUSE_SECONDS=30 python writer.py`, send a task, then kill it during the pause and restart it.
- Poison: start Writer, then run `python send_poison.py`.
- Ordering: start two Writers in the same group, then run `python ordering_experiment.py`.
