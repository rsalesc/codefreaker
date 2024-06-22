import pathlib

from . import annotations
from .clone import create_problem_structure
from .config import get_config
from .console import console
from .schema import Batch, Problem


def main(
    name: str,
    lang: annotations.Language,
    timelimit: annotations.Timelimit = 1000,
    memorylimit: annotations.Memorylimit = 256,
    multitest: annotations.Multitest = False,
):
    if get_config().get_language(lang) is None:
        console.print(
            f'[error]Language {lang or get_config().defaultLanguage} not found in config. Please check your configuration.[/error]'
        )
        return

    problem = Problem(
        name=name,
        timeLimit=timelimit,
        memoryLimit=memorylimit,
        testType='multiNumber' if multitest else 'single',
        batch=Batch.create(),
    )
    create_problem_structure(
        pathlib.Path(),
        problem,
        get_config().get_language(lang),
        status=None,
        verbose=True,
    )
