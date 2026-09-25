from uuid import NAMESPACE_URL, UUID, uuid5

from sqlmodel import Session, SQLModel, select

from mathutrice import models
from mathutrice.database import engine
from mathutrice.referentiel import REFERENTIEL

# Descriptions des notions, indexées par clé du REFERENTIEL.
DESCRIPTIONS = {
    "trigonometrie": "Étude des fonctions trigonométriques, des angles et du cercle trigonométrique.",
    "fractions_puissances_radicaux": "Manipulation des fractions, puissances et radicaux.",
    "logarithme_exponentielle": "Étude des fonctions logarithme et exponentielle.",
    "manipulation_expressions_litterales": "Isolement et manipulation de variables dans des expressions algébriques.",
    "equations_inequations": "Résolution d'équations et d'inéquations du premier et second degré.",
    "polynomes_factorisation": "Étude des polynômes, factorisation et identités remarquables.",
    "analyse_dimensionnelle": "Dimensions, unités et homogénéité des formules physiques.",
}


def _stable_id(kind: str, key: str) -> UUID:
    """UUID déterministe : le même code du REFERENTIEL donne le même id dans toute base."""
    return uuid5(NAMESPACE_URL, f"mathutrice:{kind}:{key}")


def seed_referentiel(session: Session, referentiel: dict = REFERENTIEL) -> None:
    """
    Insère les notions et compétences du REFERENTIEL. Idempotent : les lignes
    déjà présentes (repérées par referentiel_key / referentiel_code) sont conservées.
    """
    notions = {n.referentiel_key: n for n in session.exec(select(models.Notion))}
    codes = set(session.exec(select(models.Competence.referentiel_code)))

    for key, data in referentiel.items():
        notion = notions.get(key)
        if notion is None:
            notion = models.Notion(
                notion_id=_stable_id("notion", key),
                referentiel_key=key,
                title=data["notion_nom"],
                description=DESCRIPTIONS.get(key, ""),
            )
            session.add(notion)

        for comp in data["competences"]:
            if comp["code"] in codes:
                continue
            session.add(
                models.Competence(
                    competence_id=_stable_id("competence", comp["code"]),
                    referentiel_code=comp["code"],
                    title=comp["nom"],
                    level=comp["niveau"],
                    notion_id=notion.notion_id,
                )
            )
            codes.add(comp["code"])
    session.commit()


if __name__ == "__main__":
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_referentiel(session)
    print("Notions et compétences insérées.")
