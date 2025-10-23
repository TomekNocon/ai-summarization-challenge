"""Planning flow for report generation."""

from ai_pipeline_core import DocumentList, FlowConfig, pipeline_flow

from ai_summarization.documents.flow import PlanDocument
from ai_summarization.flow_options import ProjectFlowOptions
from ai_summarization_solution.documents.flow import AnalyzeDocument

from .tasks import plan_report


class PlanningFlowConfig(FlowConfig):
    """Configuration for planning flow."""

    INPUT_DOCUMENT_TYPES = [AnalyzeDocument]  # Use consolidated analysis
    OUTPUT_DOCUMENT_TYPE = PlanDocument


@pipeline_flow(config=PlanningFlowConfig)
async def planning_flow(
    project_name: str,
    documents: DocumentList,
    flow_options: ProjectFlowOptions,
) -> DocumentList:
    """Plan the report structure based on consolidated analysis."""
    # Get consolidated analysis documents
    analyze_docs = documents.filter_by(AnalyzeDocument)

    # Create the plan
    plan_doc = await plan_report(
        documents=analyze_docs,
        model=flow_options.core_model,
        task_description=flow_options.task_description,
    )

    # Return validated output
    return PlanningFlowConfig.create_and_validate_output([plan_doc])
