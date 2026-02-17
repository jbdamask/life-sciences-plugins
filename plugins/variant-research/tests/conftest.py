"""Shared fixtures and mock data for variant-research plugin tests."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add scripts directory to sys.path so we can import the modules
SCRIPTS_DIR = Path(__file__).parent.parent / "skills" / "variant-research" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Canonical variant info fixture (used by most downstream scripts)
# ---------------------------------------------------------------------------

@pytest.fixture
def variant_info():
    """Minimal variant info dict as produced by resolve_variant.py for rs699."""
    return {
        "rsid": "rs699",
        "gene_symbol": "AGT",
        "gene_name": "angiotensinogen",
        "ensembl_gene_id": "ENSG00000135744",
        "chromosome": "1",
        "position": 230710048,
        "alleles": "T>C",
        "consequence": "missense_variant",
        "clinvar_significance": "drug response",
        "protein_change": "p.Met268Thr",
        "errors": [],
    }


@pytest.fixture
def variant_info_minimal():
    """Variant info with only the required gene_symbol field."""
    return {
        "rsid": "rs699",
        "gene_symbol": "AGT",
        "gene_name": None,
        "ensembl_gene_id": None,
        "chromosome": None,
        "position": None,
        "alleles": None,
        "consequence": None,
        "clinvar_significance": None,
        "protein_change": None,
        "errors": [],
    }


@pytest.fixture
def tmp_reports_dir(tmp_path):
    """Create a temporary reports directory."""
    reports = tmp_path / "reports"
    reports.mkdir()
    return reports


@pytest.fixture
def write_variant_json(tmp_reports_dir, variant_info):
    """Write variant info JSON to tmp reports dir and return the path."""
    path = tmp_reports_dir / "rs699_variant.json"
    path.write_text(json.dumps(variant_info))
    return path


# ---------------------------------------------------------------------------
# Mock response helper
# ---------------------------------------------------------------------------

def make_mock_response(json_data=None, text="", status_code=200, raise_for_status=True):
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text if text else json.dumps(json_data or {})
    resp.json.return_value = json_data or {}
    if raise_for_status and status_code >= 400:
        from requests.exceptions import HTTPError
        resp.raise_for_status.side_effect = HTTPError(f"{status_code}")
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# MyVariant.info mock response
# ---------------------------------------------------------------------------

MYVARIANT_RESPONSE = {
    "hits": [{
        "dbsnp": {
            "rsid": "rs699",
            "chrom": "1",
            "hg19": {"start": 230710048, "end": 230710048},
            "ref": "T",
            "alt": "C",
            "gene": {"symbol": "AGT", "name": "angiotensinogen"},
        },
        "dbnsfp": {
            "genename": "AGT",
            "ensembl": {"geneid": "ENSG00000135744"},
        },
        "cadd": {
            "gene": {"genename": "AGT"},
        },
        "snpeff": {
            "ann": [{
                "effect": "missense_variant",
                "hgvs_p": "p.Met268Thr",
            }],
        },
        "clinvar": {
            "rcv": [{
                "clinical_significance": "drug response",
            }],
        },
    }],
}


# ---------------------------------------------------------------------------
# PubMed mock responses
# ---------------------------------------------------------------------------

PUBMED_ESEARCH_RESPONSE = {
    "esearchresult": {
        "idlist": ["12345678", "87654321"],
    },
}

PUBMED_EFETCH_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>12345678</PMID>
      <Article>
        <ArticleTitle>AGT variant and hypertension risk</ArticleTitle>
        <Journal>
          <Title>Journal of Hypertension</Title>
          <JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue>
        </Journal>
        <AuthorList>
          <Author><LastName>Smith</LastName><Initials>J</Initials></Author>
          <Author><LastName>Doe</LastName><Initials>A</Initials></Author>
        </AuthorList>
        <Abstract><AbstractText>This study examines the role of AGT rs699 in hypertension.</AbstractText></Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>87654321</PMID>
      <Article>
        <ArticleTitle>Pharmacogenomics of angiotensinogen</ArticleTitle>
        <Journal>
          <Title>Pharmacogenomics Journal</Title>
          <JournalIssue><PubDate><Year>2022</Year></PubDate></JournalIssue>
        </Journal>
        <AuthorList>
          <Author><LastName>Lee</LastName><Initials>K</Initials></Author>
        </AuthorList>
        <Abstract><AbstractText>Review of pharmacogenomic implications.</AbstractText></Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


# ---------------------------------------------------------------------------
# PatentsView mock response
# ---------------------------------------------------------------------------

PATENTSVIEW_RESPONSE = {
    "patents": [
        {
            "patent_id": "US-11234567-B2",
            "patent_title": "AGT inhibitor compound for treating hypertension",
            "patent_abstract": "A novel compound that inhibits angiotensinogen for treatment of hypertension.",
            "patent_date": "2023-01-15",
            "assignees": [{"assignee_organization": "Pharma Corp"}],
        },
        {
            "patent_id": "US-10987654-B1",
            "patent_title": "Diagnostic kit for AGT polymorphism detection",
            "patent_abstract": "A diagnostic assay for detecting AGT gene variants as biomarkers.",
            "patent_date": "2022-06-20",
            "assignees": [{"assignee_organization": "DiagTech Inc"}],
        },
    ],
}


# ---------------------------------------------------------------------------
# ClinVar mock response
# ---------------------------------------------------------------------------

CLINVAR_ESEARCH_RESPONSE = {
    "esearchresult": {"idlist": ["12345"]},
}

CLINVAR_ESUMMARY_RESPONSE = {
    "result": {
        "uids": ["12345"],
        "12345": {
            "uid": "12345",
            "clinical_significance": {
                "description": "drug response",
                "review_status": "criteria provided, single submitter",
                "last_evaluated": "2023-01-01",
            },
            "trait_set": [{"trait_name": "Hypertension"}],
            "variation_set": [{"variation_archive_id": "12345"}],
        },
    },
}


# ---------------------------------------------------------------------------
# ClinicalTrials.gov mock response
# ---------------------------------------------------------------------------

CTGOV_RESPONSE = {
    "studies": [{
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT12345678",
                "officialTitle": "Study of AGT inhibitor in hypertension",
                "briefTitle": "AGT inhibitor trial",
            },
            "statusModule": {"overallStatus": "RECRUITING"},
            "designModule": {"phases": ["PHASE3"]},
            "sponsorCollaboratorsModule": {
                "leadSponsor": {"name": "Pharma Corp"},
            },
            "conditionsModule": {"conditions": ["Hypertension"]},
            "armsInterventionsModule": {
                "interventions": [{
                    "name": "AGT-001",
                    "type": "DRUG",
                    "description": "Experimental AGT inhibitor",
                }],
            },
        },
    }],
}


# ---------------------------------------------------------------------------
# GWAS Catalog mock response
# ---------------------------------------------------------------------------

GWAS_RESPONSE = {
    "_embedded": {
        "associations": [{
            "efoTraits": [{"trait": "Hypertension"}],
            "pvalueMantissa": 3.5,
            "pvalueExponent": -12,
            "betaNum": 0.15,
            "betaUnit": "mmHg",
            "betaDirection": "increase",
            "loci": [{"strongestRiskAlleles": [{"riskAlleleName": "rs699-C"}]}],
            "_links": {"study": {"href": "https://www.ebi.ac.uk/gwas/rest/api/studies/GCST001234"}},
        }],
    },
}

GWAS_STUDY_RESPONSE = {
    "accessionId": "GCST001234",
    "publicationInfo": {
        "pubmedId": "27618448",
        "publicationDate": "2016-10-01",
        "publication": "Nat Genet",
        "title": "Meta-analysis identifies common and rare variants influencing blood pressure.",
        "author": {"fullname": "Liu C"},
    },
}


# ---------------------------------------------------------------------------
# STRING-db mock responses
# ---------------------------------------------------------------------------

STRING_RESOLVE_RESPONSE = [{"stringId": "9606.ENSP00000355627"}]

STRING_NETWORK_RESPONSE = [
    {
        "preferredName_A": "AGT",
        "preferredName_B": "REN",
        "score": 0.999,
        "nscore": 0, "fscore": 0, "pscore": 0,
        "ascore": 0, "escore": 0.8, "dscore": 0.9, "tscore": 0.95,
    },
    {
        "preferredName_A": "AGT",
        "preferredName_B": "ACE",
        "score": 0.998,
        "nscore": 0, "fscore": 0, "pscore": 0,
        "ascore": 0, "escore": 0.7, "dscore": 0.85, "tscore": 0.9,
    },
]


# ---------------------------------------------------------------------------
# HPA mock response
# ---------------------------------------------------------------------------

HPA_RESPONSE = [
    {
        "Gene": "AGT",
        "Gene synonym": "SERPINA8",
        "Uniprot": "P01019",
        "Protein class": "Enzymes, Secreted proteins",
        "Subcellular location": "Vesicles",
        "Tissue expression": "Liver;Kidney",
        "RNA expression": "Liver: 1234.5 nTPM",
    },
]


# ---------------------------------------------------------------------------
# IntAct PSICQUIC mock response (MITAB 2.7 format)
# ---------------------------------------------------------------------------

INTACT_MITAB_RESPONSE = (
    "uniprotkb:P01019\tuniprotkb:P00797\t-\t-\t"
    "uniprotkb:AGT(display_short)\tuniprotkb:REN(display_short)\t"
    "psi-mi:\"MI:0006\"(anti bait coimmunoprecipitation)\t"
    "author1 et al.\t"
    "pubmed:12345678\t"
    "taxid:9606\ttaxid:9606\t"
    "psi-mi:\"MI:0915\"(physical association)\t"
    "psi-mi:\"MI:0469\"(IntAct)\t"
    "intact:EBI-12345\t"
    "intact-miscore:0.65\n"
    "uniprotkb:P01019\tuniprotkb:P12821\t-\t-\t"
    "uniprotkb:AGT(display_short)\tuniprotkb:ACE(display_short)\t"
    "psi-mi:\"MI:0019\"(coimmunoprecipitation)\t"
    "author2 et al.\t"
    "pubmed:87654321\t"
    "taxid:9606\ttaxid:9606\t"
    "psi-mi:\"MI:0915\"(physical association)\t"
    "psi-mi:\"MI:0469\"(IntAct)\t"
    "intact:EBI-67890\t"
    "intact-miscore:0.45\n"
)


# ---------------------------------------------------------------------------
# BioPlex mock TSV data
# ---------------------------------------------------------------------------

BIOPLEX_TSV_DATA = (
    "GeneA\tGeneB\tUniprotA\tUniprotB\tSymbolA\tSymbolB\tpW\tpNI\tpInt\n"
    "183\t5972\tP01019\tP00797\tAGT\tREN\t0.01\t0.05\t0.94\n"
    "183\t1636\tP01019\tP12821\tAGT\tACE\t0.02\t0.08\t0.90\n"
    "999\t888\tQ99999\tQ88888\tFOO\tBAR\t0.5\t0.3\t0.2\n"
)


# ---------------------------------------------------------------------------
# BioGRID mock response
# ---------------------------------------------------------------------------

BIOGRID_RESPONSE = {
    "100001": {
        "BIOGRID_ID": 100001,
        "OFFICIAL_SYMBOL_A": "AGT",
        "OFFICIAL_SYMBOL_B": "REN",
        "EXPERIMENTAL_SYSTEM": "Two-hybrid",
        "THROUGHPUT": "High Throughput",
        "PUBMED_ID": "12345678",
        "ORGANISM_A": "Homo sapiens",
        "ORGANISM_B": "Homo sapiens",
        "SCORE": None,
    },
}


# ---------------------------------------------------------------------------
# Open Targets mock responses
# ---------------------------------------------------------------------------

OT_TARGET_INFO_RESPONSE = {
    "data": {
        "target": {
            "id": "ENSG00000135744",
            "approvedSymbol": "AGT",
            "approvedName": "angiotensinogen",
            "biotype": "protein_coding",
            "functionDescriptions": [
                "Essential component of the renin-angiotensin system (RAS)."
            ],
            "proteinIds": [{"id": "P01019", "source": "uniprot_swissprot"}],
            "targetClass": [{"id": "enzyme", "label": "Enzyme"}],
            "tractability": [
                {"label": "Small molecule binder", "modality": "SM", "value": True},
                {"label": "Clinical precedence", "modality": "AB", "value": False},
            ],
        }
    }
}

OT_KNOWN_DRUGS_RESPONSE = {
    "data": {
        "target": {
            "knownDrugs": {
                "uniqueDrugs": 2,
                "rows": [
                    {
                        "drug": {
                            "id": "CHEMBL1234",
                            "name": "LOSARTAN",
                            "drugType": "Small molecule",
                            "mechanismsOfAction": {
                                "rows": [{"mechanismOfAction": "Angiotensin receptor antagonist", "targets": [{"approvedSymbol": "AGT"}]}],
                            },
                            "maximumClinicalTrialPhase": 4,
                            "hasBeenWithdrawn": False,
                            "indications": {"rows": [{"disease": {"name": "Hypertension"}, "maxPhaseForIndication": 4}]},
                        },
                        "disease": {"name": "Hypertension"},
                        "phase": 4,
                        "status": "Approved",
                        "urls": [],
                    },
                    {
                        "drug": {
                            "id": "CHEMBL5678",
                            "name": "VALSARTAN",
                            "drugType": "Small molecule",
                            "mechanismsOfAction": {
                                "rows": [{"mechanismOfAction": "Angiotensin receptor antagonist", "targets": [{"approvedSymbol": "AGT"}]}],
                            },
                            "maximumClinicalTrialPhase": 4,
                            "hasBeenWithdrawn": False,
                            "indications": {"rows": [{"disease": {"name": "Heart failure"}, "maxPhaseForIndication": 4}]},
                        },
                        "disease": {"name": "Heart failure"},
                        "phase": 4,
                        "status": "Approved",
                        "urls": [],
                    },
                ],
            }
        }
    }
}

OT_DISEASE_ASSOC_RESPONSE = {
    "data": {
        "target": {
            "associatedDiseases": {
                "rows": [
                    {
                        "disease": {"id": "EFO:001", "name": "Hypertension"},
                        "score": 0.85,
                        "datasourceScores": [
                            {"id": "genetic_association", "score": 0.9},
                            {"id": "known_drug", "score": 0.7},
                        ],
                    },
                ],
            }
        }
    }
}


# ---------------------------------------------------------------------------
# Complete JSON fixtures for report generation
# ---------------------------------------------------------------------------

@pytest.fixture
def full_literature_json():
    return {
        "rsid": "rs699",
        "gene_symbol": "AGT",
        "pubmed_articles": [
            {"pmid": "12345678", "title": "AGT and hypertension", "authors": "Smith J et al.", "journal": "J Hypertens", "year": "2023", "abstract_snippet": "Study..."},
        ],
        "scholar_articles": [],
        "search_queries_used": ["AGT AND rs699"],
        "errors": [],
    }


@pytest.fixture
def full_patents_json():
    return {
        "rsid": "rs699",
        "gene_symbol": "AGT",
        "patents": [
            {"patent_number": "US-11234567-B2", "title": "AGT inhibitor", "assignee": "Pharma Corp", "date": "2023-01-15", "abstract_snippet": "Novel compound...", "classification": "drug"},
        ],
        "search_queries_used": ["AGT"],
        "errors": [],
    }


@pytest.fixture
def full_clinical_json():
    return {
        "rsid": "rs699",
        "gene_symbol": "AGT",
        "clinvar_entries": [
            {"variant_id": "VCV12345", "clinical_significance": "drug response", "conditions": "Hypertension", "review_status": "criteria provided", "last_evaluated": "2023-01-01"},
        ],
        "clinical_trials": [
            {"nct_id": "NCT12345678", "title": "AGT trial", "phase": "PHASE3", "status": "RECRUITING", "sponsor": "Pharma Corp", "conditions": "Hypertension", "interventions": "AGT-001"},
        ],
        "gwas_associations": [
            {"trait": "Hypertension", "p_value": "3.5e-12", "effect_size": "beta=0.15 mmHg (increase)", "risk_allele": "rs699-C", "study_accession": "GCST001234", "pmid": "27618448"},
        ],
        "errors": [],
    }


@pytest.fixture
def full_protein_json():
    return {
        "rsid": "rs699",
        "gene_symbol": "AGT",
        "string_interactions": {
            "interactions": [
                {"partner": "REN", "preferredName": "REN", "protein_a": "AGT", "protein_b": "REN", "score": 0.999, "combined_score": 0.999, "sources": "experimental, database, textmining", "nscore": 0, "fscore": 0, "pscore": 0, "ascore": 0, "escore": 0.8, "dscore": 0.9, "tscore": 0.95},
            ],
            "errors": [],
        },
        "hpa_expression": {
            "protein_class": "Enzymes",
            "subcellular_location": "Vesicles",
            "tissue_expression": "Liver;Kidney",
            "rna_expression": "Liver: 1234.5 nTPM",
            "errors": [],
        },
        "intact": {
            "database": "IntAct",
            "gene_symbol": "AGT",
            "interactions": [
                {"interactors": ["AGT", "REN"], "interaction_type": "physical association", "detection_method": "anti bait coimmunoprecipitation", "publication": "12345678", "confidence_score": 0.65},
            ],
            "total_count": 1,
            "errors": [],
        },
        "bioplex": {
            "database": "BioPlex",
            "gene_symbol": "AGT",
            "interactions": [
                {"gene_a": "183", "gene_b": "5972", "symbol_a": "AGT", "symbol_b": "REN", "uniprot_a": "P01019", "uniprot_b": "P00797", "p_wrong": 0.01, "p_no_interaction": 0.05, "p_interaction": 0.94},
            ],
            "total_count": 1,
            "errors": [],
        },
        "biogrid": {
            "database": "BioGRID",
            "gene_symbol": "AGT",
            "interactions": [],
            "total_count": 0,
            "errors": ["BIOGRID_API_KEY not set."],
        },
        "errors": ["BIOGRID_API_KEY not set."],
    }


@pytest.fixture
def full_drug_targets_json():
    return {
        "rsid": "rs699",
        "gene_symbol": "AGT",
        "ensembl_gene_id": "ENSG00000135744",
        "target_info": {"description": "Essential component of the RAS.", "protein_class": "Enzyme"},
        "known_drugs": [
            {"drug_name": "LOSARTAN", "drug_type": "Small molecule", "mechanism_of_action": "Angiotensin receptor antagonist", "phase": "Phase 4", "indication": "Hypertension", "company": ""},
        ],
        "disease_associations": [
            {"disease_name": "Hypertension", "overall_score": 0.85, "data_types": "genetic_association, known_drug"},
        ],
        "tractability": {"small_molecule": "Small molecule binder; ", "antibody": "", "other_modalities": ""},
        "data_sources": {"open_targets_url": "https://platform.opentargets.org/target/ENSG00000135744"},
        "errors": [],
    }
