# DATA 260 HW8 Kafka implementation

This folder contains the HW8 extension for the existing clinical-trial project.
It uses `Trial` as the primary entity and keeps the HW7 application unchanged.

## Configuration

`SID4=8561`, `PORT_BASE=8461`, `PREFIX=s8561`, `SEED=8561`,
`VERIFY_SEED=268561`, and `DOMAIN_ID=1`.

The local model used by the agent pipeline is `qwen3:8b` through Ollama.

## Start

From this directory, install `requirements.txt`, start the Kafka compose file,
create topics with `python create_topics.py`, then run `python trial_worker.py`.
In another terminal run `python api.py`, and finally `python homework_demo.py`.

The agent pipeline is started with `planner.py`, `writer.py`, `reviewer.py`,
and `send_question.py` in four separate terminals.
