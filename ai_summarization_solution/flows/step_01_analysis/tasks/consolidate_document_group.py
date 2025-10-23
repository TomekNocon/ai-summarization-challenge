# """Group similar documents and consolidate overlapping content."""

# import asyncio
# from collections import defaultdict

# from ai_pipeline_core import (
#     AIMessages,
#     DocumentList,
#     ModelName,
#     PromptManager,
#     get_pipeline_logger,
#     llm,
#     pipeline_task,
# )

# from ai_summarization_solution.documents.flow import AnalyzeDocument, InputDocument
# from ai_summarization_solution.documents.task.document_metadata import (
#     CompanyFact,
#     DocumentCompanyFacts,
#     DocumentCompanyFactsDoc,
# )

# prompt_manager = PromptManager(__file__)
# logger = get_pipeline_logger(__name__)


# def group_documents_by_similarity(
#     documents: DocumentList,
#     metadata_list: list[DocumentMetadataDoc],
# ) -> dict[str, list[tuple[InputDocument, DocumentMetadata]]]:
#     """Group documents based on metadata similarity."""

#     groups = defaultdict(list)

#     for doc, metadata_doc in zip(documents, metadata_list):
#         metadata = metadata_doc.get_metadata()

#         # Smart grouping based on document characteristics
#         if len(metadata.companies) > 5:
#             # Many companies = market research/overview document
#             # Group by main topic theme
#             if metadata.topics:
#                 # Look for key themes to group similar market research
#                 main_theme = None
#                 for topic in metadata.topics:
#                     topic_lower = topic.lower()
#                     if "ai assistant" in topic_lower or "personal assistant" in topic_lower:
#                         main_theme = "ai_assistants"
#                         break
#                     elif (
#                         "local" in topic_lower
#                         or "privacy" in topic_lower
#                         or "second brain" in topic_lower
#                     ):
#                         main_theme = "local_ai_solutions"
#                         break
#                     elif "productivity" in topic_lower or "developer" in topic_lower:
#                         main_theme = "productivity_tools"
#                         break
#                     elif "enterprise" in topic_lower or "business" in topic_lower:
#                         main_theme = "enterprise_solutions"
#                         break

#                 group_key = (
#                     f"theme_{main_theme}"
#                     if main_theme
#                     else f"type_{metadata.document_type.lower().replace(' ', '_')}"
#                 )
#             else:
#                 group_key = f"type_{metadata.document_type.lower().replace(' ', '_')}"

#         elif 1 <= len(metadata.companies) <= 5:
#             # Few companies = focused company analysis
#             # Group by primary company
#             primary_company = (
#                 sorted(metadata.companies)[0].lower().replace(" ", "_").replace(".", "")
#             )
#             group_key = f"company_{primary_company}"

#         else:
#             # No companies = general content
#             group_key = f"type_{metadata.document_type.lower().replace(' ', '_')}"

#         groups[group_key].append((doc, metadata))

#         # Debug logging for each document grouping decision
#         logger.debug(
#             f"Document '{doc.name}' → Group '{group_key}' "
#             f"(companies: {metadata.companies}, type: {metadata.document_type})"
#         )

#     logger.debug(f"Created {len(groups)} document groups from {len(documents)} documents")

#     # Log group sizes for debugging
#     for group_name, group_docs in groups.items():
#         doc_names = [doc.name for doc, _ in group_docs]
#         logger.debug(f"Group '{group_name}': {len(group_docs)} documents - {doc_names}")

#     return dict(groups)


# @pipeline_task
# async def consolidate_document_group(
#     doc_group: list[tuple[InputDocument, DocumentMetadata]],
#     model: ModelName,
#     task_description: str,
# ) -> AnalyzeDocument:
#     """Consolidate document group (handles both single and multiple docs)."""

#     # Extract documents and metadata
#     documents = [doc for doc, _ in doc_group]
#     metadata_items = [metadata for _, metadata in doc_group]

