from src.modules.evaluation import cli
from src.modules.evaluation.domain.models import DEFAULT_LEGAL_METRICS, EvaluationMetric


def test_run_legal_arguments() -> None:
    args = cli.build_parser().parse_args(
        [
            "run-legal",
            "--dataset",
            "d.json",
            "--metrics",
            "legal_citation_exactness",
            "--max-samples",
            "3",
        ]
    )
    assert args.command == "run-legal"
    assert args.dataset == "d.json"
    assert cli._parse_metrics(args.metrics, cli.DEFAULT_LEGAL_METRICS) == [
        EvaluationMetric.LEGAL_CITATION_EXACTNESS
    ]
    assert args.max_samples == 3


def test_legal_metrics_default() -> None:
    assert cli._parse_metrics(None, DEFAULT_LEGAL_METRICS) == DEFAULT_LEGAL_METRICS


def test_rag_command_still_parses() -> None:
    args = cli.build_parser().parse_args(["run", "--dataset", "d.json", "--user-id", "u"])
    assert args.command == "run"
