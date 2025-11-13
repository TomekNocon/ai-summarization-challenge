"""Extract metadata from documents for grouping and analysis."""

from ai_pipeline_core import (
    AIMessages,
    ModelName,
    PromptManager,
    get_pipeline_logger,
    llm,
    pipeline_task,
)

from ai_summarization.documents.flow import InputDocument
from ai_summarization_solution.documents.task.document_metadata import (
    DocumentCompanyFacts,
    DocumentCompanyFactsDoc,
)

prompt_manager = PromptManager(__file__)
logger = get_pipeline_logger(__name__)


@pipeline_task
async def extract_document_metadata(
    document: InputDocument,
    model: ModelName,
    task_description: str,
) -> DocumentCompanyFactsDoc:
    """Extract key metadata from a document for analysis and grouping."""

    prompt = prompt_manager.get(
        "extract_document_metadata",
        task_description=task_description,
    )

    context = AIMessages([document])
    messages = AIMessages([prompt])

    # Use structured output for reliable company facts extraction
    result = await llm.generate_structured(
        model=model,
        context=context,
        messages=messages,
        response_format=DocumentCompanyFacts,
    )

    logger.debug(f"""Extracted {len(result.parsed.facts)} company facts from {document.name}""")

    return DocumentCompanyFactsDoc.create(
        name=f"{document.name}_company_facts.json",
        content=result.parsed,
    )
