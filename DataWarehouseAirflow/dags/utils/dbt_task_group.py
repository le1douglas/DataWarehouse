# the cosmos task group every dag uses: a dbt build, one airflow task per dbt node
# - imported as utils.dbt_task_group: the dags folder is on the python path
# - utils is in .airflowignore, so the dag processor does not parse it as a dag
import os
from pathlib import Path

from cosmos import DbtTaskGroup, ExecutionConfig, LoadMode, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import ExecutionMode, InvocationMode, TestBehavior

# dbt is in its own venv, not airflow's: cosmos runs it as a subprocess, never imports it
_DBT_EXECUTABLE = "/opt/venvs/dbt/bin/dbt"
# set in docker/pipeline/Dockerfile
_DBT_PROJECT_DIR = Path(os.environ["DBT_PROJECT_DIR"])
_DBT_PROFILES_DIR = Path(os.environ["DBT_PROFILES_DIR"])
# airflow's manifest, read to draw the tasks, so a task does not run dbt ls each time it parses its dag file again
# - written by airflow-init on every up and by refresh_metadata, neither started during a load
# - a model added since has no task until the manifest is refreshed
_DBT_MANIFEST = Path(os.environ["DBT_STATE_DIR"]) / "airflow-manifest" / "target" / "manifest.json"


def dbt_task_group(
    group_id: str,
    select: list[str],
    operator_args: dict | None = None,
) -> DbtTaskGroup:
    # the dbt build of select, one task per node
    # - a failed node fails its task and skips the nodes after it, as one dbt build would
    # - operator_args go to every task
    return DbtTaskGroup(
        group_id=group_id,
        project_config=ProjectConfig(
            dbt_project_path=_DBT_PROJECT_DIR,
            manifest_path=_DBT_MANIFEST,
            # installed already: in the image in prod, in the dbt-state volume in dev
            install_dbt_deps=False,
            env_vars={
                # relative to the project: cosmos runs each task in its own temporary copy of the project
                # - compose's shared interactive folder let tasks running at once break each other's partial parse
                # - cosmos' partial parse cache reads <project>/target too
                "DBT_TARGET_PATH": "target",
                "DBT_LOG_PATH": "logs",
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
            # cosmos reads select itself, against the manifest
            load_method=LoadMode.DBT_MANIFEST,
            select=select,
            # a model and its tests in one task: a failed test fails the task
            test_behavior=TestBehavior.BUILD,
        ),
        operator_args=operator_args or {},
    )
