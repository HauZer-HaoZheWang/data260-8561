# AI_USE

1. I used an AI assistant to inspect the HW6 specification, scaffold the MongoDB/FastAPI modules, propose schemas, and review test coverage. I wrote or verified the local environment setup, real database runs, screenshots, probe scores, and final Git submission.
2. One unsuitable initial design was treating the existing MySQL API as if it were already MongoDB-backed; the assignment requires a separate MongoDB database and collections while preserving the old application.
3. I detected the problem by inspecting the HW5 source and database module, which showed SQLAlchemy and MySQL-only configuration.
4. I changed the design to add `code/memory_application/` with independent PyMongo connection, Pydantic schemas, document routes, memory routes, and file-memory routes, while mounting those routers into the existing FastAPI app.
