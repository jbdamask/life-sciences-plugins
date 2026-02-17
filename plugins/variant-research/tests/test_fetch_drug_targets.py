"""Tests for fetch_drug_targets.py."""

from unittest.mock import patch
import pytest

from conftest import (
    make_mock_response,
    OT_TARGET_INFO_RESPONSE,
    OT_KNOWN_DRUGS_RESPONSE,
    OT_DISEASE_ASSOC_RESPONSE,
)
from fetch_drug_targets import (
    _graphql_query,
    fetch_target_info,
    fetch_known_drugs,
    fetch_disease_associations,
    fetch_all_drug_targets,
)


class TestGraphqlQuery:
    """Tests for the GraphQL helper."""

    @patch("fetch_drug_targets.requests.post")
    def test_successful_query(self, mock_post):
        mock_post.return_value = make_mock_response(json_data={"data": {"target": {"id": "test"}}})
        result = _graphql_query("query { target { id } }")
        assert result["data"]["target"]["id"] == "test"

    @patch("fetch_drug_targets.requests.post")
    def test_with_variables(self, mock_post):
        mock_post.return_value = make_mock_response(json_data={"data": {}})
        _graphql_query("query($id: String!) { target(id: $id) { id } }", {"id": "ENSG001"})
        call_kwargs = mock_post.call_args
        assert "variables" in call_kwargs.kwargs["json"]

    @patch("fetch_drug_targets.requests.post")
    def test_network_failure(self, mock_post):
        from requests.exceptions import ConnectionError
        mock_post.side_effect = ConnectionError("fail")
        with pytest.raises(ConnectionError):
            _graphql_query("query { target { id } }")


class TestFetchTargetInfo:
    """Tests for target info retrieval."""

    @patch("fetch_drug_targets._graphql_query")
    def test_successful_fetch(self, mock_gql):
        mock_gql.return_value = OT_TARGET_INFO_RESPONSE
        result = fetch_target_info("ENSG00000135744")
        assert result["approvedSymbol"] == "AGT"
        assert len(result["tractability"]) == 2

    @patch("fetch_drug_targets._graphql_query")
    def test_target_not_found(self, mock_gql):
        mock_gql.return_value = {"data": {"target": None}}
        result = fetch_target_info("ENSG_NONEXISTENT")
        assert result is None


class TestFetchKnownDrugs:
    """Tests for known drugs retrieval."""

    @patch("fetch_drug_targets._graphql_query")
    def test_successful_fetch(self, mock_gql):
        mock_gql.return_value = OT_KNOWN_DRUGS_RESPONSE
        drugs = fetch_known_drugs("ENSG00000135744")
        assert len(drugs) == 2
        assert drugs[0]["drug_name"] == "LOSARTAN"
        assert drugs[0]["drug_type"] == "Small molecule"
        assert drugs[0]["mechanism_of_action"] == "Angiotensin receptor antagonist"
        assert "4" in drugs[0]["phase"]

    @patch("fetch_drug_targets._graphql_query")
    def test_deduplicates_by_name(self, mock_gql):
        """Same drug appearing in multiple rows should be deduplicated."""
        response = OT_KNOWN_DRUGS_RESPONSE.copy()
        # Duplicate LOSARTAN row
        rows = response["data"]["target"]["knownDrugs"]["rows"]
        response["data"]["target"]["knownDrugs"]["rows"] = rows + [rows[0]]
        mock_gql.return_value = response
        drugs = fetch_known_drugs("ENSG00000135744")
        drug_names = [d["drug_name"] for d in drugs]
        assert len(drug_names) == len(set(drug_names))

    @patch("fetch_drug_targets._graphql_query")
    def test_empty_drugs(self, mock_gql):
        mock_gql.return_value = {"data": {"target": {"knownDrugs": {"rows": []}}}}
        drugs = fetch_known_drugs("ENSG00000135744")
        assert drugs == []

    @patch("fetch_drug_targets._graphql_query")
    def test_missing_knownDrugs_key(self, mock_gql):
        """Handle target with no knownDrugs data."""
        mock_gql.return_value = {"data": {"target": {}}}
        drugs = fetch_known_drugs("ENSG00000135744")
        assert drugs == []


