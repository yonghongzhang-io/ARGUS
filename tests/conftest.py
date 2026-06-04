import pytest


@pytest.fixture
def supported_paper():
    def factory(paper_id: str = "supported") -> dict:
        return {
            "id": paper_id,
            "title": "Supported DID identification pilot fixture",
            "metadata": {
                "fixture_type": "synthetic parsed-paper fixture",
                "domain": "environmental policy DID",
            },
            "sections": {
                "parallel trends": (
                    "The event-study pre-trend coefficients are near zero and support "
                    "parallel trends; placebo pre-period estimates are also null."
                ),
                "no anticipation": (
                    "No anticipation is supported by the timeline of announcement and "
                    "implementation; event-study leads are null."
                ),
                "treatment timing": (
                    "Staggered adoption is handled with Callaway-Sant'Anna, "
                    "Sun-Abraham, and a Goodman-Bacon decomposition for heterogeneous effects."
                ),
                "sutva": (
                    "SUTVA and interference are assessed with spillover robustness, "
                    "buffer-zone checks, and leakage sensitivity."
                ),
                "control group": (
                    "A balance table shows matched controls; the donor pool is justified "
                    "with matching and synthetic control checks."
                ),
                "specification": (
                    "The specification robustness table varies fixed effects, controls, "
                    "and functional form choices."
                ),
                "inference": (
                    "Standard errors are clustered by province, with wild-cluster "
                    "bootstrap robustness for serial correlation."
                ),
                "sample period": (
                    "Sample period and time-window sensitivity checks vary start period, "
                    "end period, and unbalanced panel handling."
                ),
                "concurrent policies": (
                    "Concurrent policies are enumerated; policy controls and placebo "
                    "periods isolate the carbon trading pilot."
                ),
                "robustness placebo": (
                    "Placebo-in-time, placebo-in-space, falsification tests, permutation "
                    "checks, and randomization inference are reported."
                ),
                "data measurement": (
                    "The data source documents definition stability, missingness handling, "
                    "and measurement consistency over time."
                ),
            },
            "figures": [
                {
                    "id": "fig_event_study",
                    "caption": "Event-study plot with null pre-trend coefficients.",
                }
            ],
        }

    return factory
