import typer

from codefreaker import checker

from . import annotations
from . import clone as clone_pkg
from . import config
from . import testcase
from . import create as create_pkg
from . import edit as edit_pkg
from . import test as test_pkg
from . import submit as submit_pkg

app = typer.Typer(no_args_is_help=True, cls=annotations.AliasGroup)
app.add_typer(
    config.app,
    name="config, cfg",
    cls=annotations.AliasGroup,
    help="Manage the configuration of the tool.",
)
app.add_typer(
    testcase.app,
    name="testcase, tc",
    cls=annotations.AliasGroup,
    help="Commands to manage the testcases of a problem.",
)
app.add_typer(
    checker.app,
    name="checker, check",
    cls=annotations.AliasGroup,
    help="Commands to manage the checker of a problem.",
)


@app.command("clone, c")
def clone(lang: annotations.Language):
    """
    Clones by waiting for a set of problems to be sent through Competitive Companion.
    """
    clone_pkg.main(lang=lang)


@app.command("new, n")
def new(
    name: str,
    language: annotations.Language,
    timelimit: annotations.Timelimit = 1000,
    memorylimit: annotations.Memorylimit = 256,
    multitest: annotations.Multitest = False,
):
    """
    Create a new problem from scratch.
    """
    create_pkg.main(name, language, timelimit, memorylimit, multitest)


@app.command("edit, e")
def edit(
    problem: annotations.Problem, language: annotations.LanguageWithDefault = None
):
    """
    Edit the code of a problem using the provided language.
    """
    edit_pkg.main(problem, language)


@app.command("test, t")
def test(
    problem: annotations.Problem,
    language: annotations.LanguageWithDefault = None,
    keep_sandbox: bool = False,
    index: annotations.TestcaseIndex = None,
):
    """
    Test a problem using the provided language.
    """
    test_pkg.main(problem, language, keep_sandbox=keep_sandbox, index=index)


@app.command("submit, s")
def submit(
    problem: annotations.Problem,
    language: annotations.LanguageWithDefault = None,
    keep_sandbox: bool = False,
):
    """
    Submit a problem using the provided language.
    """
    submit_pkg.main(problem, language, keep_sandbox=keep_sandbox)


@app.callback()
def callback():
    pass
