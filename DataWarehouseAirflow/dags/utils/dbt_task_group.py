# the cosmos setup every dag shares: a dbt build as a cosmos task group, one airflow task per dbt node. imported by its
# full path, utils.dbt_task_group, as airflow's modules management asks: the dags folder is on the python path, and
# utils is in .airflowignore, so the dag processor does not parse it as a dag
import os
from pathlib import Path

from cosmos import DbtTaskGroup, ExecutionConfig, LoadMode, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import ExecutionMode, InvocationMode, TestBehavior

# dbt is in its own venv, not airflow's: cosmos runs it as a subprocess, never imports it
_DBT_EXECUTABLE = "/opt/venvs/dbt/bin/dbt"
# set by the image and by the dev container (docker/airflow/Dockerfile, docker/dev/Dockerfile)
_DBT_PROJECT_DIR = Path(os.environ["DBT_PROJECT_DIR"])
_DBT_PROFILES_DIR = Path(os.environ["DBT_PROFILES_DIR"])
# the manifest every dbt parse, compile or build writes, read to draw the tasks: no dbt ls when a task starts, as every
# task parses its dag file again. in DBT_TARGET_PATH, dev's dbt-state volume, which any dbt command of the dev container
# rewrites (docker/compose.dev.yaml); in prod, unset, the project's target, written by dbt parse at the image build
# (docker/airflow/Dockerfile). a model added since the last parse has no task until dbt parses again
_DBT_MANIFEST = _DBT_PROJECT_DIR / os.environ.get("DBT_TARGET_PATH", "target") / "manifest.json"


def dbt_task_group(
    group_id: str,
    select: list[str],
    exclude: list[str] | None = None,
    cautious: bool = False,
    operator_args: dict | None = None,
) -> DbtTaskGroup:
    # the dbt build of select, without exclude, one task per node. a failed node fails its task, and the nodes after it
    # are not run, as with one dbt build. operator_args go to every task of the group.
    # cautious: a test is selected only when every model it reads is, so a test reading a model left out of select is
    # not run. a test reading two selected models then runs in its own task after both, as no single node's build
    # selects it
    return DbtTaskGroup(
        group_id=group_id,
        project_config=ProjectConfig(
            dbt_project_path=_DBT_PROJECT_DIR,
            manifest_path=_DBT_MANIFEST,
            # the packages are installed already: by the image build in prod, in the dbt-state volume in dev
            install_dbt_deps=False,
            env_vars={
                # relative to the project: cosmos runs every task in its own temp copy of the project, so each writes
                # its own target and logs. dev points both at the shared dbt-state volume (docker/compose.dev.yaml),
                # where tasks running at once broke each other's partial parse. prod sets neither, so this is its
                # default. cosmos's partial parse cache reads <project>/target as well
                "DBT_TARGET_PATH": "target",
                "DBT_LOG_PATH": "logs",
                # dbt reads it by itself, in every node's dbt build. cosmos draws the tasks from the manifest without
                # it: should_detach_multiple_parents_tests below gives the same tasks
                **({"DBT_INDIRECT_SELECTION": "cautious"} if cautious else {}),
            },
        ),
        profile_config=ProfileConfig(
            profile_name="DataWarehouseDbt",
            target_name="dw",
            profiles_yml_filepath=_DBT_PROFILES_DIR / "profiles.yml",
        ),
        execution_config=ExecutionConfig(
            execution_mode=ExecutionMode.LOCAL,
            invocation_mode=InvocationMode.SUBPROCESS,
            dbt_executable_path=_DBT_EXECUTABLE,
        ),
        render_config=RenderConfig(
            # the tasks drawn from the manifest, by cosmos's own reading of select and exclude
            load_method=LoadMode.DBT_MANIFEST,
            select=select,
            exclude=exclude or [],
            # a model and its tests in one task, dbt build of that node: a failed test fails the task
            test_behavior=TestBehavior.BUILD,
            should_detach_multiple_parents_tests=cautious,
        ),
        operator_args=operator_args or {},
    )
