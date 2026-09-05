"""
Unit tests for evidence coverage and facet clustering.
"""

import pytest
from evidence.models import EvidencePassage
from search.query import QueryFacet
from evidence.coverage import cluster_evidence_by_facets, EvidenceCoverageReport


def test_cluster_evidence_multi_domain_coverage():
    facets = [
        QueryFacet(
            facet_id="instruments",
            title="Scientific Instruments",
            description="Overview of NIRCam, MIRI, and NIRSpec",
            keywords=["nircam", "miri", "nirspec", "instrument", "spectrograph"],
        ),
        QueryFacet(
            facet_id="discoveries",
            title="Major Discoveries",
            description="Galaxies and exoplanet observations",
            keywords=["galaxy", "exoplanet", "atmosphere", "discovery", "redshift"],
        ),
        QueryFacet(
            facet_id="launch_orbit",
            title="Launch & Orbit",
            description="Ariane 5 launch and L2 halo orbit",
            keywords=["launch", "ariane", "orbit", "lagrange", "l2"],
        ),
    ]

    passages = [
        EvidencePassage(
            text="JWST carries four primary instruments including NIRCam and the Mid-Infrared Instrument MIRI.",
            source_url="https://nasa.gov/jwst/instruments",
            source_domain="nasa.gov",
            source_title="NASA JWST",
        ),
        EvidencePassage(
            text="The NIRSpec spectrograph allows simultaneous observation of up to 100 astronomical targets.",
            source_url="https://esa.int/jwst/nirspec",
            source_domain="esa.int",
            source_title="ESA NIRSpec",
        ),
        EvidencePassage(
            text="JWST discovered candidate early galaxies formed within 350 million years of the Big Bang.",
            source_url="https://nature.com/articles/jwst-galaxies",
            source_domain="nature.com",
            source_title="Nature Astronomy",
        ),
    ]

    report = cluster_evidence_by_facets(passages, facets)

    assert isinstance(report, EvidenceCoverageReport)
    assert report.total_facets == 3

    # Instruments facet has 2 independent domains (nasa.gov and esa.int) -> fully covered
    inst_cluster = next(c for c in report.clusters if c.facet_id == "instruments")
    assert inst_cluster.status == "fully_covered"
    assert len(inst_cluster.corroborating_domains) == 2

    # Discoveries facet has 1 domain (nature.com) -> partially covered
    disc_cluster = next(c for c in report.clusters if c.facet_id == "discoveries")
    assert disc_cluster.status == "partially_covered"

    # Launch & Orbit had no matching passage -> uncovered
    orbit_cluster = next(c for c in report.clusters if c.facet_id == "launch_orbit")
    assert orbit_cluster.status == "uncovered"
    assert any("Launch & Orbit" in req for req in report.unverified_requirements)

    assert report.covered_facets == 2
    assert report.coverage_ratio == pytest.approx(2 / 3, 0.01)

