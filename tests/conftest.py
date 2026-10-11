"""
Runs before the project is first imported, so the suite needs no `.env`
(CI has none) and can never reach a real LLM endpoint.
"""

import os

import dotenv

# The project calls load_dotenv() on import: a local `.env` must not leak a
# real endpoint or key into the tests.
dotenv.load_dotenv = lambda *args, **kwargs: False

# llm_client refuses to import without these (ADR 0002). Dummy values only.
os.environ["LLM_BASE_URL"] = "http://llm-endpoint.invalid/v1"
os.environ["LLM_API_KEY"] = "dummy-key"
os.environ["LLM_MODEL"] = "dummy-model"
