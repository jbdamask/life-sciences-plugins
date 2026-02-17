# Life Sciences Plugins

A Claude Code plugin marketplace for life sciences research — genomics, variant analysis, and biomedical databases.

## Installation

```
/plugin marketplace add jbdamask/life-sciences-plugins
```

## Plugins

### variant-research

Research a genomic variant by rsID. Searches 11 biomedical databases in parallel and generates an interactive HTML report.

**Usage:**
```
/variant-research rs429358
```

**Databases searched:**
- **Clinical:** ClinVar, ClinicalTrials.gov, GWAS Catalog
- **Literature:** PubMed
- **Patents:** PatentsView
- **Protein:** STRING-db, Human Protein Atlas, IntAct, BioPlex, BioGRID
- **Drug Targets:** Open Targets Platform

**Report sections:** Variant Summary, Clinical Significance, GWAS Associations, Literature Review, Patent Landscape, Protein Interactions, Drug Target Analysis, Competitive Intelligence, and References.

**Optional API keys** (set as environment variables for expanded results):
- `PATENTSVIEW_API_KEY` — required for patent search ([free key](https://patentsview.org/apis/keyrequest))
- `BIOGRID_API_KEY` — required for BioGRID ([free key](https://wiki.thebiogrid.org/doku.php/biogridrest))
- `NCBI_API_KEY` — increases PubMed rate limit from 3/s to 10/s
