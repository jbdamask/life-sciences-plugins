"""Tests for generate_report.py."""

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from generate_report import (
    load_json_file,
    generate_report,
    _build_competitive_intel,
    _collect_references,
)


TEMPLATE_DIR = str(Path(__file__).parent.parent / "skills" / "variant-research" / "templates")


class TestLoadJsonFile:
    """Tests for the JSON file loader."""

    def test_valid_file(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text(json.dumps({"key": "value"}))
        result = load_json_file(str(f))
        assert result["key"] == "value"

    def test_missing_file(self, tmp_path):
        result = load_json_file(str(tmp_path / "missing.json"))
        assert result["_unavailable"] is True
        assert len(result["errors"]) == 1

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{not valid json")
        result = load_json_file(str(f))
        assert result["_unavailable"] is True


class TestBuildCompetitiveIntel:
    """Tests for competitive intelligence extraction."""

    def test_with_patents_and_trials(self, full_patents_json, full_clinical_json):
        result = _build_competitive_intel(full_patents_json, full_clinical_json)
        companies = result["companies"]
        assert "Pharma Corp" in companies
        assert len(companies["Pharma Corp"]["patents"]) == 1
        assert len(companies["Pharma Corp"]["trials"]) == 1

    def test_empty_data(self):
        result = _build_competitive_intel(
            {"patents": []},
            {"clinical_trials": []},
        )
        assert result["companies"] == {}

    def test_unavailable_data(self):
        result = _build_competitive_intel(
            {"_unavailable": True},
            {"_unavailable": True},
        )
        assert result["companies"] == {}

    def test_multiple_companies(self):
        patents = {"patents": [
            {"assignee": "CompanyA", "title": "P1", "date": "2023", "patent_number": "US-1"},
            {"assignee": "CompanyB", "title": "P2", "date": "2023", "patent_number": "US-2"},
        ]}
        clinical = {"clinical_trials": [
            {"sponsor": "CompanyA", "title": "T1", "phase": "3", "status": "RECRUITING", "nct_id": "NCT001"},
        ]}
        result = _build_competitive_intel(patents, clinical)
        assert len(result["companies"]) == 2
        assert len(result["companies"]["CompanyA"]["patents"]) == 1
        assert len(result["companies"]["CompanyA"]["trials"]) == 1


class TestCollectReferences:
    """Tests for reference collection."""

    def test_pubmed_references(self, full_literature_json):
        refs = _collect_references(full_literature_json, {"patents": []}, {"clinical_trials": []}, {}, {})
        assert len(refs) == 1
        assert refs[0]["source"] == "PubMed"
        assert refs[0]["id"] == "12345678"
        assert "pubmed" in refs[0]["url"]

    def test_deduplication(self, full_literature_json, full_protein_json):
        # IntAct interaction has same PMID 12345678 as literature
        refs = _collect_references(full_literature_json, {"patents": []}, {"clinical_trials": []}, full_protein_json, {})
        pmids = [r["id"] for r in refs if r["id"] == "12345678"]
        assert len(pmids) == 1  # Should be deduplicated

    def test_intact_and_biogrid_pmids(self, full_protein_json):
        refs = _collect_references(
            {"pubmed_articles": [], "scholar_articles": []},
            {"patents": []},
            {"clinical_trials": []},
            full_protein_json,
            {},
        )
        pmids = [r["id"] for r in refs]
        assert "12345678" in pmids

    def test_empty_data(self):
        refs = _collect_references(
            {"pubmed_articles": [], "scholar_articles": []},
            {"patents": []},
            {"clinical_trials": []},
            {},
            {},
        )
        assert refs == []


class TestGenerateReport:
    """Tests for the full report generation pipeline."""

    def test_full_report(self, tmp_reports_dir, variant_info,
                         full_literature_json, full_patents_json,
                         full_clinical_json, full_protein_json,
                         full_drug_targets_json):
        """Generate a complete report with all data present."""
        # Write all JSON files
        (tmp_reports_dir / "rs699_variant.json").write_text(json.dumps(variant_info))
        (tmp_reports_dir / "rs699_literature.json").write_text(json.dumps(full_literature_json))
        (tmp_reports_dir / "rs699_patents.json").write_text(json.dumps(full_patents_json))
        (tmp_reports_dir / "rs699_clinical.json").write_text(json.dumps(full_clinical_json))
        (tmp_reports_dir / "rs699_protein.json").write_text(json.dumps(full_protein_json))
        (tmp_reports_dir / "rs699_drug_targets.json").write_text(json.dumps(full_drug_targets_json))

        output = generate_report("rs699", str(tmp_reports_dir), TEMPLATE_DIR)
        assert Path(output).exists()

        html = Path(output).read_text()
        assert "RS699" in html  # rsid is upper-cased in template
        assert "AGT" in html
        assert "Hypertension" in html
        assert "LOSARTAN" in html
        assert "Pharma Corp" in html

    def test_missing_all_data_files(self, tmp_reports_dir, variant_info):
        """Report should still generate with only variant info."""
        (tmp_reports_dir / "rs699_variant.json").write_text(json.dumps(variant_info))

        output = generate_report("rs699", str(tmp_reports_dir), TEMPLATE_DIR)
        html = Path(output).read_text()
        assert "RS699" in html
        assert "unavailable" in html.lower() or "data unavailable" in html.lower()

    def test_missing_variant_file(self, tmp_reports_dir):
        """Even if variant file is missing, report should still render."""
        output = generate_report("rs699", str(tmp_reports_dir), TEMPLATE_DIR)
        html = Path(output).read_text()
        assert "Unknown" in html  # gene_symbol defaults to "Unknown"

    def test_custom_output_path(self, tmp_reports_dir, variant_info):
        (tmp_reports_dir / "rs699_variant.json").write_text(json.dumps(variant_info))
        custom_path = str(tmp_reports_dir / "custom_report.html")
        output = generate_report("rs699", str(tmp_reports_dir), TEMPLATE_DIR, output_path=custom_path)
        assert output == custom_path
        assert Path(custom_path).exists()

    def test_report_has_all_sections(self, tmp_reports_dir, variant_info,
                                     full_literature_json, full_patents_json,
                                     full_clinical_json, full_protein_json,
                                     full_drug_targets_json):
        """Verify all 9 sections are present in the output."""
        (tmp_reports_dir / "rs699_variant.json").write_text(json.dumps(variant_info))
        (tmp_reports_dir / "rs699_literature.json").write_text(json.dumps(full_literature_json))
        (tmp_reports_dir / "rs699_patents.json").write_text(json.dumps(full_patents_json))
        (tmp_reports_dir / "rs699_clinical.json").write_text(json.dumps(full_clinical_json))
        (tmp_reports_dir / "rs699_protein.json").write_text(json.dumps(full_protein_json))
        (tmp_reports_dir / "rs699_drug_targets.json").write_text(json.dumps(full_drug_targets_json))

        output = generate_report("rs699", str(tmp_reports_dir), TEMPLATE_DIR)
        html = Path(output).read_text()

        section_ids = [
            "variant-summary", "clinical-significance", "gwas",
            "literature", "patents", "protein", "drug-targets",
            "competitive-intel", "references",
        ]
        for section_id in section_ids:
            assert f'id="{section_id}"' in html, f"Missing section: {section_id}"

    def test_report_with_errors_in_data(self, tmp_reports_dir, variant_info):
        """Report should render error messages gracefully."""
        (tmp_reports_dir / "rs699_variant.json").write_text(json.dumps(variant_info))

        # Literature with errors
        lit = {"rsid": "rs699", "pubmed_articles": [], "scholar_articles": [],
               "errors": ["PubMed search failed: timeout", "Google Scholar not available"]}
        (tmp_reports_dir / "rs699_literature.json").write_text(json.dumps(lit))

        output = generate_report("rs699", str(tmp_reports_dir), TEMPLATE_DIR)
        html = Path(output).read_text()
        assert "timeout" in html

    def test_string_data_renders_correctly(self, tmp_reports_dir, variant_info, full_protein_json):
        """Verify STRING interaction partner names and scores render in the report (not dashes)."""
        (tmp_reports_dir / "rs699_variant.json").write_text(json.dumps(variant_info))
        (tmp_reports_dir / "rs699_protein.json").write_text(json.dumps(full_protein_json))

        output = generate_report("rs699", str(tmp_reports_dir), TEMPLATE_DIR)
        html = Path(output).read_text()
        assert "STRING-db" in html
        # Partner name should appear in the rendered HTML (not a dash)
        assert "REN" in html
        # Score should appear
        assert "0.999" in html
        # Sources should appear
        assert "experimental" in html
