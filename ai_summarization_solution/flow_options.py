"""Flow options configuration for ai-summarization."""

from ai_pipeline_core import FlowOptions, ModelName
from pydantic import Field


class ProjectFlowOptions(FlowOptions):
    """Options to be provided to each flow in the ai-summarization pipeline.

    Extends the base FlowOptions with project-specific configuration.
    """

    # Optionally override defaults from base class
    core_model: ModelName = Field(default="gpt-5")
    small_model: ModelName = Field(default="gpt-5-mini")

    # Base task description - the overall project goal
    base_task: str = Field(
        default="detailed research report about companies developing AI assistants",
        description="The overall project goal that guides all flows",
    )

    # Legacy field for backward compatibility
    task_description: str = Field(
        default=(
            "Write a very detailed research report about companies developing AI assistants. "
            "Start report with detailed introduction to each project working on AI assistants. "
            "Each project should have status, timeline, key milestones, history and future plans. "
            "Then compare them with each other, explain strengths and weaknesses of each project. "
            "Use only provided documents to write the report, do not use your internal knowledge. "
        ),
        description="Legacy task description - use get_task_for_stage() instead",
    )

    def get_task_for_stage(self, stage: str) -> str:
        """Get stage-specific task description for focused processing."""

        tasks = {
            "analysis": (
                f"Analyze and consolidate documents for {self.base_task}. "
                "Remove duplicate information while preserving essential details about "
                "company status, timelines, key milestones, history, and future plans. "
                "Group similar documents and create optimized versions for efficient writing. "
                "Use only provided documents, do not add external knowledge. "
            ),
            "planning": (
                f"Create detailed structure and plan for {self.base_task}. "
                "Design comprehensive organization including company introductions, "
                "status analysis, timeline sections, comparative analysis, and conclusions. "
                "Focus on logical flow and complete coverage of all required elements."
            ),
            "writing": (
                f"Write comprehensive {self.base_task} with detailed company analysis. "
                "Start with detailed introduction to each AI assistant project. "
                "Include status, timeline, key milestones, history and future plans. "
                "Use only provided documents, do not add external knowledge."
            ),
            "review": (
                f"Review and improve {self.base_task} for quality and completeness. "
                "Verify all required sections are present and well-developed. "
                "Check for accuracy, clarity, and alignment with project requirements. "
                "Identify areas needing improvement or additional detail."
            ),
            "rewrite": (
                f"Rewrite and finalize {self.base_task} incorporating review feedback. "
                "Create polished, comprehensive final version with all improvements. "
                "Ensure professional quality and complete coverage of all requirements."
            ),
        }

        return tasks.get(stage, self.task_description)  # Fallback to legacy