#     # Get combined metadata across all documents in group
#     all_companies = set()
#     all_topics = set()
#     for metadata in metadata_items:
#         all_companies.update(metadata.companies)
#         all_topics.update(metadata.topics)

#     # Single unified prompt (LLM handles single vs multiple naturally)
#     prompt = prompt_manager.get(
#         "consolidate_document_group",
#         task_description=task_description,
#         companies=", ".join(sorted(all_companies)),
#         topics=", ".join(sorted(all_topics)),
#         document_count=len(documents),  # LLM can see if it's 1 or many
#     )

#     # CACHE-OPTIMIZED: Two-stage processing for better cache utilization
#     if len(documents) == 1:
#         # Single document - optimal caching
#         context = AIMessages([documents[0]])
#         messages = AIMessages([prompt])

#         result = await llm.generate(
#             model=model,
#             context=context,
#             messages=messages,
#         )
#     else:
#         # Multiple documents - process each individually first, then consolidate summaries
#         individual_summaries = []

#         for doc in documents:
#             # Cache-friendly: each document processed individually
#             summary_prompt = prompt_manager.get(
#                 "consolidate_document_group",
#                 task_description=f"Create brief summary of this document for: {task_description}",
#                 companies=", ".join(sorted(all_companies)),
#                 topics=", ".join(sorted(all_topics)),
#                 document_count=1,  # Individual processing
#             )

#             summary_result = await llm.generate(
#                 model=model,
#                 context=AIMessages([doc]),  # Individual doc cached!
#                 messages=AIMessages([summary_prompt]),
#             )
#             individual_summaries.append(summary_result.content)

#         # Final consolidation step (small, fast)
#         consolidation_prompt = f"""
#         Consolidate these {len(individual_summaries)} document summaries into a unified analysis:

#         Task: {task_description}
#         Focus: {", ".join(sorted(all_companies))} - {", ".join(sorted(all_topics))}

#         Remove duplicates, combine complementary information, create coherent final analysis.
#         """

#         result = await llm.generate(
#             model=model,
#             context=AIMessages(individual_summaries),  # Small summaries, not full docs
#             messages=AIMessages([consolidation_prompt]),
#         )

#     # Generate descriptive filename
#     main_company = list(all_companies)[0] if all_companies else "general"
#     suffix = "single" if len(documents) == 1 else "consolidated"
#     filename = f"analysis_{main_company}_{suffix}.md"

#     logger.debug(
#         f"Consolidating {len(documents)} documents into '{filename}' "
#         f"(companies: {sorted(all_companies)}, topics: {sorted(all_topics)})"
#     )

#     return AnalyzeDocument.create(
#         name=filename,
#         content=result.content,
#     )


# @pipeline_task
# async def group_and_consolidate_documents(
#     documents: DocumentList,
#     metadata_list: list[DocumentMetadataDoc],
#     model: ModelName,
#     task_description: str,
# ) -> list[AnalyzeDocument]:
#     """Group similar documents and consolidate them into optimized analyses."""

#     # Group documents by similarity
#     document_groups = group_documents_by_similarity(documents, metadata_list)

#     # Log grouping results
#     total_original = len(documents)
#     total_groups = len(document_groups)
#     logger.debug(f"Grouped {total_original} documents into {total_groups} groups")

#     for group_key, group_docs in document_groups.items():
#         doc_names = [doc.name for doc, _ in group_docs]
#         logger.debug(f"Group '{group_key}': {len(group_docs)} documents - {doc_names}")

#     # Consolidate each group in parallel
#     consolidation_tasks = [
#         consolidate_document_group(group_docs, model, task_description)
#         for group_docs in document_groups.values()
#     ]

#     consolidated_docs = await asyncio.gather(*consolidation_tasks)

#     # Calculate token reduction estimate
#     original_tokens = sum(
#         metadata_doc.get_metadata().estimated_tokens for metadata_doc in metadata_list
#     )
#     logger.debug(
#         f"Estimated token reduction: {original_tokens} → "
#         f"{len(consolidated_docs)} consolidated documents"
#     )

#     return consolidated_docs
