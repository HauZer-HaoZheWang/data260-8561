import asyncio
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from common import BOOTSTRAP, DRAFTS, DLQ, FINAL, INBOX, REQUESTS, RESPONSES, TASKS


async def main():
    admin = AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP)
    await admin.start()
    try:
        topics = [
            NewTopic(REQUESTS, 1, 1), NewTopic(RESPONSES, 1, 1),
            NewTopic(INBOX, 1, 1), NewTopic(TASKS, 2, 1),
            NewTopic(DRAFTS, 1, 1), NewTopic(FINAL, 1, 1),
            NewTopic(DLQ, 1, 1),
        ]
        try:
            await admin.create_topics(topics)
        except Exception as exc:
            if "TopicExists" not in str(exc):
                raise
        print("Created or confirmed HW8 topics:", ", ".join(t.name for t in topics))
    finally:
        await admin.close()


if __name__ == "__main__":
    asyncio.run(main())
