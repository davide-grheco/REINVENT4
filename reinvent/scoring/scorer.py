"""Prototype for the new heart of the scoring component

A scoring function is composed of components.  An aggregation function
combines components into the final scoring function.  Each component has a
weight and cna be transformed from a function.  Components report a primary
score for training and possibly secondary scores for reporting only.
Components also report uncertainties and failure of the actual scorer.
A scorer can be call through API, REST API or subprocess.
"""

from __future__ import annotations

__all__ = ["Scorer"]
from collections import defaultdict
from typing import List, Optional
import logging

import numpy as np
import pathos as pa
from pathos.pools import ParallelPool

from . import aggregators
from .config import get_components
from .compute_scores import compute_transform
from .results import ScoreResults


logger = logging.getLogger(__name__)


class Scorer:
    """The main handler for a request to a scoring function"""

    def __init__(self, config: dict):
        """Set up the scorer

        :param config: scoring configuration
        """
        self.aggregate = getattr(aggregators, config["type"])
        self.parallel = config.get("parallel", False)

        self.components = get_components(config["component"])

    def compute_results(
        self,
        smilies: List[str],
        mask: np.ndarray,
        fragments: Optional[List[str]] = None,
    ) -> ScoreResults:
        """Compute the score from a list of SMILES

        :param smilies: list of SMILES
        :param mask: mask to filter invalid and duplicate SMILES
        :param fragments: optional fragment SMILES
        :return: all results for the SMILES
        """
        # needs to be list for duplicate comps, name change for clearity
        completed_components = []
        filters_to_report = []
        # ntasks = len(self.components.scorers)

        # if self.parallel and ntasks > 1:
        if False:
            cpu_count = pa.helpers.cpu_count()
            nodes = min(cpu_count, ntasks)
            pool = ParallelPool(nodes=nodes)

            pool_params = tuple(
                (smilies, params[0], self.caches[component_type])
                for component_type, params in self.components.scorers.items()
            )

            pool_results = pool.map(compute_component_scores, *zip(*pool_params))

            # TODO: implement
        else:
            # Compute the filter mask to prevent computation of scores in the
            # second loop over the non-filter components below
            for component in self.components.filters:
                transform_result = compute_transform(
                    component.component_type, component.params, smilies, component.cache, mask
                )

                for scores in transform_result.transformed_scores:
                    mask = np.logical_and(scores, mask)
                # NOTE: filters are NOT also used as components as in REINVENT3

                filters_to_report.append(transform_result)

            for component in self.components.scorers:
                if fragments and component.component_type.startswith("fragment"):
                    pass_smilies = fragments
                else:
                    pass_smilies = smilies

                transform_result = compute_transform(
                    component.component_type, component.params, pass_smilies, component.cache, mask
                )

                completed_components.append(transform_result)

        scores_and_weights = []

        for component in completed_components:
            for tscores, weight in zip(component.transformed_scores, component.weight):
                scores_and_weights.append((tscores, weight))

        total_scores = self.aggregate(scores_and_weights)

        penalties = np.full(len(smilies), 1.0, dtype=float)

        for component in self.components.penalties:
            transform_result = compute_transform(
                component.component_type, component.params, smilies, component.cache, mask
            )

            for scores in transform_result.transformed_scores:
                penalties *= scores

            completed_components.append(transform_result)

        for filter_to_report in filters_to_report:
            completed_components.append(filter_to_report)

        return ScoreResults(smilies, total_scores * penalties, completed_components)

    __call__ = compute_results
