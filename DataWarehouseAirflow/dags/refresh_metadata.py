# the refresh of what the readers of gold take from the database's catalog, started by hand: before an openmetadata
# ingestion, and before a new excel or power bi model, which read gold's keys to draw the diagram and suggest the
# relationships. nothing in the pipeline relies on them, so no other dag adds or keeps them: dbt_constraints is off in
# every other dbt run (dbt_project.yml), and a table built again loses its keys, and the foreign keys pointing at it,
# until the next run of this dag
import os
from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag

# every primary, unique and foreign key test of the project: the tests of dbt_constraints, the only package with tests
# of these names. each one runs, and the package's on-run-end hook adds the key of each test that passed and is
# missing. a key whose test fails, or whose table is not built yet (a fact before its first load), stays missing and
# fails the task, after the hook has added the others
_KEY_TESTS = "test_name:primary_key test_name:unique_key test_name:foreign_key"


@dag(
    dag_id="refresh_metadata",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    # a failed refresh is looked at before it runs again
    default_args={"retries": 0},
    tags=["metadata"],
)
def refresh_metadata():
    BashOperator(
        task_id="keys",
        # the package's hooks run only in this dbt invocation. dbt test builds nothing, so they drop no key.
        # its own target and logs, metadata-export (x-dbt-env in docker/compose.yaml), which openmetadata and the erd
        # read: never airflow's manifest. its --vars force a full parse, which stays in this folder's partial parse
        bash_command=(
            f"dbt test --select {_KEY_TESTS} --vars '{{dbt_constraints_enabled: true}}'"
            " --target-path $DBT_METADATA_EXPORT_DIR/target --log-path $DBT_METADATA_EXPORT_DIR/logs"
        ),
        # dbt reads the project from the folder it runs in, and DBT_PROFILES_DIR by itself. set by the image and by the
        # dev container (the venvs stage of docker/pipeline/Dockerfile)
        cwd=os.environ["DBT_PROJECT_DIR"],
        # the publish pool of the loads (load_datasets.py), so its alter tables never run next to a build of gold
        pool="publish",
    )


refresh_metadata()
