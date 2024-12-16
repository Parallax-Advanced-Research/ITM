class SearchActionRuleSet:
    """
    Ruleset specifically for analyzing SEARCH actions.
    Ensures that the SEARCH action evaluates all casualties instead of individual ones.
    """

    BASE_SCORE = 0.7  # Baseline competence score for a SEARCH action.

    def assess_search_action(self, casualties, supplies):
        """
        Assess the appropriateness of the SEARCH action considering all casualties.
        """
        search_scores = {}

        # Iterate over each casualty to check for missing information or unseen status.
        for casualty in casualties:
            score = self.BASE_SCORE

            # Increase score if the casualty is unseen or missing critical information.
            if casualty.unseen:
                score += 0.2
            if any(
                getattr(casualty.vitals, attr) is None for attr in vars(casualty.vitals)
            ):
                score += 0.1
            if not casualty.injuries:
                score += 0.1

            # Cap the score at 1.0
            search_scores[casualty.id] = min(score, 1.0)

        # Calculate an overall assessment score by averaging individual casualty scores.
        overall_score = (
            sum(search_scores.values()) / len(casualties)
            if casualties
            else self.BASE_SCORE
        )

        # Return a single overall decision for the SEARCH action
        return min(overall_score, 1.0)