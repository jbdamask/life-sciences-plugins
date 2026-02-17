"""Tests for fetch_clinical.py."""

from unittest.mock import patch
import pytest

from conftest import (
    make_mock_response,
    CLINVAR_ESEARCH_RESPONSE,
    CLINVAR_ESUMMARY_RESPONSE,
    CTGOV_RESPONSE,
    GWAS_RESPONSE,
    GWAS_STUDY_RESPONSE,
)
from fetch_clinical import (
    fetch_clinvar,
    fetch_clinical_trials,
    fetch_gwas_associations,
    fetch_all_clinical,
)


class TestFetchClinvar:
    """Tests for ClinVar search."""

    @patch("fetch_clinical.requests.get")
    def test_successful_fetch(self, mock_get):
        mock_get.side_effect = [
            make_mock_response(json_data=CLINVAR_ESEARCH_RESPONSE),
            make_mock_response(json_data=CLINVAR_ESUMMARY_RESPONSE),
        ]
        entries = fetch_clinvar("rs699", "AGT")
        assert len(entries) == 1
        assert entries[0]["clinical_significance"] == "drug response"
        assert entries[0]["conditions"] == "Hypertension"
        assert entries[0]["review_status"] == "criteria provided, single submitter"

    @patch("fetch_clinical.requests.get")
    def test_no_ids_found(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={
            "esearchresult": {"idlist": []},
        })
        entries = fetch_clinvar("rs999999", "FAKE")
        assert entries == []

    @patch("fetch_clinical.requests.get")
    def test_network_failure(self, mock_get):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("fail")
        entries = fetch_clinvar("rs699", "AGT")
        assert len(entries) == 1
        assert "error" in entries[0]

    @patch("fetch_clinical.requests.get")
    def test_clinical_significance_as_string(self, mock_get):
        """Some ClinVar entries have clinical_significance as a plain string."""
        summary = {
            "result": {
                "uids": ["999"],
                "999": {
                    "uid": "999",
                    "clinical_significance": "Pathogenic",
                    "trait_set": [],
                    "variation_set": [],
                },
            },
        }
        mock_get.side_effect = [
            make_mock_response(json_data={"esearchresult": {"idlist": ["999"]}}),
            make_mock_response(json_data=summary),
        ]
        entries = fetch_clinvar("rs699", "AGT")
        assert entries[0]["clinical_significance"] == "Pathogenic"


class TestFetchClinicalTrials:
    """Tests for ClinicalTrials.gov search."""

    @patch("fetch_clinical.requests.get")
    def test_successful_fetch(self, mock_get):
        mock_get.return_value = make_mock_response(json_data=CTGOV_RESPONSE)
        trials = fetch_clinical_trials("AGT")
        assert len(trials) == 1
        assert trials[0]["nct_id"] == "NCT12345678"
        assert trials[0]["status"] == "RECRUITING"
        assert trials[0]["sponsor"] == "Pharma Corp"
        assert "PHASE3" in trials[0]["phase"]
        assert "AGT-001" in trials[0]["interventions"]

    @patch("fetch_clinical.requests.get")
    def test_empty_result(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"studies": []})
        trials = fetch_clinical_trials("NONEXISTENT")
        assert trials == []

    @patch("fetch_clinical.requests.get")
    def test_network_failure(self, mock_get):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("fail")
        trials = fetch_clinical_trials("AGT")
        assert len(trials) == 1
        assert "error" in trials[0]

    @patch("fetch_clinical.requests.get")
    def test_missing_optional_fields(self, mock_get):
        """Study missing optional fields should not crash."""
        response = {"studies": [{
            "protocolSection": {
                "identificationModule": {"nctId": "NCT00000001"},
                "statusModule": {},
                "designModule": {},
                "sponsorCollaboratorsModule": {},
                "conditionsModule": {},
                "armsInterventionsModule": {},
            },
        }]}
        mock_get.return_value = make_mock_response(json_data=response)
        trials = fetch_clinical_trials("AGT")
        assert trials[0]["nct_id"] == "NCT00000001"
        assert trials[0]["phase"] == "Not specified"


