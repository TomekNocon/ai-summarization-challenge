"""Consolidate duplicate company facts while preserving all important information."""

import asyncio
from collections import defaultdict

from ai_pipeline_core import (
    AIMessages,
    ModelName,
    PromptManager,
    get_pipeline_logger,
    llm,
    pipeline_task,
)

from ai_summarization_solution.documents.task.document_metadata import (
    CompanyFact,
    DocumentCompanyFactsDoc,
)

prompt_manager = PromptManager(__file__)
logger = get_pipeline_logger(__name__)


@pipeline_task
async def consolidate_company_facts(
    all_company_facts: list[DocumentCompanyFactsDoc],
    model: ModelName,
) -> list[CompanyFact]:
    """Consolidate duplicate companies while preserving all important information."""

    # Group facts by company name (case insensitive)
    company_groups = defaultdict(list)

    for doc in all_company_facts:
        for fact in doc.get_facts():
            # Normalize company name for grouping
            normalized_name = fact.company_name.lower().strip()
            company_groups[normalized_name].append(fact)

    logger.debug(
        f"Grouped {sum(len(facts) for facts in company_groups.values())} facts "
        f"into {len(company_groups)} companies"
    )

    # Process each company group
    consolidated_facts = []
    consolidation_tasks = []

    for company_name, facts_list in company_groups.items():
        if len(facts_list) == 1:
            # Single source - no consolidation needed
            consolidated_facts.append(facts_list[0])
        else:
            # Multiple sources - consolidate with temporal priority
            task = consolidate_company_group(facts_list, model)
            consolidation_tasks.append(task)

    # Run consolidations in parallel
    if consolidation_tasks:
        consolidated_results = await asyncio.gather(*consolidation_tasks)
        consolidated_facts.extend(consolidated_results)

    logger.debug(f"Consolidated to {len(consolidated_facts)} unique companies")

    return consolidated_facts


async def consolidate_company_group(facts_list: list[CompanyFact], model: ModelName) -> CompanyFact:
    """Consolidate multiple facts for same company with temporal preference."""

    # Sort by temporal priority (newer first)
    sorted_facts = sorted(
        facts_list,
        key=lambda f: (f.document_publication_date or "0000", f.confidence_score),
        reverse=True,
    )

    company_name = facts_list[0].company_name
    newest_date = sorted_facts[0].document_publication_date
    oldest_date = sorted_facts[-1].document_publication_date

    logger.debug(
        f"Consolidating {len(facts_list)} facts for {company_name} "
        f"(newest: {newest_date}, oldest: {oldest_date})"
    )

    prompt = prompt_manager.get(
        "consolidate_company_facts",
        company_name=company_name,
        facts_count=len(facts_list),
        newest_date=newest_date or "Unknown",
        oldest_date=oldest_date or "Unknown",
    )

    # Prepare context with priority-ordered facts
    facts_context = f"COMPANY: {company_name}\n\n"
    facts_context += "PRIORITY ORDER (newest first):\n\n"

    for i, fact in enumerate(sorted_facts):
        facts_context += f"=== SOURCE {i + 1} ===\n"
        facts_context += f"Publication Date: {fact.document_publication_date or 'Unknown'}\n"
        facts_context += f"Confidence Score: {fact.confidence_score}\n"
        facts_context += f"Source Date: {fact.source_date or 'Not specified'}\n\n"
        facts_context += f"Introduction: {fact.introduction}\n"
        facts_context += f"Project Status: {fact.project_status}\n"
        facts_context += f"Market Position: {fact.market_position}\n"

        if fact.timeline_milestones:
            facts_context += f"Milestones: {', '.join(fact.timeline_milestones)}\n"
        if fact.future_plans:
            facts_context += f"Future Plans: {', '.join(fact.future_plans)}\n"
        if fact.strengths:
            facts_context += f"Strengths: {', '.join(fact.strengths)}\n"
        if fact.weaknesses:
            facts_context += f"Weaknesses: {', '.join(fact.weaknesses)}\n"

        facts_context += "\n"

    context = AIMessages([facts_context])
    messages = AIMessages([prompt])

    result = await llm.generate_structured(
        model=model, context=context, messages=messages, response_format=CompanyFact
    )

    return result.parsed
