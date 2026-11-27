# started by hand:
# - before an OpenMetadata ingestion or a new Excel or Power BI model, which read gold's keys
# - to bring gold up to today without a load (fct_journal_entries__daily runs to the day of its build)
# it rebuilds gold, adds back the keys a rebuild drops, then refreshes airflow's manifest: never run it during a load
import os
from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag
from utils.dbt_task_group import dbt_task_group

# the dbt_constraints tests, the only ones with these names
# - the package's on-run-end hook adds the key of each test that passed and is missing
# - a key whose test fails, or whose table does not exist yet, stays missing and fails the task, after the others
_KEY_TESTS = "test_name:primary_key test_name:unique_key test_name:foreign_key"

# the loads' publish pool (load_datasets.py), so this dag never builds or alters a gold table during a publish
_PUBLISH_POOL = "publish"


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
    # gold rebuilt as a publish builds it. silver is not touched, so no load is published
    gold = dbt_task_group("gold", ["path:models/gold"], operator_args={"pool": _PUBLISH_POOL})

    keys = BashOperator(
        task_id="keys",
        # - the package is on only in this dbt run; dbt test builds nothing, so it drops no key
        # - its own target, metadata-export, which OpenMetadata and the diagram read, never airflow's manifest
        # - --vars forces a full parse, kept in this folder
        bash_command=(
            f"dbt test --select {_KEY_TESTS} --vars '{{dbt_constraints_enabled: true}}'"
            " --target-path $DBT_METADATA_EXPORT_DIR/target --log-path $DBT_METADATA_EXPORT_DIR/logs"
        ),
        # dbt reads the project from the folder it runs in (DBT_PROJECT_DIR: docker/pipeline/Dockerfile)
        cwd=os.environ["DBT_PROJECT_DIR"],
        pool=_PUBLISH_POOL,
    )

    # airflow's manifest, refreshed as on every up, so a new or changed model or test reaches the dags
    # - last, so this run's own tasks do not change under it: a new gold model gets its task from the next run
    # - the packages are not installed again: a change to packages.yml still needs an up
    # - no check for a running load: like an up, this dag is not started during one
    airflow_manifest = BashOperator(
        task_id="airflow_manifest",
        bash_command=(
            "dbt parse --target-path $DBT_STATE_DIR/airflow-manifest/target"
            " --log-path $DBT_STATE_DIR/airflow-manifest/logs"
        ),
        cwd=os.environ["DBT_PROJECT_DIR"],
    )

    # a failed gold build adds no keys, and a failed refresh is looked at before the manifest changes
    gold >> keys >> airflow_manifest


refresh_metadata()
