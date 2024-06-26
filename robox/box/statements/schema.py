import pathlib
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field

from robox.autoenum import AutoEnum, alias


### Pipeline nodes.
class roboxToTeX(BaseModel):
    type: Literal['rbx-tex']

    # Template that should be used to render the rbx-tex blocks.
    template: pathlib.Path = pathlib.Path('template.rbx.tex')


class TexToPDF(BaseModel):
    type: Literal['tex2pdf']


class JinjaTeX(BaseModel):
    type: Literal['jinja-tex']


PipelineStep = TexToPDF | JinjaTeX | roboxToTeX


### Statement types
class StatementType(AutoEnum):
    roboxTeX = alias('robox-tex', 'rbx-tex', 'rbx')  # type: ignore
    TeX = alias('tex')
    JinjaTeX = alias('jinja-tex')
    PDF = alias('pdf')

    def get_file_suffix(self) -> str:
        match self:
            case StatementType.TeX:
                return '.tex'
            case StatementType.roboxTeX:
                return '.rbx.tex'
            case StatementType.JinjaTeX:
                return '.jinja.tex'
            case StatementType.PDF:
                return '.pdf'
        raise ValueError(f'Unknown statement type: {self}')


class Statement(BaseModel):
    model_config = ConfigDict(extra='forbid')

    # Name of the problem, as it appears in the statement.
    title: str

    # Path relative to the package directory where the input statement is located.
    path: pathlib.Path

    # Type of the input statement.
    type: StatementType

    # Forces a certain sequence of conversion steps to happen during the statement
    # generation process.
    pipeline: List[PipelineStep] = Field(default_factory=list, discriminator='type')

    # Assets relative to the package directory that should be included while building
    # the statement. Files will be included in the same folder as the statement file, preserving
    # their relativeness.
    assets: List[pathlib.Path] = []

    # Language this is statement is written in.
    language: str = 'en'
