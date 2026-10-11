"""
llm_client.py — Client LLM partagé (API compatible OpenAI)

Point d'entrée unique vers le LLM. Le endpoint, la clé et le modèle viennent
uniquement des settings, sans valeur par défaut dans le code :
  - LLM_BASE_URL : endpoint compatible OpenAI
  - LLM_API_KEY  : clé de ce endpoint
  - LLM_MODEL    : modèle servi par ce endpoint

DeadlineClient tient le délai d'un test d'évaluation (#86) : 5 minutes pour
tous les appels du test, retries compris.
"""

import logging
import os
from typing import Callable

from dotenv import load_dotenv
from openai import APITimeoutError, OpenAI

load_dotenv()

_missing = [
    name
    for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
    if not os.getenv(name)
]

if _missing:
    raise ValueError(f"{', '.join(_missing)} missing")

MODEL = os.environ["LLM_MODEL"]

client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
)


logger = logging.getLogger(__name__)

# Un test d'évaluation se termine en 5 minutes au plus (hypothèse D, #61).
EVALUATION_TEST_DEADLINE_SECONDS = 5 * 60


class DeadlineReached(Exception):
    """Le délai du test d'évaluation est atteint : aucun appel ne sera relancé.

    Distincte de ValueError (sortie invalide), pour que la boucle des 3
    tentatives des générateurs ne la rattrape pas.
    """


class DeadlineClient:
    """Client LLM d'un test d'évaluation, sous un seul délai de 5 minutes.

    Le délai démarre à la construction et vaut pour tous les appels faits
    ensuite. Chaque appel n'a que le temps restant, sans retry de la
    bibliothèque. Une fois le délai passé, plus aucun appel ne part.

      client : client compatible OpenAI (celui des settings en production)
      clock  : horloge en secondes (time.monotonic en production)
    """

    def __init__(self, client: OpenAI, clock: Callable[[], float]):
        self._client = client
        self._clock = clock
        self._deadline = clock() + EVALUATION_TEST_DEADLINE_SECONDS
        self._calls = 0

    def complete(self, messages: list[dict]) -> str:
        """Envoie messages au LLM et renvoie le texte de sa réponse.

        Lève DeadlineReached si le délai est passé, avant l'appel ou pendant.
        """
        time_left = self._deadline - self._clock()
        if time_left <= 0:
            self._deadline_reached()

        self._calls += 1
        try:
            response = self._client.with_options(
                timeout=time_left, max_retries=0
            ).chat.completions.create(model=MODEL, messages=messages)
        except APITimeoutError as e:
            if self._clock() >= self._deadline:
                self._deadline_reached(e)
            raise
        return response.choices[0].message.content

    def _deadline_reached(self, cause: Exception | None = None):
        logger.warning(
            f"Délai de {EVALUATION_TEST_DEADLINE_SECONDS} s atteint "
            f"après {self._calls} appel(s) au LLM"
        )
        raise DeadlineReached(
            f"délai de {EVALUATION_TEST_DEADLINE_SECONDS} s atteint"
        ) from cause
