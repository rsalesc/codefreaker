import dataclasses
import pathlib
import shutil
import tempfile
import typing
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

import typer

from robox import console
from robox.box.schema import Package, Testcase
from robox.box.statements.latex import Latex
from robox.box.statements.latex_jinja import (
    render_latex_template,
    render_latex_template_blocks,
)
from robox.box.statements.schema import (
    JinjaTeX,
    PipelineStep,
    Statement,
    StatementType,
    TexToPDF,
    roboxToTeX,
)


@dataclasses.dataclass
class StatementCodeLanguage:
    name: str
    command: str


@dataclasses.dataclass
class StatementBuilderContext:
    languages: List[StatementCodeLanguage]
    params: PipelineStep
    assets: List[Tuple[pathlib.Path, pathlib.Path]] = dataclasses.field(
        default_factory=list
    )

    def build_jinja_kwargs(self) -> Dict[str, Any]:
        return {'languages': self.languages}


@dataclasses.dataclass
class StatementBuilderProblem:
    package: Package
    statement: Statement
    samples: List[Testcase] = dataclasses.field(default_factory=list)

    def build_jinja_kwargs(self) -> Dict[str, Any]:
        return {
            'package': self.package,
            'statement': self.statement,
            'samples': self.samples,
            'vars': self.package.vars,
            'title': self.statement.title or self.package.name,
        }


def prepare_assets(
    assets: List[Tuple[pathlib.Path, pathlib.Path]],
    dest_dir: pathlib.Path,
):
    dest_dir.mkdir(parents=True, exist_ok=True)

    for asset_in, asset_out in assets:
        if not asset_in.is_file():
            console.console.print(
                f'[error]Asset [item]{asset_in}[/item] does not exist in your package.[/error]'
            )
            raise typer.Exit(1)

        # dest_path = dest_dir / asset.resolve().relative_to(statement_dir)
        dest_path = dest_dir / asset_out
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(asset_in), str(dest_path))


def render_jinja(
    assets: List[Tuple[pathlib.Path, pathlib.Path]], content: bytes, **kwargs
) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        temp_dir = pathlib.Path(td)
        prepare_assets(assets, temp_dir)

        temp_file = '__input__.tex'
        temp_path = temp_dir / temp_file
        temp_path.write_bytes(content)

        result: str = render_latex_template(
            str(temp_dir),
            temp_file,
            kwargs,
        )
        return result.encode()


def render_jinja_blocks(
    assets: List[Tuple[pathlib.Path, pathlib.Path]], content: bytes, **kwargs
) -> Dict[str, str]:
    with tempfile.TemporaryDirectory() as td:
        temp_dir = pathlib.Path(td)
        prepare_assets(assets, temp_dir)

        temp_file = '__input__.tex'
        temp_path = temp_dir / temp_file
        temp_path.write_bytes(content)

        result: Dict[str, str] = render_latex_template_blocks(
            str(temp_dir),
            temp_file,
            kwargs,
        )
        return result


class StatementBuilder(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def default_params(self) -> PipelineStep:
        pass

    @abstractmethod
    def input_type(self) -> StatementType:
        pass

    @abstractmethod
    def output_type(self) -> StatementType:
        pass

    def inject_assets(
        self, params: PipelineStep
    ) -> List[Tuple[pathlib.Path, pathlib.Path]]:
        return []

    @abstractmethod
    def build(
        self,
        input: bytes,
        context: StatementBuilderContext,
        problem: StatementBuilderProblem,
        verbose: bool = False,
    ) -> bytes:
        pass


class JinjaTeXBuilder(StatementBuilder):
    def name(self) -> str:
        return 'jinja-tex'

    def default_params(self) -> PipelineStep:
        return JinjaTeX(type='jinja-tex')

    def input_type(self) -> StatementType:
        return StatementType.JinjaTeX

    def output_type(self) -> StatementType:
        return StatementType.TeX

    def build(
        self,
        input: bytes,
        context: StatementBuilderContext,
        problem: StatementBuilderProblem,
        verbose: bool = False,
    ) -> bytes:
        return render_jinja(
            context.assets,
            input,
            **context.build_jinja_kwargs(),
            problem=problem.build_jinja_kwargs(),
        )


class roboxTeXBuilder(StatementBuilder):
    def name(self) -> str:
        return 'rbx-tex'

    def default_params(self) -> PipelineStep:
        return roboxToTeX(type='rbx-tex')

    def input_type(self) -> StatementType:
        return StatementType.roboxTeX

    def output_type(self) -> StatementType:
        return StatementType.TeX

    def inject_assets(
        self, params: PipelineStep
    ) -> List[Tuple[pathlib.Path, pathlib.Path]]:
        params = typing.cast(roboxToTeX, params)
        if not params.template:
            return []
        return [(params.template, params.template)]

    def build(
        self,
        input: bytes,
        context: StatementBuilderContext,
        problem: StatementBuilderProblem,
        verbose: bool = False,
    ) -> bytes:
        params = typing.cast(roboxToTeX, context.params)
        assert params.template is not None
        blocks = render_jinja_blocks(
            context.assets, input, **problem.build_jinja_kwargs()
        )

        input_str = f'%- extends "{params.template}"'
        problems = [
            {
                'blocks': blocks,
                **problem.build_jinja_kwargs(),
            }
        ]
        return render_jinja(
            context.assets,
            input_str.encode(),
            **context.build_jinja_kwargs(),
            problems=problems,
        )


class TeX2PDFBuilder(StatementBuilder):
    def name(self) -> str:
        return 'tex2pdf'

    def default_params(self) -> PipelineStep:
        return TexToPDF(type='tex2pdf')

    def input_type(self) -> StatementType:
        return StatementType.TeX

    def output_type(self) -> StatementType:
        return StatementType.PDF

    def build(
        self,
        input: bytes,
        context: StatementBuilderContext,
        problem: StatementBuilderProblem,
        verbose: bool = False,
    ) -> bytes:
        latex = Latex(input.decode())
        with tempfile.TemporaryDirectory() as td:
            temp_dir = pathlib.Path(td)
            prepare_assets(context.assets, temp_dir)
            latex_result = latex.build_pdf(temp_dir)
        pdf = latex_result.pdf
        if pdf is None:
            console.console.print(f'{latex_result.result.stdout.decode()}')
            console.console.print('[error]PdfLaTeX compilation failed.[/error]')
            raise typer.Exit(1)

        if verbose:
            console.console.print(f'{latex_result.result.stdout.decode()}')

        return pdf


BUILDER_LIST = [TeX2PDFBuilder(), JinjaTeXBuilder(), roboxTeXBuilder()]
