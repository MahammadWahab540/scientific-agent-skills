from __future__ import annotations


class BayesianUpdater:
    """Update a hypothesis probability with an explicit likelihood ratio."""

    def update(self, prior_probability: float, likelihood_ratio: float) -> float:
        if not 0 < prior_probability < 1:
            raise ValueError("prior_probability must be between 0 and 1, exclusive")
        if likelihood_ratio <= 0:
            raise ValueError("likelihood_ratio must be greater than 0")
        prior_odds = prior_probability / (1.0 - prior_probability)
        posterior_odds = prior_odds * likelihood_ratio
        return posterior_odds / (1.0 + posterior_odds)
