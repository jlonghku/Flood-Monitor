"""Image water-depth estimation interface with auditable outputs."""

from __future__ import annotations

from pathlib import Path

from ..models import DepthObservation, Evidence


class ImageDepthExtractor:
    """Estimate water-depth ranges from photo metadata or analyst labels.

    This deterministic implementation accepts optional labels now and provides a
    stable interface for later vision-model integration.
    """

    REFERENCE_DEPTHS = {
        "ankle": (0.05, 0.15),
        "curb": (0.08, 0.18),
        "knee": (0.35, 0.55),
        "tire": (0.25, 0.45),
        "wheel": (0.30, 0.55),
        "door": (0.55, 0.90),
        "barrier": (0.40, 0.80),
        "storefront_step": (0.10, 0.30),
    }

    def estimate(
        self,
        image_path: str | Path,
        *,
        reference_object: str | None = None,
        location: tuple[float, float] | None = None,
        time: str | None = None,
        evidence: Evidence | None = None,
    ) -> DepthObservation:
        label = (reference_object or "unknown").lower()
        depth_range = self.REFERENCE_DEPTHS.get(label)
        depth_m = round(sum(depth_range) / 2, 3) if depth_range else None
        evidence_ids = [evidence.evidence_id] if evidence and evidence.evidence_id else []
        return DepthObservation(
            location=location or (evidence.location if evidence else None),
            time=time or (evidence.observed_time if evidence else None),
            depth_m=depth_m,
            depth_range_m=depth_range,
            method="image_reference_object",
            reference_object=reference_object,
            location_name=evidence.location_name if evidence else None,
            evidence_ids=evidence_ids,
            confidence=0.75 if depth_range else 0.35,
        )
