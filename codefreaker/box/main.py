import shutil

import typer

from codefreaker import annotations, console, utils
from codefreaker.box.generators import (
    generate_outputs_for_testcases,
    generate_testcases,
)
from codefreaker.box.solutions import print_run_report, run_solutions
from codefreaker.box.validators import validate_testcases

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)


@app.command('build, b')
def build(verify: bool = True):
    with utils.StatusProgress(
        'Building testcases...',
        'Built [item]{processed}[/item] testcases...',
        keep=True,
    ) as s:
        generate_testcases(s)

    with utils.StatusProgress(
        'Building outputs for testcases...',
        'Built [item]{processed}[/item] outputs...',
        keep=True,
    ) as s:
        generate_outputs_for_testcases(s)

    if verify:
        with utils.StatusProgress(
            'Validating testcases...',
            'Validated [item]{processed}[/item] testcases...',
            keep=True,
        ) as s:
            validate_testcases(s)

    console.console.print('[success]Problem built successfully![/success]')


@app.command('run')
def run():
    build()

    with utils.StatusProgress('Running solutions...') as s:
        evals_per_solution = run_solutions(s)

    console.console.print()
    console.console.rule('[status]Run report[/status]', style='status')
    print_run_report(evals_per_solution, console.console)


@app.command('clear')
def clear():
    console.console.print('Cleaning cache and build directories...')
    shutil.rmtree('.box', ignore_errors=True)
    shutil.rmtree('build', ignore_errors=True)


@app.callback()
def callback():
    pass
