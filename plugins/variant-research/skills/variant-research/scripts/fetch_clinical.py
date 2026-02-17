#!/usr/bin/env python3
"""Fetch clinical data from ClinVar, ClinicalTrials.gov, and GWAS Catalog.

Produces reports/{rsid}_clinical.json with clinvar_entries, clinical_trials,
and gwas_associations.
"""

import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"
GWAS_API = "https://www.ebi.ac.uk/gwas/rest/api"


def fetch_clinvar(rsid: str, gene_symbol: str) -> list[dict]:
    """Search ClinVar via NCBI E-utilities for the given rsID."""
    entries = []

    try:
        # Search ClinVar for just the rsID
        resp = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params={
            "db": "clinvar",
            "term": rsid,
            "retmode": "json",
            "retmax": 20,
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        ids = data.get("esearchresult", {}).get("idlist", [])

        if not ids:
            return entries

        time.sleep(1.5)

        # Get summaries
        resp = requests.get(f"{EUTILS_BASE}/esummary.fcgi", params={
            "db": "clinvar",
            "id": ",".join(ids),
            "retmode": "json",
        }, timeout=30)
        resp.raise_for_status()
        summary_data = resp.json()

        results = summary_data.get("result", {})
        for uid in ids:
            entry = results.get(uid, {})
            if not entry or uid == "uids":
                continue

            # Classification lives under germline_classification (current API)
            germline = entry.get("germline_classification", {})
            if not isinstance(germline, dict):
                germline = {}

            clin_sig = germline.get("description", "")
            review_status = germline.get("review_status", "")
            last_evaluated = germline.get("last_evaluated", "")

            # Conditions are nested inside germline_classification.trait_set
            conditions = []
            trait_set = germline.get("trait_set", [])
            if isinstance(trait_set, list):
                for trait in trait_set:
                    if isinstance(trait, dict):
                        trait_name = trait.get("trait_name", "")
                        if trait_name:
                            conditions.append(trait_name)

            # Accession (e.g. VCV000441269)
            accession = entry.get("accession", "")
            title = entry.get("title", "")

            entries.append({
                "variant_id": accession or uid,
                "title": title,
                "clinical_significance": clin_sig,
                "conditions": "; ".join(conditions) if conditions else "",
                "review_status": review_status,
                "last_evaluated": last_evaluated,
            })

    except requests.RequestException as e:
        entries.append({"error": f"ClinVar search failed: {str(e)}"})

    return entries


def fetch_clinical_trials(gene_symbol: str) -> list[dict]:
    """Search ClinicalTrials.gov v2 API for trials targeting the gene."""
    trials = []

    try:
        resp = requests.get(CTGOV_API, params={
            "query.term": gene_symbol,
            "pageSize": 20,
            "format": "json",
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            design_module = protocol.get("designModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            conditions_module = protocol.get("conditionsModule", {})
            arms_module = protocol.get("armsInterventionsModule", {})

            # NCT ID
            nct_id = id_module.get("nctId", "")

            # Title
            title = id_module.get("officialTitle", id_module.get("briefTitle", ""))

            # Phase
            phases = design_module.get("phases", [])
            phase = ", ".join(phases) if phases else "Not specified"

            # Status
            status = status_module.get("overallStatus", "")

            # Sponsor
            sponsor = ""
            lead_sponsor = sponsor_module.get("leadSponsor", {})
            if isinstance(lead_sponsor, dict):
                sponsor = lead_sponsor.get("name", "")

            # Conditions
            conditions = conditions_module.get("conditions", [])
            conditions_str = "; ".join(conditions) if conditions else ""

            # Interventions
            interventions = []
            for arm_int in arms_module.get("interventions", []):
                name = arm_int.get("name", "")
                int_type = arm_int.get("type", "")
                desc = arm_int.get("description", "")
                if name:
                    entry = f"{name} ({int_type})" if int_type else name
                    if desc:
                        entry += f" - {desc[:150]}"
                    interventions.append(entry)

            trials.append({
                "nct_id": nct_id,
                "title": title,
                "phase": phase,
                "status": status,
                "sponsor": sponsor,
                "conditions": conditions_str,
                "interventions": "; ".join(interventions) if interventions else "",
            })

    except requests.RequestException as e:
        trials.append({"error": f"ClinicalTrials.gov search failed: {str(e)}"})

    return trials


def _fetch_gwas_study_pmids(study_urls: list[str]) -> dict[str, str]:
    """Fetch PMIDs for a list of GWAS Catalog study URLs.

    Returns a mapping of study_url -> pmid (as string).
    Failures are silently skipped (returning empty string for that URL).
    """
    pmid_map: dict[str, str] = {}
    for url in study_urls:
        if not url:
            continue
        try:
            time.sleep(0.2)
            resp = requests.get(url, headers={"Accept": "application/json"}, timeout=30)
            resp.raise_for_status()
            study_data = resp.json()
            pub_info = study_data.get("publicationInfo", {})
            raw_pmid = pub_info.get("pubmedId")
            if raw_pmid is not None:
                pmid_map[url] = str(raw_pmid)
        except (requests.RequestException, ValueError, KeyError):
            pass
    return pmid_map


def fetch_gwas_associations(rsid: str) -> list[dict]:
    """Search GWAS Catalog REST API for associations with the given rsID."""
    associations = []

    try:
        url = f"{GWAS_API}/singleNucleotidePolymorphisms/{rsid}/associations?projection=associationBySnp"
        resp = requests.get(url, headers={"Accept": "application/json"}, timeout=60)

        if resp.status_code == 404:
            return associations

        resp.raise_for_status()
        data = resp.json()

        # First pass: collect association data and unique study URLs
        parsed = []
        study_urls = set()
        embedded = data.get("_embedded", {})
        for assoc in embedded.get("associations", []):
            # Trait
            trait = ""
            for t in assoc.get("efoTraits", []):
                trait = t.get("trait", "")
                if trait:
                    break

            # P-value
            p_value = assoc.get("pvalue", "")
            p_mantissa = assoc.get("pvalueMantissa")
            p_exponent = assoc.get("pvalueExponent")
            if p_mantissa is not None and p_exponent is not None:
                p_value = f"{p_mantissa}e{p_exponent}"

            # Effect size
            beta = assoc.get("betaNum")
            beta_unit = assoc.get("betaUnit", "")
            beta_direction = assoc.get("betaDirection", "")
            or_val = assoc.get("orPerCopyNum")
            ci = assoc.get("range", "")

            effect_size = ""
            if beta is not None:
                effect_size = f"beta={beta}"
                if beta_unit:
                    effect_size += f" {beta_unit}"
                if beta_direction:
                    effect_size += f" ({beta_direction})"
            elif or_val is not None:
                effect_size = f"OR={or_val}"
                if ci:
                    effect_size += f" {ci}"

            # Risk allele
            risk_allele = ""
            for snp in assoc.get("loci", [{}]):
                for strongest in snp.get("strongestRiskAlleles", []):
                    risk_allele = strongest.get("riskAlleleName", "")
                    if risk_allele:
                        break

            # Study link for PMID lookup
            study_link = assoc.get("_links", {}).get("study", {}).get("href", "")
            if study_link:
                study_urls.add(study_link)

            parsed.append({
                "trait": trait,
                "p_value": str(p_value),
                "effect_size": effect_size,
                "risk_allele": risk_allele,
                "_study_link": study_link,
            })

        # Second pass: fetch PMIDs from study endpoints
        pmid_map = _fetch_gwas_study_pmids(list(study_urls))

        # Build final association list with PMIDs populated
        for entry in parsed:
            study_link = entry.pop("_study_link")
            entry["pmid"] = pmid_map.get(study_link, "")
            associations.append(entry)

    except requests.RequestException as e:
        associations.append({"error": f"GWAS Catalog search failed: {str(e)}"})

    return associations


def fetch_all_clinical(rsid: str, gene_symbol: str) -> dict:
    """Fetch all clinical data for the given variant/gene."""
    result = {
        "rsid": rsid,
        "gene_symbol": gene_symbol,
        "clinvar_entries": [],
        "clinical_trials": [],
        "gwas_associations": [],
        "errors": [],
    }

    # ClinVar
    try:
        clinvar = fetch_clinvar(rsid, gene_symbol)
        # Separate errors from real entries
        for entry in clinvar:
            if "error" in entry:
                result["errors"].append(entry["error"])
            else:
                result["clinvar_entries"].append(entry)
    except Exception as e:
        result["errors"].append(f"ClinVar failed: {str(e)}")

    time.sleep(0.34)

    # ClinicalTrials.gov
    try:
        trials = fetch_clinical_trials(gene_symbol)
        for trial in trials:
            if "error" in trial:
                result["errors"].append(trial["error"])
            else:
                result["clinical_trials"].append(trial)
    except Exception as e:
        result["errors"].append(f"ClinicalTrials.gov failed: {str(e)}")

    time.sleep(0.5)

    # GWAS Catalog
    try:
        gwas = fetch_gwas_associations(rsid)
        for assoc in gwas:
            if "error" in assoc:
                result["errors"].append(assoc["error"])
            else:
                result["gwas_associations"].append(assoc)
    except Exception as e:
        result["errors"].append(f"GWAS Catalog failed: {str(e)}")

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_clinical.py <rsID> [reports_dir]", file=sys.stderr)
        sys.exit(1)

    rsid = sys.argv[1].lower().strip()
    reports_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd() / "reports"

    # Read variant info
    variant_file = reports_dir / f"{rsid}_variant.json"
    try:
        with open(variant_file) as f:
            variant_info = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"Could not read variant info: {e}"}))
        sys.exit(1)

    gene_symbol = variant_info.get("gene_symbol", "")
    if not gene_symbol:
        print(json.dumps({"error": "No gene_symbol in variant info"}))
        sys.exit(1)

    result = fetch_all_clinical(rsid, gene_symbol)

    # Write output
    output_file = reports_dir / f"{rsid}_clinical.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Clinical results written to {output_file}")


if __name__ == "__main__":
    main()
