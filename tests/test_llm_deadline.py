"""
One evaluation test ends within 5 minutes (#86, Assumption D in #61).

The fake LLM endpoint sits behind a real `openai` client, so the deadline is
seen the way the LLM endpoint would see it: through the time each call is
allowed before it times out.
"""

import httpx2
import openai
import pytest

from mathutrice.llm_client import DeadlineClient, DeadlineReached

# Written out, not imported: a deadline other than 5 minutes must fail here.
FIVE_MINUTES = 4 * 60

# Measured on 25 September 2026: one call to the LLM endpoint takes about 2.3 s.
SECONDS_PER_ANSWER = 2.3


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float):
        self.now += seconds


def slow_llm_endpoint(clock: FakeClock, seconds_per_answer: float, calls_started: list):
    """An OpenAI-compatible client whose endpoint answers after `seconds_per_answer`
    by `clock`, or times out first if the call is allowed less time than that."""

    def answer(request: httpx2.Request) -> httpx2.Response:
        calls_started.append(clock())
        allowed = request.extensions["timeout"]["read"]
        if allowed is not None and allowed < seconds_per_answer:
            clock.advance(allowed)
            raise httpx2.ReadTimeout("no answer in time", request=request)
        clock.advance(seconds_per_answer)
        return httpx2.Response(
            200,
            json={
                "id": "fake",
                "object": "chat.completion",
                "created": 0,
                "model": "dummy-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "{}"},
                    }
                ],
            },
        )

    return openai.OpenAI(
        base_url="http://llm-endpoint.invalid/v1",
        api_key="dummy-key",
        http_client=httpx2.Client(transport=httpx2.MockTransport(answer)),
    )


def test_an_evaluation_test_on_a_slow_llm_endpoint_ends_with_the_deadline_within_5_minutes():
    clock = FakeClock()
    calls_started = []
    llm = DeadlineClient(
        slow_llm_endpoint(clock, SECONDS_PER_ANSWER, calls_started), clock
    )

    # 200 questions × 2.3 s = 460 s: far more work than 5 minutes allow.
    with pytest.raises(DeadlineReached):
        for question in range(200):
            llm.complete([{"role": "user", "content": f"Question {question}"}])

    # Ended at the deadline: not after it, and not one answer or more before it.
    assert FIVE_MINUTES - SECONDS_PER_ANSWER < clock() <= FIVE_MINUTES + 1e-9
    # No call was started once the deadline had passed.
    assert all(started < FIVE_MINUTES for started in calls_started)
