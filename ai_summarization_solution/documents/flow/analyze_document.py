"""Flow document for analyzed and deduplicated content."""

from ai_pipeline_core import FlowDocument


class AnalyzeDocument(FlowDocument):
    """Flow document containing analyzed and deduplicated content from input documents.

    These documents are the output of the analysis phase where similar documents
    are grouped and consolidated to reduce redundancy before report generation.
    """

    # No FILES enum - we create dynamic filenames based on company/topic groups
