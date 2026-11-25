from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class SignalBlock:
    """Channel-major samples with a monotonic source sample index."""

    start_sample: int
    sample_rate: int
    samples: np.ndarray
    labels: np.ndarray