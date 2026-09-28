# AI Use

## 1. What did I use AI for, and what did I do myself?

I used ChatGPT/Codex to help read the assignment, plan the work, draft code, explain errors, and suggest test commands. I ran the commands myself, reviewed the code, tested the application, collected the measurements, checked the results, and took the screenshots.

## 2. What AI-produced output was wrong or unsuitable?

The first RAG setup used the text2text-generation pipeline with Transformers 5.17.0. That version did not support this pipeline name, so the program stopped with an "Unknown task" error.

## 3. How did I detect or verify the problem?

I read the terminal traceback. It listed the supported tasks and showed that text2text-generation was missing. I also ran pip check and printed the installed package versions.

## 4. What did I change, and why does it work now?

I installed Transformers 4.57.1, sentence-transformers 5.1.2, and sentencepiece 0.2.2. These versions work together and support the FLAN-T5 pipeline. After the change, pip check reported no broken requirements and the RAG experiment completed with 36 results.
