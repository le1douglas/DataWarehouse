# the loads: one dag per dataset, load_<dataset>. meltano appends the dataset's csv to bronze, then cosmos runs the dbt
# build of that load as one airflow task per node, so the ui shows which model or test refused it. dbt judges that load
# alone and adds it to silver only when its data tests pass. one load is the two commands with one load_id, which every
# bronze row gets
import os
from pathlib import Path
from uuid import uuid7

from airflow.sdk import dag, task
from cosmos import (
    DbtTaskGroup,
    ExecutionConfig,
    LoadMode,
    ProfileConfig,
    ProjectConfig,
    RenderConfig,
)
from cosmos.constants import ExecutionMode, InvocationMode, SourceRenderingBehavior, TestBehavior

# every dataset with a load. from its name come its meltano extractor, tap-csv-<dataset> with hyphens
# (DataWarehouseMeltano/meltano.yml), and its bronze table, brnz_<dataset>, the dbt source the build starts from
# (DataWarehouseDbt/models/sources.yml)
_DATASETS = ["journal_entries", "plants_batches"]

# dbt is in its own venv, not airflow's: cosmos runs it as a subprocess, never imports it
_DBT_EXECUTABLE = "/opt/venvs/dbt/bin/dbt"
# set by the image and by the dev container (docker/airflow/Dockerfile, docker/dev/Dockerfile)
_DBT_PROJECT_DIR = Path(os.environ["DBT_PROJECT_DIR"])
_DBT_PROFILES_DIR = Path(os.environ["DBT_PROFILES_DIR"])


def _make_load_dag(dataset: str) -> None:
    extractor = "tap-csv-" + dataset.replace("_", "-")
    bronze_table = "brnz_" + dataset

    @dag(
        dag_id=f"load_{dataset}",
        # started by hand from the ui, for now
        schedule=None,
        catchup=False,
        # one load at a time: two builds at once leave silver wrong while both report success (docs/UPLOAD_REPORT.csv,
        # 6.5 and 6.6)
        max_active_runs=1,
        # no retries: a failed meltano run may have loaded the rows anyway, and a failed build may have reached silver
        # (docs/UPLOAD_REPORT.csv, 7.2 and 12.2). a retry would load or judge the file twice, so a person looks first
        default_args={"retries": 0},
        tags=["load", dataset],
    )
    def load():
        @task
        def make_load_id() -> str:
            # time ordered, the same kind of id as postgres' uuidv7()
            return str(uuid7())

        @task.bash
        def extract_load(load_id: str) -> str:
            # meltano writes MELTANO_RUN_ID into every bronze row as load_id
            return f"MELTANO_RUN_ID={load_id} meltano run {extractor} target-postgres"

        build = DbtTaskGroup(
            group_id="build",
            project_config=ProjectConfig(
                dbt_project_path=_DBT_PROJECT_DIR,
                # the packages are installed already: by the image build in prod, in the dbt-state volume in dev
                install_dbt_deps=False,
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
                # the dag processor runs dbt ls to draw the tasks. dbt parses without the load_id var, only compiling
                # staging needs it
                load_method=LoadMode.DBT_LS,
                dbt_executable_path=_DBT_EXECUTABLE,
                select=[f"source:dw_bronze.{bronze_table}+"],
                # one dbt build per node, its tests in the same task: a failed test fails the task, and everything after
                # it is not run, as with one dbt build. silver is added only when staging passes
                test_behavior=TestBehavior.BUILD,
                # the source's own tests in a task before staging: the row count test refuses a file without rows.
                # without this cosmos leaves sources out, and that test would never run
                source_rendering_behavior=SourceRenderingBehavior.WITH_TESTS_OR_FRESHNESS,
            ),
            operator_args={
                # every dbt command of this run gets the same load_id, so staging holds only this load. rendered when
                # the task runs, from the id make_load_id returned
                "vars": {"load_id": "{{ ti.xcom_pull(task_ids='make_load_id') }}"},
            },
        )

        load_id = make_load_id()
        extract_load(load_id) >> build

    load()


for _dataset in _DATASETS:
    _make_load_dag(_dataset)
