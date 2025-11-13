"""Single-batch consolidation - process ALL companies in ONE API call.

This approach:
1. Groups all company facts by company
2. Makes ONE single API call to consolidate ALL companies
3. Minimizes prompt overhead and API costs
4. Maintains quality through structured output
"""

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
    ConsolidatedCompanyFacts,
    DocumentCompanyFactsDoc,
)

prompt_manager = PromptManager(__file__)
logger = get_pipeline_logger(__name__)


@pipeline_task
async def consolidate_company_facts_single_batch(
    all_company_facts: list[DocumentCompanyFactsDoc],
    model: ModelName,
) -> list[CompanyFact]:
    """Consolidate ALL companies in a SINGLE API call."""

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

    # Separate single-fact companies (no consolidation needed)
    single_fact_companies = []
    multi_fact_companies = {}

    for company_name, facts_list in company_groups.items():
        if len(facts_list) == 1:
            single_fact_companies.append(facts_list[0])
        else:
            multi_fact_companies[company_name] = facts_list

    if not multi_fact_companies:
        # No consolidation needed - all companies have single facts
        logger.debug("No consolidation needed - all companies have single sources")
        return single_fact_companies

    # **SINGLE API CALL** for ALL multi-fact companies
    logger.debug(
        f"Single-batch consolidation: {len(multi_fact_companies)} companies in ONE call "
        f"(vs {len(multi_fact_companies)} separate calls)"
    )

    consolidated_companies = await consolidate_all_companies_batch(multi_fact_companies, model)

    # Combine single-fact and consolidated companies
    all_results = single_fact_companies + consolidated_companies

    logger.debug(
        f"Completed single-batch consolidation: {len(company_groups)} total companies, "
        f"1 API call for {len(multi_fact_companies)} multi-source companies"
    )

    return all_results


async def consolidate_all_companies_batch(
    multi_fact_companies: dict[str, list[CompanyFact]], model: ModelName
) -> list[CompanyFact]:
    """Consolidate ALL multi-fact companies in ONE API call."""

    # Prepare consolidated context with ALL companies
    batch_context = "BATCH COMPANY CONSOLIDATION\n\n"
    batch_context += f"Processing {len(multi_fact_companies)} companies with multiple sources:\n\n"

    for company_name, facts_list in multi_fact_companies.items():
        # Sort facts by temporal priority for this company
        sorted_facts = sorted(
            facts_list,
            key=lambda f: (f.document_publication_date or "0000", f.confidence_score),
            reverse=True,
        )

        batch_context += f"{'=' * 50}\n"
        batch_context += f"COMPANY: {facts_list[0].company_name}\n"
        batch_context += f"SOURCES: {len(facts_list)} (newest first)\n"
        batch_context += f"NEWEST DATE: {sorted_facts[0].document_publication_date or 'Unknown'}\n"
        batch_context += f"OLDEST DATE: {sorted_facts[-1].document_publication_date or 'Unknown'}\n"
        batch_context += f"{'=' * 50}\n\n"

        for i, fact in enumerate(sorted_facts):
            batch_context += f"--- SOURCE {i + 1} ---\n"
            batch_context += f"Publication Date: {fact.document_publication_date or 'Unknown'}\n"
            batch_context += f"Confidence Score: {fact.confidence_score}\n"
            batch_context += f"Source Date: {fact.source_date or 'Not specified'}\n\n"
            batch_context += f"Introduction: {fact.introduction}\n"
            batch_context += f"Status: {fact.project_status}\n"
            batch_context += f"Market Position: {fact.market_position}\n"

            if fact.timeline_milestones:
                batch_context += f"Milestones: {', '.join(fact.timeline_milestones)}\n"
            if fact.future_plans:
                batch_context += f"Future Plans: {', '.join(fact.future_plans)}\n"
            if fact.strengths:
                batch_context += f"Strengths: {', '.join(fact.strengths)}\n"
            if fact.weaknesses:
                batch_context += f"Weaknesses: {', '.join(fact.weaknesses)}\n"

            batch_context += "\n"

        batch_context += "\n"

    # Get single prompt for ALL companies
    prompt = prompt_manager.get(
        "consolidate_company_facts_single_batch",
        companies_count=len(multi_fact_companies),
        company_list=", ".join([facts[0].company_name for facts in multi_fact_companies.values()]),
    )

    # **SINGLE API CALL** for all companies
    context = AIMessages([batch_context])  # All companies in context
    messages = AIMessages([prompt])  # Single consolidation prompt

    result = await llm.generate_structured(
        model=model, context=context, messages=messages, response_format=ConsolidatedCompanyFacts
    )

    logger.debug(f"Single batch consolidated {len(result.parsed.companies)} companies")
    return result.parsed.companies
