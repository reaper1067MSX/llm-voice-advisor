"""Backward compatibility shim for abi_coach.metatuning -> abi_coach.slices.metatuning.engine."""

from abi_coach.slices.metatuning.engine import MetaTuningEngine, MetaTuningResult

__all__ = ["MetaTuningEngine", "MetaTuningResult"]