class TestFetchGwasAssociations:
    """Tests for GWAS Catalog search."""

    @patch("fetch_clinical.requests.get")
    def test_successful_fetch(self, mock_get):
        mock_get.side_effect = [
            make_mock_response(json_data=GWAS_RESPONSE),       # associations
            make_mock_response(json_data=GWAS_STUDY_RESPONSE),  # study for PMID
        ]
        assocs = fetch_gwas_associations("rs699")
        assert len(assocs) == 1
        assert assocs[0]["trait"] == "Hypertension"
        assert assocs[0]["p_value"] == "3.5e-12"
        assert "beta=0.15" in assocs[0]["effect_size"]
        assert assocs[0]["risk_allele"] == "rs699-C"
        assert assocs[0]["study_accession"] == "GCST001234"
        assert assocs[0]["pmid"] == "27618448"

    @patch("fetch_clinical.requests.get")
    def test_404_returns_empty(self, mock_get):
        resp = make_mock_response(status_code=404, raise_for_status=False)
        resp.status_code = 404
        mock_get.return_value = resp
        assocs = fetch_gwas_associations("rs999999999")
        assert assocs == []

    @patch("fetch_clinical.requests.get")
    def test_or_effect_size(self, mock_get):
        """Test odds ratio instead of beta."""
        or_response = {"_embedded": {"associations": [{
            "efoTraits": [{"trait": "Diabetes"}],
            "pvalueMantissa": 1.2,
            "pvalueExponent": -8,
            "orPerCopyNum": 1.35,
            "range": "[1.2-1.5]",
            "loci": [{"strongestRiskAlleles": [{"riskAlleleName": "rs699-A"}]}],
            "_links": {"study": {"href": "https://www.ebi.ac.uk/gwas/rest/api/studies/GCST999"}},
        }]}}
        study_resp = {"publicationInfo": {"pubmedId": "99999999"}}
        mock_get.side_effect = [
            make_mock_response(json_data=or_response),     # associations
            make_mock_response(json_data=study_resp),       # study for PMID
        ]
        assocs = fetch_gwas_associations("rs699")
        assert "OR=1.35" in assocs[0]["effect_size"]
        assert assocs[0]["pmid"] == "99999999"

    @patch("fetch_clinical.requests.get")
    def test_pmid_populated_from_study(self, mock_get):
        """PMID is now fetched from the study endpoint linked in each association."""
        mock_get.side_effect = [
            make_mock_response(json_data=GWAS_RESPONSE),       # associations
            make_mock_response(json_data=GWAS_STUDY_RESPONSE),  # study for PMID
        ]
        assocs = fetch_gwas_associations("rs699")
        assert assocs[0]["pmid"] == "27618448"

    @patch("fetch_clinical.requests.get")
    def test_pmid_empty_when_study_fetch_fails(self, mock_get):
        """PMID falls back to empty string if the study endpoint fails."""
        from requests.exceptions import ConnectionError
        mock_get.side_effect = [
            make_mock_response(json_data=GWAS_RESPONSE),  # associations
            ConnectionError("study fetch failed"),         # study endpoint fails
        ]
        assocs = fetch_gwas_associations("rs699")
        assert len(assocs) == 1
        assert assocs[0]["pmid"] == ""


class TestFetchAllClinical:
    """Tests for the orchestrating fetch_all_clinical() function."""

    @patch("fetch_clinical.fetch_gwas_associations")
    @patch("fetch_clinical.fetch_clinical_trials")
    @patch("fetch_clinical.fetch_clinvar")
    def test_successful_fetch_all(self, mock_clinvar, mock_trials, mock_gwas):
        mock_clinvar.return_value = [{"clinical_significance": "Pathogenic", "conditions": "Test"}]
        mock_trials.return_value = [{"nct_id": "NCT001", "title": "Test trial"}]
        mock_gwas.return_value = [{"trait": "Hypertension", "p_value": "1e-10"}]

        result = fetch_all_clinical("rs699", "AGT")
        assert len(result["clinvar_entries"]) == 1
        assert len(result["clinical_trials"]) == 1
        assert len(result["gwas_associations"]) == 1
        assert result["errors"] == []

    @patch("fetch_clinical.fetch_gwas_associations")
    @patch("fetch_clinical.fetch_clinical_trials")
    @patch("fetch_clinical.fetch_clinvar")
    def test_error_entries_separated(self, mock_clinvar, mock_trials, mock_gwas):
        """Error entries from sub-functions should be moved to errors list."""
        mock_clinvar.return_value = [{"error": "ClinVar search failed: timeout"}]
        mock_trials.return_value = []
        mock_gwas.return_value = []

        result = fetch_all_clinical("rs699", "AGT")
        assert result["clinvar_entries"] == []
        assert "ClinVar search failed: timeout" in result["errors"]

    @patch("fetch_clinical.fetch_gwas_associations")
    @patch("fetch_clinical.fetch_clinical_trials")
    @patch("fetch_clinical.fetch_clinvar")
    def test_exception_in_source_continues(self, mock_clinvar, mock_trials, mock_gwas):
        """If one source throws an unexpected exception, others continue."""
        mock_clinvar.side_effect = RuntimeError("unexpected")
        mock_trials.return_value = [{"nct_id": "NCT001"}]
        mock_gwas.return_value = []

        result = fetch_all_clinical("rs699", "AGT")
        assert len(result["clinical_trials"]) == 1
        assert any("ClinVar failed" in e for e in result["errors"])
