import os

for _k in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
    os.environ.setdefault(_k, "test")

from sqlmodel import Session, SQLModel, create_engine, select

from mathutrice import models
from mathutrice.fonctions_python.main import REFERENTIEL
from mathutrice.fonctions_python.seed import seed_referentiel


def _session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_seed_inserts_every_notion_and_competence_of_the_referentiel():
    with _session() as s:
        seed_referentiel(s)
        notions = {n.referentiel_key: n for n in s.exec(select(models.Notion))}
        comps = {c.referentiel_code: c for c in s.exec(select(models.Competence))}

    assert set(notions) == set(REFERENTIEL)
    expected = {
        c["code"]: key for key, d in REFERENTIEL.items() for c in d["competences"]
    }
    assert set(comps) == set(expected)
    for code, key in expected.items():
        assert comps[code].notion_id == notions[key].notion_id


def test_seed_is_idempotent():
    with _session() as s:
        seed_referentiel(s)
        seed_referentiel(s)
        assert len(s.exec(select(models.Notion)).all()) == len(REFERENTIEL)
        assert len(s.exec(select(models.Competence)).all()) == sum(
            len(d["competences"]) for d in REFERENTIEL.values()
        )


def test_seed_ids_are_stable_across_databases():
    ids = []
    for _ in range(2):
        with _session() as s:
            seed_referentiel(s)
            ids.append({n.referentiel_key: n.notion_id for n in s.exec(select(models.Notion))})
    assert ids[0] == ids[1]
