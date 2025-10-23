"""Optimized consolidation - minimize API calls while preserving quality.

Key optimizations:
1. Batch consolidation by company (not per individual fact)
2. Single LLM call per company with multiple facts
3. Reduce prompt overhead through batching
4. Maintain deduplication and temporal priority logic
"""

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
async def consolidate_company_facts_optimized(
    all_company_facts: list[DocumentCompanyFactsDoc],
    model: ModelName,
) -> list[CompanyFact]:
    """Optimized consolidation - one call per company, not per fact."""

    # Group facts by company name (case insensitive)
    company_groups = defaultdict(list)

    for doc in all_company_facts:
        for fact in doc.get_facts():
            normalized_name = fact.company_name.lower().strip()
            company_groups[normalized_name].append(fact)

    logger.debug(
        f"Grouped {sum(len(facts) for facts in company_groups.values())} facts "
        f"into {len(company_groups)} companies"
    )

    # Process companies in parallel - ONE CALL PER COMPANY
    consolidation_tasks = []
    single_fact_companies = []

    for company_name, facts_list in company_groups.items():
        if len(facts_list) == 1:
            # Single source - no consolidation needed
            single_fact_companies.append(facts_list[0])
        else:
            # Multiple sources - consolidate ALL facts for this company in ONE call
            task = consolidate_single_company_batch(facts_list, model)
            consolidation_tasks.append(task)

    # Run all company consolidations in parallel
    consolidated_results = []
    if consolidation_tasks:
        consolidated_results = await asyncio.gather(*consolidation_tasks)

    # Combine results
    all_results = single_fact_companies + consolidated_results

    total_facts = sum(len(facts) for facts in company_groups.values())
    logger.debug(
        f"Optimized consolidation: {len(company_groups)} companies → "
        f"{len(consolidation_tasks)} LLM calls (vs {total_facts} individual calls)"
    )

    return all_results


async def consolidate_single_company_batch(
    facts_list: list[CompanyFact], model: ModelName
) -> CompanyFact:
    """Consolidate ALL facts for one company in a SINGLE LLM call."""

    company_name = facts_list[0].company_name

    # Sort by temporal priority (newer first)
    sorted_facts = sorted(
        facts_list,
        key=lambda f: (f.document_publication_date or "0000", f.confidence_score),
        reverse=True,
    )

    logger.debug(f"Batch consolidating {len(facts_list)} facts for {company_name}")

    # Get consolidation prompt
    prompt = prompt_manager.get(
        "consolidate_company_facts_optimized",
        company_name=company_name,
        facts_count=len(facts_list),
        newest_date=sorted_facts[0].document_publication_date or "Unknown",
        oldest_date=sorted_facts[-1].document_publication_date or "Unknown",
    )

    # OPTIMIZATION: All facts for this company in context (cached per company)
    # Instead of individual fact processing, batch everything for the company
    company_context = f"COMPANY: {company_name}\n\n"
    company_context += f"CONSOLIDATING {len(facts_list)} FACTS (priority order - newest first):\n\n"

    for i, fact in enumerate(sorted_facts):
        company_context += f"=== FACT {i + 1} ===\n"
        company_context += f"Publication Date: {fact.document_publication_date or 'Unknown'}\n"
        company_context += f"Confidence Score: {fact.confidence_score}\n"
        company_context += f"Source Date: {fact.source_date or 'Not specified'}\n\n"
        company_context += f"Introduction: {fact.introduction}\n"
        company_context += f"Project Status: {fact.project_status}\n"
        company_context += f"Market Position: {fact.market_position}\n"

        if fact.timeline_milestones:
            company_context += f"Milestones: {', '.join(fact.timeline_milestones)}\n"
        if fact.future_plans:
            company_context += f"Future Plans: {', '.join(fact.future_plans)}\n"
        if fact.strengths:
            company_context += f"Strengths: {', '.join(fact.strengths)}\n"
        if fact.weaknesses:
            company_context += f"Weaknesses: {', '.join(fact.weaknesses)}\n"

        company_context += "\n"

    # SINGLE CALL for entire company consolidation
    context = AIMessages([company_context])  # All facts for this company
    messages = AIMessages([prompt])  # Consolidation instructions

    result = await llm.generate_structured(
        model=model, context=context, messages=messages, response_format=CompanyFact
    )

    return result.parsed
