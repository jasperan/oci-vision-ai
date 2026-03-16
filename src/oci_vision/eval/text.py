from __future__ import annotations

from oci_vision.core.models import TextDetectionResult


def normalized_edit_distance(a: str, b: str) -> float:
    if a == b:
        return 0.0
    if not a and not b:
        return 0.0

    rows = len(a) + 1
    cols = len(b) + 1
    dp = [[0] * cols for _ in range(rows)]

    for i in range(rows):
        dp[i][0] = i
    for j in range(cols):
        dp[0][j] = j

    for i in range(1, rows):
        for j in range(1, cols):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )

    return dp[-1][-1] / max(len(a), len(b), 1)


def text_similarity(prediction: TextDetectionResult, truth: TextDetectionResult) -> float:
    return 1.0 - normalized_edit_distance(prediction.full_text, truth.full_text)


def line_accuracy(prediction: TextDetectionResult, truth: TextDetectionResult) -> float:
    truth_lines = [line.text for line in truth.lines]
    predicted_lines = [line.text for line in prediction.lines]
    if not truth_lines:
        return 1.0 if not predicted_lines else 0.0

    matches = sum(1 for pred, actual in zip(predicted_lines, truth_lines) if pred == actual)
    return matches / len(truth_lines)
