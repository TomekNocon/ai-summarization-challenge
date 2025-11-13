"""Analysis flow for document optimization and deduplication."""

import asyncio
from datetime import datetime

from ai_pipeline_core import DocumentList, FlowConfig, pipeline_flow

from ai_summarization_solution.documents.flow import AnalyzeDocument, InputDocument
from ai_summarization_solution.flow_options import ProjectFlowOptions

from .tasks import extract_document_metadata
from .tasks.consolidate_company_facts_single_batch import consolidate_company_facts_single_batch


class AnalysisFlowConfig(FlowConfig):
    """Configuration for analysis flow."""

    INPUT_DOCUMENT_TYPES = [InputDocument]
    OUTPUT_DOCUMENT_TYPE = AnalyzeDocument


@pipeline_flow(config=AnalysisFlowConfig)
async def analysis_flow(
    project_name: str,
    documents: DocumentList,
    flow_options: ProjectFlowOptions,
) -> DocumentList:
    """Analyze, deduplicate and optimize input documents for efficient processing."""

    # Get input documents
    input_docs = documents.filter_by(InputDocument)

    company_facts_tasks = [
        extract_document_metadata(
            document=doc,
            model=flow_options.small_model,  # Use cheaper model
            task_description=flow_options.get_task_for_stage("meta"),
        )
        for doc in input_docs
    ]

    document_company_facts_list = await asyncio.gather(*company_facts_tasks)

    consolidated_facts = await consolidate_company_facts_single_batch(
        all_company_facts=document_company_facts_list,
        model=flow_options.core_model,  # Use core model
    )

    facts_summary = "# Consolidated Company Analysis\n\n"
    facts_summary += f"**Analysis Date**: {datetime.now().strftime('%Y-%m-%d')}\n"
    facts_summary += f"**Sources Processed**: {len(input_docs)} documents\n"
    facts_summary += f"**Companies Identified**: {len(consolidated_facts)} unique companies\n\n"

    for fact in consolidated_facts:
        facts_summary += f"## {fact.company_name}\n"
        facts_summary += f"**Introduction:** {fact.introduction}\n"
        facts_summary += f"**Status:** {fact.project_status}\n"
        facts_summary += f"**Market Position:** {fact.market_position}\n"
        if fact.timeline_milestones:
            facts_summary += f"**Milestones:** {', '.join(fact.timeline_milestones)}\n"
        if fact.future_plans:
            facts_summary += f"**Future Plans:** {', '.join(fact.future_plans)}\n"
        if fact.strengths:
            facts_summary += f"**Strengths:** {', '.join(fact.strengths)}\n"
        if fact.weaknesses:
            facts_summary += f"**Weaknesses:** {', '.join(fact.weaknesses)}\n"
        if fact.source_date:
            facts_summary += f"**Latest Information Date:** {fact.source_date}\n"
        if fact.document_publication_date:
            facts_summary += f"**Document Publication Date:** {fact.document_publication_date}\n"
        facts_summary += "\n"

    analyze_doc = AnalyzeDocument.create(
        name="consolidated_company_analysis.md",
        content=facts_summary,
    )

    # Return validated output
    return AnalysisFlowConfig.create_and_validate_output([analyze_doc])
