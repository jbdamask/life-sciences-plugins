---
name: variant-research
description: "Research a genomic variant by rsID. Searches 11 biomedical databases and generates an interactive HTML report."
argument-hint: "<rsID> (e.g., rs699)"
---

# /variant-research

You are the variant research orchestrator. Given an rsID, you coordinate a comprehensive search across biomedical databases and produce an interactive HTML research report.

## Input
The user provides an rsID (e.g., `rs699`, `rs334`, `rs12345`).

Store the rsID (lowercase, trimmed) as `$RSID`.

Use `${CLAUDE_PLUGIN_ROOT}` as the base path for all script references. The venv and scripts live at:
- Venv: `${CLAUDE_PLUGIN_ROOT}/.venv/bin/activate`
- Scripts: `${CLAUDE_PLUGIN_ROOT}/skills/variant-research/scripts/`

## Workflow

### Phase 0: Setup (blocking, first run only)

If the venv does not exist, run setup:

```bash
if [ ! -d "${CLAUDE_PLUGIN_ROOT}/.venv" ]; then
  bash "${CLAUDE_PLUGIN_ROOT}/skills/variant-research/scripts/setup.sh"
fi
```

### Phase 1: Variant Resolution (blocking)

Run the variant resolver to get gene information:

```bash
source "${CLAUDE_PLUGIN_ROOT}/.venv/bin/activate" && python "${CLAUDE_PLUGIN_ROOT}/skills/variant-research/scripts/resolve_variant.py" $RSID
```

Save the output to `reports/${RSID}_variant.json`.

Read and parse the JSON. Extract:
- `gene_symbol` (REQUIRED -- abort if missing)
- `gene_name`
- `ensembl_gene_id`

Tell the user:
> Resolved **$RSID** to gene **$GENE_SYMBOL** ($GENE_NAME). Starting parallel database searches...

### Phase 2: Parallel Database Searches (5 scripts, all in parallel)

Launch ALL FIVE of these as parallel Task agents using subagent_type "Bash". Each runs a Python script that calls REST APIs directly (no MCP tools needed).

**IMPORTANT**: Launch all 5 in a SINGLE response with 5 parallel Task tool calls.

1. **Literature Search**
   - subagent_type: "Bash"
   - Prompt: `source "${CLAUDE_PLUGIN_ROOT}/.venv/bin/activate" && python "${CLAUDE_PLUGIN_ROOT}/skills/variant-research/scripts/fetch_literature.py" $RSID`

2. **Patent Search**
   - subagent_type: "Bash"
   - Prompt: `source "${CLAUDE_PLUGIN_ROOT}/.venv/bin/activate" && python "${CLAUDE_PLUGIN_ROOT}/skills/variant-research/scripts/fetch_patents.py" $RSID`

3. **Clinical Search**
   - subagent_type: "Bash"
   - Prompt: `source "${CLAUDE_PLUGIN_ROOT}/.venv/bin/activate" && python "${CLAUDE_PLUGIN_ROOT}/skills/variant-research/scripts/fetch_clinical.py" $RSID`

4. **Protein Search**
   - subagent_type: "Bash"
   - Prompt: `source "${CLAUDE_PLUGIN_ROOT}/.venv/bin/activate" && python "${CLAUDE_PLUGIN_ROOT}/skills/variant-research/scripts/fetch_protein.py" $RSID`

5. **Drug Target Search**
   - subagent_type: "Bash"
   - Prompt: `source "${CLAUDE_PLUGIN_ROOT}/.venv/bin/activate" && python "${CLAUDE_PLUGIN_ROOT}/skills/variant-research/scripts/fetch_drug_targets.py" $RSID`

Wait for all to complete. Report progress to the user as each finishes.

### Phase 3: Report Generation (blocking, after Phase 2)

Generate the HTML report:

```bash
source "${CLAUDE_PLUGIN_ROOT}/.venv/bin/activate" && python "${CLAUDE_PLUGIN_ROOT}/skills/variant-research/scripts/generate_report.py" $RSID
```

The report will be at `reports/${RSID}_report.html`.

### Phase 4: Present Results

Tell the user:

> Research complete for **$RSID** ($GENE_SYMBOL).
>
> Report: `reports/${RSID}_report.html`
>
> **Summary of findings:**
> - Literature: X PubMed articles
> - Patents: Z patents found
> - Clinical: A ClinVar entries, B trials, C GWAS associations
> - Protein: D STRING interactions, E IntAct, F BioPlex, G BioGRID
> - Drug targets: H known drugs, I disease associations

Fill in the counts from the JSON files. Note any databases that returned errors.

## Error Handling

- If Phase 1 fails (no gene_symbol): Tell the user the rsID could not be resolved and suggest checking the ID.
- If individual Phase 2 scripts fail: Continue with available data. Note failures in the summary.
- If Phase 3 fails: Try running the report generator again. If it fails twice, list the available JSON files and suggest manual review.
- Always ensure the venv is activated before running Python scripts: `source "${CLAUDE_PLUGIN_ROOT}/.venv/bin/activate"`
