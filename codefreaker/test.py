import atexit
import dataclasses
import pathlib
from typing import List, Optional
from rich.columns import Columns
from rich.panel import Panel
from rich.text import Text

from codefreaker import annotations, metadata, testcase_rendering
from codefreaker import config
from codefreaker.config import Language, get_config
from codefreaker.console import console
from codefreaker.grading import steps
from codefreaker.grading.judge.sandboxes import stupid_sandbox
from codefreaker.schema import DumpedProblem


def get_testcase_index(path: pathlib.Path) -> int:
    return int(path.stem.split(".")[-1])


def get_testcases_io(
    problem: DumpedProblem, root: pathlib.Path = pathlib.Path(".")
) -> List[steps.TestcaseIO]:
    testcases_per_index = {}
    for input_file in root.glob(f"{problem.code}.*.in"):
        try:
            index = get_testcase_index(input_file)
        except ValueError:
            continue
        testcases_per_index[index] = steps.TestcaseIO(index=index, input=input_file)

    for output_file in root.glob(f"{problem.code}.*.out"):
        index = get_testcase_index(output_file)
        try:
            index = get_testcase_index(output_file)
        except ValueError:
            continue
        if index in testcases_per_index:
            testcases_per_index[index] = dataclasses.replace(
                testcases_per_index[index], output=output_file
            )
            continue
        testcases_per_index[index] = steps.TestcaseIO(index=index, output=output_file)

    return sorted(testcases_per_index.values(), key=lambda x: x.index)


def _pretty_print_output_on_panel(file: pathlib.Path, title: str) -> Panel:
    return Panel(
        testcase_rendering.render_from_file(file),
        title=title,
        expand=False,
    )


def _pretty_print_side_by_side(result: steps.TestcaseEvaluation):
    return Columns(
        [
            _pretty_print_output_on_panel(result.testcase.output, "Expected"),
            _pretty_print_output_on_panel(result.log.stdout_absolute_path, "Actual"),
        ],
        equal=True,
        expand=False,
    )


def _get_outcome_style(outcome: steps.Outcome) -> str:
    if outcome == steps.Outcome.ACCEPTED:
        return "success"
    if outcome == steps.Outcome.JUDGE_FAILED or outcome == steps.Outcome.INTERNAL_ERROR:
        return "warning"
    return "error"


def _pretty_print_outcome_panel(
    problem: DumpedProblem, result: steps.TestcaseEvaluation
) -> Panel:
    is_tle = result.outcome == steps.Outcome.TIME_LIMIT_EXCEEDED or (
        problem.timeLimit and result.log.time * 1000 > problem.timeLimit
    )

    text = Text()
    text.append("Outcome: ")
    text.append(
        result.outcome.value,
        style=_get_outcome_style(result.outcome),
    )
    text.append(" " * 4)
    text.append("Time: ")
    text.append(f"{result.log.time:.2f}s", style="error" if is_tle else "item")
    text.append("\n")
    if result.testcase.input:
        text.append(f"Input path: {result.testcase.input.absolute()}")
        text.append("\n")
    if result.testcase.output:
        text.append(f"Expected path: {result.testcase.output.absolute()}")
        text.append("\n")
    text.append(f"Answer path: {result.log.stdout_absolute_path}")
    return Panel(
        text,
        title=f"[bold]Testcase [item]#{result.testcase.index}[/item]",
        expand=False,
    )


def _pretty_print_evaluation_result(
    problem: DumpedProblem, result: steps.TestcaseEvaluation
):
    console.print(_pretty_print_outcome_panel(problem, result))
    if result.outcome != steps.Outcome.ACCEPTED:
        console.print(_pretty_print_side_by_side(result))
        if result.message:
            console.print(f"[error]Checker message:[/error] {result.message.strip()}")
    console.print()


def pretty_print_summary(
    problem: DumpedProblem,
    lang: Language,
    results: List[steps.TestcaseEvaluation],
    root: pathlib.Path = pathlib.Path("."),
):
    submission_file = root / lang.get_submit_file(problem.code)
    passed = sum(1 for result in results if result.outcome == steps.Outcome.ACCEPTED)
    total = len(results)
    console.print(f"Summary for problem [item]{problem.pretty_name()}[/item]:")

    # Test summary.
    text = Text()
    text.append("Passed tests: ")
    text.append(f"{passed}/{total}", style="success" if passed == total else "error")
    console.print(text)

    console.print(f"Submission file: {submission_file.absolute()}")


def pretty_print_evaluation_results(
    problem: DumpedProblem, results: List[steps.TestcaseEvaluation]
):
    for result in results:
        _pretty_print_evaluation_result(problem, result)


def main(
    problem: annotations.Problem,
    language: annotations.LanguageWithDefault = None,
    keep_sandbox: bool = False,
    index: Optional[annotations.TestcaseIndex] = None,
):
    dumped_problem = metadata.find_problem_by_anything(problem)
    if not dumped_problem:
        console.print(
            f"[error]Problem with identifier [item]{problem}[/item] not found.[/error]"
        )
        return

    lang = get_config().get_language(language)
    if not lang:
        console.print(
            f"[error]Language {language or get_config().defaultLanguage} not found in config. Please check your configuration.[/error]"
        )
        return

    testcases = get_testcases_io(dumped_problem)

    if index is not None:
        testcases = [tc for tc in testcases if tc.index == index]

    if not testcases:
        console.print(
            f"[error]No testcases found for the problem [item]{dumped_problem.pretty_name()}[/item].[/error]"
        )
        return

    box = stupid_sandbox.StupidSandbox()
    atexit.register(lambda: box.cleanup(delete=not keep_sandbox))

    with console.status(
        f"Preprocessing code for problem [item]{dumped_problem.pretty_name()}[/item] in language [item]{language or get_config().defaultLanguage}[/item]..."
    ):
        if not steps.preprocess(dumped_problem, lang, box):
            console.print(
                f"[error]Failed to preprocess problem [item]{dumped_problem.pretty_name()}[/item].[/error]"
            )
            return

    persist_root = config.get_empty_app_persist_path()

    testcase_logs = steps.run(dumped_problem, lang, box, testcases, persist_root)

    if not testcase_logs:
        console.print(
            f"[error]Failed to run testcases for problem [item]{dumped_problem.pretty_name()}[/item]. Sandbox probably crashed.[/error]"
        )
        return

    with console.status(
        f"Evaluating testcases for problem [item]{dumped_problem.pretty_name()}[/item]..."
    ):
        results = steps.evaluate(
            dumped_problem, box, testcases, testcase_logs, persist_root
        )
    if not results:
        console.print(
            f"[error]Failed to evaluate testcases for problem [item]{dumped_problem.pretty_name()}[/item].[/error]"
        )
        return
    pretty_print_evaluation_results(dumped_problem, results)
    pretty_print_summary(dumped_problem, lang, results)
