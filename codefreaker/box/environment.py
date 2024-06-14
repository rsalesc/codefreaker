import functools
import pathlib
from typing import List, Optional, Type, TypeVar
from pydantic import BaseModel
import typer

from codefreaker import config, console, utils

T = TypeVar("T", bound=BaseModel)


class FileMapping(BaseModel):
    # Path where to copy the stdin file to before running the program,
    # relative to the sandbox root.
    input: Optional[str] = "stdin"

    # Path where to output the stdout file after running the program,
    # relative to the sandbox root.
    output: Optional[str] = "stdout"

    # Path where to copy the compilable file to before compiling the program,
    # relative to the sandbox root.
    compilable: Optional[str] = "compilable"

    # Path to where to output the executable file after compiling the program,
    # relative to the sandbox root.
    executable: Optional[str] = "executable"


class EnvironmentSandbox(BaseModel):
    # Max. number of process to allow to run concurrently for the program.
    maxProcesses: Optional[int] = 1

    # Time limit in milliseconds to allow the program to run.
    timeLimit: Optional[int] = 1000

    # Wall time limit in milliseconds to allow the program to run.
    wallTimeLimit: Optional[int] = 2000

    # Memory limit in MiB.
    memoryLimit: Optional[int] = 256

    # Stack limit in MiB.
    stackLimit: Optional[int] = None

    # Whether to preserve env. variables coming from the host.
    preserveEnv: Optional[bool] = False

    # Directories in the host that should be read-only exposed to the sandbox.
    mirrorDirs: Optional[List[str]] = []


class CompilationConfig(BaseModel):
    # Commands to compile the program.
    commands: Optional[List[str]] = []

    # Sandbox configuration to use when compiling for this language.
    sandbox: Optional[EnvironmentSandbox] = None


class ExecutionConfig(BaseModel):
    # Command to run the program.
    command: Optional[str] = None

    # Sandbox configuration to use when executing for this language.
    sandbox: Optional[EnvironmentSandbox] = None


class EnvironmentLanguage(BaseModel):
    # Identifier of this language within this environment.
    name: str

    # File extension supported by this language. If there's only one language
    # that supports a certain file extension in the environment, the tool
    # will automatically identify the language based on such extension.
    extension: str

    # Compilation config to use when compiling programs for this language.
    compilation: Optional[CompilationConfig] = None

    # Execution config to use when running programs for this language.
    execution: ExecutionConfig

    # Mapping for files within the sandbox. If not specified, the default mapping
    # for the environment will be used.
    fileMapping: Optional[FileMapping] = None


class Environment(BaseModel):
    # Default mapping for files within the sandbox. Fields in the mapping can be
    # individually overridden in the language configuration.
    defaultFileMapping: Optional[FileMapping] = None

    # Default compilation configuration to use when compiling programs. Fields in
    # the compilation config can be individually overridden in the language configuration.
    defaultCompilation: Optional[CompilationConfig] = None

    # Default execution configuration to use when running programs. Fields in the
    # execution config can be individually overridden in the language configuration.
    defaultExecution: Optional[ExecutionConfig] = None

    # Configuration for each language supported in this environment.
    languages: Optional[List[EnvironmentLanguage]] = []

    # Identifier of the sandbox used by this environment (e.g. "stupid", "isolate")
    sandbox: str


def get_environment_path(env: str) -> pathlib.Path:
    return config.get_app_file(pathlib.PosixPath("environments") / f"{env}.cfk.yml")


@functools.cache
def get_environment(env: Optional[str] = None) -> Environment:
    env_path = get_environment_path(env or config.get_config().boxEnvironment)
    if not env_path.is_file():
        console.console.print(
            f"Environment file [item]{env_path}[/item] not found.", style="error"
        )
        raise typer.Exit()
    return utils.model_from_yaml(Environment, env_path.read_text())


@functools.cache
def get_language(name: str) -> EnvironmentLanguage:
    for lang in get_environment().languages:
        if lang.name == name:
            return lang
    console.console.print(f"Language [item]{name}[/item] not found.", style="error")
    raise typer.Exit()


def _merge_shallow_models(model: Type[T], base: T, override: T) -> T:
    return model(
        **{
            **base.model_dump(exclude_unset=True),
            **override.model_dump(exclude_unset=True),
        }
    )


def _merge_compilation_configs(
    compilation_configs: List[CompilationConfig],
) -> CompilationConfig:
    merged_cfg = CompilationConfig()
    merged_cfg.sandbox = EnvironmentSandbox(
        max_processes=None,
        timelimit=10000,
        wallTimeLimit=10000,
        memoryLimit=512,
        preserveEnv=True,
        mirrorDirs=["/etc", "/usr"],
    )
    for cfg in compilation_configs:
        merged_cfg.commands = cfg.commands or merged_cfg.commands
        merged_cfg.sandbox = _merge_shallow_models(
            EnvironmentSandbox, cfg.sandbox, merged_cfg.sandbox
        )
    return merged_cfg


@functools.cache
def get_compilation_config(language: str) -> CompilationConfig:
    environment = get_environment()
    return _merge_compilation_configs(
        [environment.defaultCompilation, get_language(language).compilation]
    )


def _merge_execution_configs(
    execution_configs: List[ExecutionConfig],
) -> ExecutionConfig:
    merged_cfg = ExecutionConfig()
    for cfg in execution_configs:
        merged_cfg.command = cfg.command or merged_cfg.command
        merged_cfg.sandbox = _merge_shallow_models(
            EnvironmentSandbox, cfg.sandbox, merged_cfg.sandbox
        )
    return merged_cfg


@functools.cache
def get_execution_config(language: str) -> ExecutionConfig:
    environment = get_environment()
    return _merge_execution_configs(
        [environment.defaultExecution, get_language(language).execution]
    )


@functools.cache
def get_file_mapping(language: str) -> FileMapping:
    environment = get_environment()
    return _merge_shallow_models(
        FileMapping,
        environment.defaultFileMapping or FileMapping(),
        get_language(language).fileMapping or FileMapping(),
    )