class TestFetchDiseaseAssociations:
    """Tests for disease association retrieval."""

    @patch("fetch_drug_targets._graphql_query")
    def test_successful_fetch(self, mock_gql):
        mock_gql.return_value = OT_DISEASE_ASSOC_RESPONSE
        assocs = fetch_disease_associations("ENSG00000135744")
        assert len(assocs) == 1
        assert assocs[0]["disease_name"] == "Hypertension"
        assert assocs[0]["overall_score"] == 0.85
        assert "genetic_association" in assocs[0]["data_types"]

    @patch("fetch_drug_targets._graphql_query")
    def test_filters_zero_score_sources(self, mock_gql):
        response = {"data": {"target": {"associatedDiseases": {"rows": [{
            "disease": {"id": "EFO:001", "name": "Test"},
            "score": 0.5,
            "datasourceScores": [
                {"id": "active_source", "score": 0.5},
                {"id": "inactive_source", "score": 0},
            ],
        }]}}}}
        mock_gql.return_value = response
        assocs = fetch_disease_associations("ENSG00000135744")
        assert "active_source" in assocs[0]["data_types"]
        assert "inactive_source" not in assocs[0]["data_types"]


class TestFetchAllDrugTargets:
    """Tests for the orchestrating function."""

    @patch("fetch_drug_targets.fetch_disease_associations")
    @patch("fetch_drug_targets.fetch_known_drugs")
    @patch("fetch_drug_targets.fetch_target_info")
    def test_successful_fetch_all(self, mock_target, mock_drugs, mock_diseases):
        mock_target.return_value = OT_TARGET_INFO_RESPONSE["data"]["target"]
        mock_drugs.return_value = [{"drug_name": "LOSARTAN"}]
        mock_diseases.return_value = [{"disease_name": "Hypertension", "overall_score": 0.85}]

        result = fetch_all_drug_targets("rs699", "AGT", "ENSG00000135744")
        assert result["rsid"] == "rs699"
        assert result["target_info"]["description"].startswith("Essential")
        assert len(result["known_drugs"]) == 1
        assert len(result["disease_associations"]) == 1
        assert "small_molecule" in result["tractability"]

    def test_missing_ensembl_id(self):
        result = fetch_all_drug_targets("rs699", "AGT", "")
        assert len(result["errors"]) == 1
        assert "No ensembl_gene_id" in result["errors"][0]

    @patch("fetch_drug_targets.fetch_disease_associations")
    @patch("fetch_drug_targets.fetch_known_drugs")
    @patch("fetch_drug_targets.fetch_target_info")
    def test_target_not_found(self, mock_target, mock_drugs, mock_diseases):
        mock_target.return_value = None  # Target not in OT
        mock_drugs.return_value = []
        mock_diseases.return_value = []

        result = fetch_all_drug_targets("rs699", "AGT", "ENSG_BAD")
        assert any("Target not found" in e for e in result["errors"])

    @patch("fetch_drug_targets.fetch_disease_associations")
    @patch("fetch_drug_targets.fetch_known_drugs")
    @patch("fetch_drug_targets.fetch_target_info")
    def test_partial_failure(self, mock_target, mock_drugs, mock_diseases):
        """If drugs query fails, target info and diseases should still work."""
        from requests.exceptions import ConnectionError
        mock_target.return_value = OT_TARGET_INFO_RESPONSE["data"]["target"]
        mock_drugs.side_effect = ConnectionError("timeout")
        mock_diseases.return_value = [{"disease_name": "Hypertension"}]

        result = fetch_all_drug_targets("rs699", "AGT", "ENSG00000135744")
        assert result["target_info"] != {}
        assert len(result["disease_associations"]) == 1
        assert any("drug query failed" in e for e in result["errors"])

    @patch("fetch_drug_targets.fetch_disease_associations")
    @patch("fetch_drug_targets.fetch_known_drugs")
    @patch("fetch_drug_targets.fetch_target_info")
    def test_tractability_parsing(self, mock_target, mock_drugs, mock_diseases):
        mock_target.return_value = OT_TARGET_INFO_RESPONSE["data"]["target"]
        mock_drugs.return_value = []
        mock_diseases.return_value = []

        result = fetch_all_drug_targets("rs699", "AGT", "ENSG00000135744")
        assert "Small molecule binder" in result["tractability"]["small_molecule"]
        # AB value is False, so it should be empty
        assert result["tractability"]["antibody"] == ""

    @patch("fetch_drug_targets.fetch_disease_associations")
    @patch("fetch_drug_targets.fetch_known_drugs")
    @patch("fetch_drug_targets.fetch_target_info")
    def test_open_targets_url(self, mock_target, mock_drugs, mock_diseases):
        mock_target.return_value = OT_TARGET_INFO_RESPONSE["data"]["target"]
        mock_drugs.return_value = []
        mock_diseases.return_value = []

        result = fetch_all_drug_targets("rs699", "AGT", "ENSG00000135744")
        assert "ENSG00000135744" in result["data_sources"]["open_targets_url"]
