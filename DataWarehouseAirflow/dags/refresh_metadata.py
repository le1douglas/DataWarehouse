# the refresh of gold and of what its readers take from the database's catalog, started by hand: before an
# openmetadata ingestion, before a new excel or power bi model, which read gold's keys to draw the diagram and suggest
# the relationships, and to bring gold up to today without a load (fct_journal_entries__daily runs to the day of its
# build). gold is built again first, then its keys are added: a table built again loses its keys, and the foreign keys
# pointing at it. nothing in the pipeline relies on the keys, so no other dag adds or keeps them: dbt_constraints is
# off in every other dbt run (dbt_project.yml), and they are missing until the next run of this dag
import os
from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag
from utils.dbt_task_group import dbt_task_group

# every primary, unique and foreign key test of the project: the tests of dbt_constraints, the only package with tests
# of these names. each one runs, and the package's on-run-end hook adds the key of each test that passed and is
# missing. a key whose test fails, or whose table is not built yet (on a database without the setup build), stays
# missing and fails the task, after the hook has added the others
_KEY_TESTS = "test_name:primary_key test_name:unique_key test_name:foreign_key"

# the pool of the loads' publish (load_datasets.py): one slot, so this dag never builds gold, or alters its tables, next
# to a load's build of gold
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
    # every gold model and its tests, built again from silver and the seeds, as a load's publish builds them: one task
    # per node. silver is not touched, so no load is published
    gold = dbt_task_group("gold", ["path:models/gold"], operator_args={"pool": _PUBLISH_POOL})

    keys = BashOperator(
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
        pool=_PUBLISH_POOL,
    )

    # the keys of the tables just built: a failed build of gold adds none
    gold >> keys


refresh_metadata()
