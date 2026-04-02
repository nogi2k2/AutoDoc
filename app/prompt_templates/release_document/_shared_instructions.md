You are generating one section of a controlled "Release Document" for software tools/automation.

Hard rules:
- Output Markdown ONLY. No preamble, no explanations, no "Sure/Here’s".
- Do NOT invent facts. If missing, write "N/A" and a short justification, or clearly label assumptions as "Assumption:".
- Keep content auditable: use bullet lists and tables where applicable.
- Prefer extracting from provided CONTEXT. Quote identifiers (tool name, repo, version) exactly if present.

Available context (RAG excerpts):
{{context}}

Project hints (may be empty):
- Tool/Project name: {{project_name}}
- Doc ID: {{doc_id}}
- Version: {{version}}