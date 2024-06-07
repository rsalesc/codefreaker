import os
import pathlib
import subprocess

from codefreaker import metadata
from . import console
from .config import get_config
from . import annotations


def get_editor():
    return get_config().editor or os.environ.get("EDITOR", None)


def open_editor(path: pathlib.Path):
    if get_editor() is None:
        raise Exception("No editor found. Please set the EDITOR environment variable.")
    subprocess.run([get_editor(), str(path)])


def main(problem: str, language: annotations.LanguageWithDefault = None):
    lang = get_config().get_language(language)
    if lang is None:
        console.print(
            f"[error]Language {language or get_config().defaultLanguage} not found in config. Please check your configuration.[/error]"
        )
        return

    problem = metadata.find_problem_by_anything(problem)
    if not problem:
        console.print(f"[error]Problem with identifier {problem} not found.[/error]")
        return

    filename = lang.get_file(problem.code)
    open_editor(filename)