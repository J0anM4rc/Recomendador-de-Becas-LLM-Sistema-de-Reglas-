# application/pipeline/factory.py

from __future__ import annotations

from application.pipeline.context import HandlerContext
from domain.ports import (
    LLMInterface,
    ScholarshipRepository,
    IntentExtractorService,
    SlotsExtractorService,
)

# — Handlers (application layer) —
from application.pipeline.handlers.general import (
    GeneralQAHandler,
    FallbackHandler,
    IntentHandler,
    PreprocessHandler,
)
from application.pipeline.handlers.routers import (
    RouterPostIntent,
    RouterPostHistory,
)
from application.pipeline.handlers.usecases.criteria import (
    StartCriteriaHandler,
    CollectCriteriaHandler,
    ConfirmCriteriaHandler,
    CriteriaHandler,
)
from application.pipeline.handlers.usecases.scholarship import (
    RequirementsHandler,
    DeadlinesHandler,
)


def build_pipeline(
    *,
    llm: LLMInterface,
    repository: ScholarshipRepository,
    intent_clf: IntentExtractorService,
    slots_clf: SlotsExtractorService,
) -> PreprocessHandler:
    """
    Composición de la cadena de handlers sin importar detalles de infraestructura.
    Quien llame debe inyectar:
      - llm:       un LLMInterface concreto
      - repository: un ScholarshipRepository concreto
      - intent_clf:  un IntentClassifierService concreto
      - slots_clf:   un SlotsExtractorService concreto
    """
    # 1) Use-case: Criteria
    start_handler = StartCriteriaHandler(slot_extractor=slots_clf)
    collect_handler = CollectCriteriaHandler(slot_extractor=slots_clf)
    confirm_handler = ConfirmCriteriaHandler(
        slot_extractor=slots_clf,
        scholarship_repository=repository,
    )

    intent_handler = IntentHandler(
        classifier=intent_clf,
        fallback=None,  # se poblara tras crear router_post_intent
    )

    criteria_handler = CriteriaHandler(
        start_handler=start_handler,
        collect_handler=collect_handler,
        confirm_handler=confirm_handler,
        intent_handler=intent_handler,
    )

    # 2) Use-case: Scholarship
    requirements_handler = RequirementsHandler(
        scholarship_repository=repository,
        name_extractor=slots_clf,
    )
    deadlines_handler = DeadlinesHandler(
        scholarship_repository=repository,
        name_extractor=slots_clf,
    )

    # 3) Handlers generales
    general_handler = GeneralQAHandler(llm=llm)
    fallback_handler = FallbackHandler()

    # 4) Routers
    router_post_intent = RouterPostIntent(
        criteria_handler=criteria_handler,
        requirements_handler=requirements_handler,
        deadlines_handler=deadlines_handler,
        general_handler=general_handler,
        fallback=fallback_handler,
    )
    # cerramos el círculo
    intent_handler.fallback = router_post_intent

    router_post_history = RouterPostHistory(
        criteria_handler=criteria_handler,
        requirements_handler=requirements_handler,
        deadlines_handler=deadlines_handler,
        intent_handler=intent_handler,
    )

    # 5) Punto de entrada único
    return PreprocessHandler(next_handler=router_post_history)
