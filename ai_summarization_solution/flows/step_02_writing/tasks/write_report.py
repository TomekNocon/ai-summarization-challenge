"""Write the initial report based on the plan."""

from ai_pipeline_core import (
    AIMessages,
    DocumentList,
    ModelName,
    PromptManager,
    get_pipeline_logger,
    llm,
    pipeline_task,
)

from ai_summarization.documents.flow import DraftDocument, PlanDocument

prompt_manager = PromptManager(__file__)
logger = get_pipeline_logger(__name__)


@pipeline_task
async def write_report(
    analyze_documents: DocumentList,
    plan_document: PlanDocument,
    model: ModelName,
    task_description: str,
) -> DraftDocument:
    """Write the initial report following the plan and consolidated analysis."""
    prompt = prompt_manager.get(
        "write_report",
        task_description=task_description,
    )

    # Combine plan and consolidated analysis for context
    context = AIMessages(analyze_documents)

    # Dynamic message with the prompt
    messages = AIMessages([plan_document, prompt])

    result = await llm.generate(
        model=model,
        context=context,
        messages=messages,
    )

    return DraftDocument.create(
        name=DraftDocument.FILES.REPORT_DRAFT,
        content=result.content,
    )
