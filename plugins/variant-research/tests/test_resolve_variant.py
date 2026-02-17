"""Tests for resolve_variant.py."""

from unittest.mock import patch, MagicMock
import pytest

from conftest import make_mock_response, MYVARIANT_RESPONSE
from resolve_variant import resolve_variant, _lookup_gene_name


class TestResolveVariant:
    """Tests for the resolve_variant() function."""

    @patch("resolve_variant.requests.get")
    @patch("resolve_variant._lookup_gene_name", return_value="angiotensinogen")
    def test_successful_resolution(self, mock_gene_name, mock_get):
        mock_get.return_value = make_mock_response(json_data=MYVARIANT_RESPONSE)
        result = resolve_variant("rs699")

        assert result["rsid"] == "rs699"
        assert result["gene_symbol"] == "AGT"
        assert result["chromosome"] == "1"
        assert result["position"] == 230710048
        assert result["alleles"] == "T>C"
        assert result["consequence"] == "missense_variant"
        assert result["protein_change"] == "p.Met268Thr"
        assert result["clinvar_significance"] == "drug response"
        assert result["ensembl_gene_id"] == "ENSG00000135744"
        assert result["errors"] == []

    @patch("resolve_variant.requests.get")
    def test_no_hits(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"hits": []})
        result = resolve_variant("rs999999999")

        assert result["gene_symbol"] is None
        assert len(result["errors"]) == 1
        assert "No hits found" in result["errors"][0]

    def test_invalid_rsid_format(self):
        result = resolve_variant("BRCA1")
        assert "error" in result
        assert "Invalid rsID format" in result["error"]

    def test_rsid_case_insensitive(self):
        with patch("resolve_variant.requests.get") as mock_get:
            mock_get.return_value = make_mock_response(json_data=MYVARIANT_RESPONSE)
            with patch("resolve_variant._lookup_gene_name", return_value=None):
                result = resolve_variant("RS699")
                assert result["rsid"] == "rs699"

    @patch("resolve_variant.requests.get")
    def test_network_failure_with_retry(self, mock_get):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("Connection refused")
        result = resolve_variant("rs699", max_retries=1)

        assert result["gene_symbol"] is None
        assert len(result["errors"]) == 1
        assert "API request failed" in result["errors"][0]
        assert mock_get.call_count == 2  # initial + 1 retry

    @patch("resolve_variant.requests.get")
    @patch("resolve_variant._lookup_gene_name", return_value=None)
    def test_gene_symbol_fallback_to_cadd(self, mock_gene_name, mock_get):
        """When dbnsfp.genename is missing, fall back to cadd.gene.genename."""
        response = {
            "hits": [{
                "dbsnp": {"rsid": "rs699", "chrom": "1", "hg19": {}},
                "dbnsfp": {},
                "cadd": {"gene": {"genename": "AGT"}},
            }],
        }
        mock_get.return_value = make_mock_response(json_data=response)
        result = resolve_variant("rs699")
        assert result["gene_symbol"] == "AGT"

    @patch("resolve_variant.requests.get")
    @patch("resolve_variant._lookup_gene_name", return_value=None)
    def test_gene_symbol_fallback_to_dbsnp(self, mock_gene_name, mock_get):
        """When dbnsfp and cadd are missing, fall back to dbsnp.gene.symbol."""
        response = {
            "hits": [{
                "dbsnp": {"rsid": "rs699", "chrom": "1", "hg19": {}, "gene": {"symbol": "AGT"}},
                "dbnsfp": {},
                "cadd": {},
            }],
        }
        mock_get.return_value = make_mock_response(json_data=response)
        result = resolve_variant("rs699")
        assert result["gene_symbol"] == "AGT"

    @patch("resolve_variant.requests.get")
    @patch("resolve_variant._lookup_gene_name", return_value=None)
    def test_gene_symbol_all_fallbacks_fail(self, mock_gene_name, mock_get):
        """When all gene symbol sources are missing."""
        response = {"hits": [{"dbsnp": {"chrom": "1", "hg19": {}}}]}
        mock_get.return_value = make_mock_response(json_data=response)
        result = resolve_variant("rs699")
        assert result["gene_symbol"] is None

    @patch("resolve_variant.requests.get")
    @patch("resolve_variant._lookup_gene_name", return_value=None)
    def test_list_type_gene_symbol(self, mock_gene_name, mock_get):
        """Handle dbnsfp.genename being a list."""
        response = {
            "hits": [{
                "dbsnp": {"chrom": "1", "hg19": {}},
                "dbnsfp": {"genename": ["AGT", "SERPINA8"]},
            }],
        }
        mock_get.return_value = make_mock_response(json_data=response)
        result = resolve_variant("rs699")
        assert result["gene_symbol"] == "AGT"

    @patch("resolve_variant.requests.get")
    @patch("resolve_variant._lookup_gene_name", return_value=None)
    def test_list_type_ensembl_id(self, mock_gene_name, mock_get):
        """Handle ensembl.geneid being a list."""
        response = {
            "hits": [{
                "dbsnp": {"chrom": "1", "hg19": {}},
                "dbnsfp": {
                    "genename": "AGT",
                    "ensembl": {"geneid": ["ENSG00000135744", "ENSG00000135745"]},
                },
            }],
        }
        mock_get.return_value = make_mock_response(json_data=response)
        result = resolve_variant("rs699")
        assert result["ensembl_gene_id"] == "ENSG00000135744"

    @patch("resolve_variant.requests.get")
    @patch("resolve_variant._lookup_gene_name", return_value=None)
    def test_cadd_gene_as_list(self, mock_gene_name, mock_get):
        """Handle cadd.gene being a list of dicts."""
        response = {
            "hits": [{
                "dbsnp": {"chrom": "1", "hg19": {}},
                "dbnsfp": {},
                "cadd": {"gene": [{"genename": "AGT"}, {"genename": "OTHER"}]},
            }],
        }
        mock_get.return_value = make_mock_response(json_data=response)
        result = resolve_variant("rs699")
        assert result["gene_symbol"] == "AGT"

    @patch("resolve_variant.requests.get")
    @patch("resolve_variant._lookup_gene_name", return_value=None)
    def test_clinvar_rcv_as_list(self, mock_gene_name, mock_get):
        """Handle clinvar.rcv being a list."""
        response = {
            "hits": [{
                "dbsnp": {"chrom": "1", "hg19": {}},
                "dbnsfp": {"genename": "AGT"},
                "clinvar": {"rcv": [
                    {"clinical_significance": "Pathogenic"},
                    {"clinical_significance": "Likely pathogenic"},
                ]},
            }],
        }
        mock_get.return_value = make_mock_response(json_data=response)
        result = resolve_variant("rs699")
        assert result["clinvar_significance"] == "Pathogenic"

    @patch("resolve_variant.requests.get")
    @patch("resolve_variant._lookup_gene_name", return_value=None)
    def test_snpeff_ann_as_list(self, mock_gene_name, mock_get):
        """Handle snpeff.ann being a list."""
        response = {
            "hits": [{
                "dbsnp": {"chrom": "1", "hg19": {}},
                "dbnsfp": {"genename": "AGT"},
                "snpeff": {"ann": [
                    {"effect": "missense_variant", "hgvs_p": "p.Met268Thr"},
                    {"effect": "synonymous_variant"},
                ]},
            }],
        }
        mock_get.return_value = make_mock_response(json_data=response)
        result = resolve_variant("rs699")
        assert result["consequence"] == "missense_variant"


class TestLookupGeneName:
    """Tests for the _lookup_gene_name() helper."""

    @patch("resolve_variant.requests.get")
    def test_successful_lookup(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={
            "hits": [{"name": "angiotensinogen"}],
        })
        assert _lookup_gene_name("AGT") == "angiotensinogen"

    @patch("resolve_variant.requests.get")
    def test_no_hits(self, mock_get):
        mock_get.return_value = make_mock_response(json_data={"hits": []})
        assert _lookup_gene_name("XYZXYZ") is None

    @patch("resolve_variant.requests.get")
    def test_network_failure_returns_none(self, mock_get):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("fail")
        assert _lookup_gene_name("AGT") is None
