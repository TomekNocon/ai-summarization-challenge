"""Document metadata for analysis and grouping."""

from typing import Optional

from ai_pipeline_core import TaskDocument
from pydantic import BaseModel, Field


class CompanyFact(BaseModel):
    """Detailed facts about a specific company or AI assistant project."""

    company_name: str = Field(description="Name of the company or project")
    introduction: str = Field(description="Detailed overview of the AI assistant project")
    project_status: str = Field(description="Current development stage and availability")
    timeline_milestones: list[str] = Field(description="Key achievements and historical context")
    future_plans: list[str] = Field(description="Roadmap and upcoming features")
    strengths: list[str] = Field(description="Key strengths and advantages")
    weaknesses: list[str] = Field(description="Limitations and areas for improvement")
    market_position: str = Field(description="How this project compares to competitors")
    source_date: Optional[str] = Field(
        description="Date of the information if available", default=None
    )

    # NEW FIELDS FOR TEMPORAL HANDLING
    document_publication_date: Optional[str] = Field(
        description="Publication/update date of source document", default=None
    )
    confidence_score: float = Field(
        description="Confidence in information recency (0-1)", default=1.0
    )


class DocumentCompanyFacts(BaseModel):
    """List of company facts extracted from a document."""

    facts: list[CompanyFact] = Field(description="List of detailed company facts")


class ConsolidatedCompanyFacts(BaseModel):
    """Container for all consolidated company facts."""

    companies: list[CompanyFact] = Field(description="List of consolidated company facts")


class DocumentCompanyFactsDoc(TaskDocument):
    """Task document containing extracted company facts."""

    def get_facts(self) -> list[CompanyFact]:
        """Parse the document content as list of CompanyFact objects."""
        return self.as_pydantic_model(DocumentCompanyFacts).facts
