import importlib
import json

from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from typing import Type

from pydantic import BaseModel
from ruamel.yaml import YAML
from structlog.stdlib import get_logger

from ice.evaluation.evaluation_report import latest_commit_hash
from ice.metrics.gold_standards import get_gold_standard
from ice.metrics.gold_standards import GoldStandard
from ice.metrics.gold_standards import load_papers
from ice.metrics.gold_standards import ParsedGoldStandardType
from ice.paper import Paper
from ice.recipe import recipe
from ice.recipes.meta.eval_paper_qa.types import AnswerEvalMethod
from ice.recipes.meta.eval_paper_qa.types import AnswerType_contra
from ice.recipes.meta.eval_paper_qa.types import ClassificationEvalMethod
from ice.recipes.meta.eval_paper_qa.types import PaperQaGoldStandard
from ice.recipes.meta.eval_paper_qa.types import PaperQaMethod
from ice.recipes.meta.eval_paper_qa.types import SequenceGenerationEvaluation
from ice.recipes.meta.eval_text_classification import BinaryClassificationMetrics
from ice.trace import trace
from ice.utils import map_async

from ice.datasets.qasper import get_gold_standard as get_qasper_gold_standard
from ice.metrics.qasper import token_f1_score

yaml = YAML(typ="safe")
log = get_logger()


async def eval_paper_qa_method(
    method: PaperQaMethod[AnswerType_contra],
    gold_standard_type: Type[ParsedGoldStandardType],
    gold_standard_to_trials: Callable[
        [GoldStandard[ParsedGoldStandardType]],
        Iterable[PaperQaGoldStandard[AnswerType_contra]],
    ],
    answer_eval_method: AnswerEvalMethod[AnswerType_contra],
    classification_eval_method: ClassificationEvalMethod,
    split: str,
    max_concurrency: int = 10,
):
    question_short_name = gold_standard_type.question_short_name

    papers = load_papers(split, question_short_name=question_short_name)

    log.info(
        "Evaluating method on papers",
        method=method.__class__.__name__,
        question_short_name=question_short_name,
        papers=[p.document_id for p in papers],
    )

    @trace
    async def run_and_eval_method(
        input_data: tuple[Paper, PaperQaGoldStandard]
    ) -> SequenceGenerationEvaluation[AnswerType_contra]:
        paper, qa_details = input_data
        answer = await method(paper, qa_details.question, qa_details.gold_support)
        # correct, detail = await answer_eval_method(
        #     question=qa_details.question,
        #     ground_truth=qa_details.gold_answer,
        #     prediction=answer.answer,
        # )
        metrics = await classification_eval_method(
            candidates=answer.support_candidates,
            predictions=answer.support_labels,
            ground_truth=qa_details.gold_support,
            scores=answer.support_scores,
        )
        return SequenceGenerationEvaluation(
            correct=True,#correct,
            detail="",#detail,
            metrics=metrics,
            generated_answer=answer.answer,
            gold_answer=qa_details.gold_answer,
            support=[
                text
                for lab, text in zip(answer.support_labels, answer.support_candidates)
                if lab
            ],
        )

    eval_data: list[tuple[Paper, PaperQaGoldStandard]] = []
    gold_supports: list[Sequence[str]] = []

    for paper in papers:
        gold = get_gold_standard(
            document_id=paper.document_id,
            question_short_name=question_short_name,
            model_type=gold_standard_type,
        )
        if not gold:
            log.warning(
                "Did not find gold standard",
                document_id=paper.document_id,
                question_short_name=question_short_name,
            )
            continue
        for trial in gold_standard_to_trials(gold):
            eval_data.append((paper, trial))
            gold_supports.append(trial.gold_support)

    results = await map_async(
        eval_data, run_and_eval_method, max_concurrency=max_concurrency
    )

    scores = [r.correct for r in results]
    metrics = [r.metrics for r in results]

    # only aggregate where there is gold support (somewhat arbitrary choice but more informative)
    metrics_under_support = [m for m, gs in zip(metrics, gold_supports) if gs]
    aggregated_metrics = BinaryClassificationMetrics.aggregate(metrics_under_support)

    return (
        sum(scores) / len(scores) if scores else 0,
        results,
        aggregated_metrics,
    )

