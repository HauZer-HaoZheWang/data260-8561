# AI Use

1. I used an AI assistant to inspect the starter repository, propose implementation structure, and review code. I ran the commands and verified the outputs myself.
2. An early assumption was that the demo authentication route could be copied directly; it was unsuitable because the homework requires MySQL users and reader/writer/moderator roles.
3. I detected this by comparing the demo schema and routes against the HW7 requirements and the existing clinical-trials schema.
4. I changed the implementation to preserve the existing domain routes, add JWT claims and role checks, and keep the old session code only as historical code.
