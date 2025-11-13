"""Writing flow for report generation."""

from ai_pipeline_core import DocumentList, FlowConfig, pipeline_flow

from ai_summarization.documents.flow import DraftDocument, PlanDocument
from ai_summarization_solution.documents.flow import AnalyzeDocument
from ai_summarization_solution.flow_options import ProjectFlowOptions

from .tasks import write_report


class WritingFlowConfig(FlowConfig):
    """Configuration for writing flow."""

    INPUT_DOCUMENT_TYPES = [AnalyzeDocument, PlanDocument]
    OUTPUT_DOCUMENT_TYPE = DraftDocument


@pipeline_flow(config=WritingFlowConfig)
async def writing_flow(
    project_name: str,
    documents: DocumentList,
    flow_options: ProjectFlowOptions,
) -> DocumentList:
    """Write the initial report draft based on consolidated analysis and plan."""
    # Get required documents
    analyze_docs = documents.filter_by(AnalyzeDocument)
    plan_doc = documents.get_by(PlanDocument)

    # Write the draft
    draft_doc = await write_report(
        analyze_documents=analyze_docs,
        plan_document=plan_doc,
        model=flow_options.core_model,
        task_description=flow_options.get_task_for_stage("writing"),
    )

    # Return validated output
    return WritingFlowConfig.create_and_validate_output([draft_doc])