async def eval_paper_qasper_qa_method(
    method: PaperQaMethod[AnswerType_contra],
    answer_eval_method: AnswerEvalMethod[AnswerType_contra],
    classification_eval_method: ClassificationEvalMethod,
    split: str,
    max_concurrency: int = 10,
    max_papers: int = 5,
    max_questions_per_paper: int = 1,
):
    papers_gs = list(get_qasper_gold_standard(split, max_papers=max_papers, max_questions_per_paper=max_questions_per_paper))

    log.info(
        "Evaluating method on papers",
        method=method.__class__.__name__,
        question_short_name="Qasper NLP QA",
        papers=list(set([p.paper.document_id for p in papers_gs])),
        total_questions=len(papers_gs),
    )

    @trace
    async def run_and_eval_method(
        qa_details: PaperQaGoldStandard
    ) -> SequenceGenerationEvaluation[AnswerType_contra]:
        answer = await method(qa_details.paper, qa_details.question, qa_details.gold_support)
        correct, detail = await answer_eval_method(
            question=qa_details.question,
            ground_truth=qa_details.gold_answer,
            prediction=answer.answer,
        )
        metrics = await classification_eval_method(
            candidates=answer.support_candidates,
            predictions=answer.support_labels,
            ground_truth=qa_details.gold_support,
            scores=answer.support_scores,
        )
        f1_score = token_f1_score(answer.answer, qa_details.gold_answer)
        return SequenceGenerationEvaluation(
            correct=correct,
            detail=detail,
            metrics=metrics,
            generated_answer=answer.answer,
            gold_answer=qa_details.gold_answer,
            support=[
                text
                for lab, text in zip(answer.support_labels, answer.support_candidates)
                if lab
            ],
            f1_score=f1_score,
        )

    eval_data: list[PaperQaGoldStandard] = papers_gs
    gold_supports: list[Sequence[str]] = [gs.gold_support for gs in papers_gs]

    results = await map_async(
        eval_data, run_and_eval_method, max_concurrency=max_concurrency
    )

    scores = [r.correct for r in results]
    metrics = [r.metrics for r in results]
    f1 = [r.f1_score for r in results]

    # only aggregate where there is gold support (somewhat arbitrary choice but more informative)
    metrics_under_support = [m for m, gs in zip(metrics, gold_supports) if gs]
    aggregated_metrics = BinaryClassificationMetrics.aggregate(metrics_under_support)

    return (
        sum(scores) / len(scores) if scores else 0,
        results,
        aggregated_metrics,
        sum(f1) / len(f1) if f1 else 0,
    )


def load_object(location: str) -> Any:
    parent_module, _, child_name = location.rpartition(".")
    module = importlib.import_module(parent_module)
    child = getattr(module, child_name)
    return child


class _PaperQaArgs(BaseModel):
    split: str
    gold_standard_type: str
    gold_standard_to_trials: str
    method: str
    answer_eval_method: str
    classification_eval_method: str

class _PaperQaArgsQasper(BaseModel):
    split: str
    method: str
    answer_eval_method: str
    classification_eval_method: str
    max_papers: int = 5
    max_questions_per_paper: int = 1


class PaperQaEvalConfig(BaseModel):
    name: str
    results_json: str | None = None
    pr_curve: str | None = None
    args: _PaperQaArgs | _PaperQaArgsQasper


def ensure_dir(path: str) -> str:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path


async def run_from_config(config: PaperQaEvalConfig) -> dict:
    score, results, agg_metrics = await eval_paper_qa_method(
        method=load_object(config.args.method),
        split=config.args.split,
        gold_standard_type=load_object(config.args.gold_standard_type),
        gold_standard_to_trials=load_object(config.args.gold_standard_to_trials),
        answer_eval_method=load_object(config.args.answer_eval_method),
        classification_eval_method=load_object(config.args.classification_eval_method),
    )
    metrics = agg_metrics.as_dict()
    results_line = dict(
        config=config.dict(),
        ice_commit=latest_commit_hash(),
        score=score,
        results=[r.as_dict() for r in results],
        metrics=metrics,
        pr_thresholds=agg_metrics.pr_thresholds(),
    )
    if config.results_json:
        with open(ensure_dir(config.results_json), "w") as r:
            r.writelines([json.dumps(results_line, indent=2, sort_keys=True)])
    if config.pr_curve:
        agg_metrics.save_pr_curve(config.pr_curve)
    return results_line

async def run_from_config_qasper(config: PaperQaEvalConfig) -> dict:
    score, results, agg_metrics, f1 = await eval_paper_qasper_qa_method(
        method=load_object(config.args.method),
        split=config.args.split,
        answer_eval_method=load_object(config.args.answer_eval_method),
        classification_eval_method=load_object(config.args.classification_eval_method),
        max_papers=config.args.max_papers,
        max_questions_per_paper=config.args.max_questions_per_paper,
    )
    metrics = agg_metrics.as_dict()
    results_line = dict(
        config=config.dict(),
        ice_commit=latest_commit_hash(),
        score=score,
        results=[r.as_dict() for r in results],
        metrics=metrics,
        pr_thresholds=agg_metrics.pr_thresholds(),
        qasper_f1_score=f1,
    )
    if config.results_json:
        with open(ensure_dir(config.results_json), "w") as r:
            r.writelines([json.dumps(results_line, indent=2, sort_keys=True)])
    if config.pr_curve:
        agg_metrics.save_pr_curve(config.pr_curve)
    return results_line


async def eval_from_config(config_path: str = "/code/ice/recipes/meta/configs/qasper.yaml"):
    configs = yaml.load(Path(config_path))

    parsed = [PaperQaEvalConfig.parse_obj(configs[0])]
    for prev_idx, config in enumerate(configs[1:]):
        prev_args = parsed[prev_idx].args.dict()
        config["args"] = prev_args | config["args"]
        parsed.append(PaperQaEvalConfig.parse_obj(config))

    return await map_async(parsed, run_from_config, max_concurrency=1)

async def eval_from_config_qasper(config_path: str = "/code/ice/recipes/meta/configs/qasper.yaml"):
    configs = yaml.load(Path(config_path))

    parsed = [PaperQaEvalConfig.parse_obj(configs[0])]
    for prev_idx, config in enumerate(configs[1:]):
        prev_args = parsed[prev_idx].args.dict()
        config["args"] = prev_args | config["args"]
        parsed.append(PaperQaEvalConfig.parse_obj(config))

    return await map_async(parsed, run_from_config_qasper, max_concurrency=1)

recipe.main(eval_from_config_qasper)