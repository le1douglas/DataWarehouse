# the load dags: one per dataset, load_<dataset>, started by hand
# - meltano appends the csv to bronze, dbt audits the load, and only an accepted load is published to silver and gold
# - each step writes the load's state to dw_control.ctl_loads, which dbt reads to choose the load
# - every run ends its load, so a dataset has at most one open load
# - an outage between a dbt step and its state write can leave one open: the next run stops before ingest
# - audit and publish are cosmos task groups, one task per dbt node, so airflow shows which model or test failed
import os
from uuid import uuid7

import psycopg2
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task
from utils.dbt_task_group import dbt_task_group

# the name gives the meltano extractor (tap-csv-<dataset>, with hyphens) and the dbt models (stg_, slvr_<dataset>)
_DATASETS = ["journal_entries", "plants_batches"]

# one slot, taken per dbt node: gold joins the silver of more than one dataset, so two publishes must never build the
# same node at once. created by airflow-init (docker/compose.yaml)
_PUBLISH_POOL = "publish"


# a load in one of these states is in staging
_OPEN_STATES = ("landed", "accepted")


def _connect():
    # dbt's connection (data_build_tool/profiles.yml), set on the scheduler (docker/compose.yaml)
    return psycopg2.connect(
        host=os.environ["DBT_HOST"],
        port=os.environ["DBT_PORT"],
        dbname=os.environ["DBT_DBNAME"],
        user=os.environ["DBT_USER"],
        password=os.environ["DBT_ENV_SECRET_PASSWORD"],
    )


def _open_loads(source: str) -> list[tuple[str, str]]:
    connection = _connect()
    with connection, connection.cursor() as cursor:
        cursor.execute(
            "select load_id::text, state from dw_control.ctl_loads where source = %s and state in %s order by load_id",
            (source, _OPEN_STATES),
        )
        rows = cursor.fetchall()
    connection.close()
    return rows


def _record(load_id: str, source: str, state: str) -> None:
    connection = _connect()
    with connection, connection.cursor() as cursor:
        if state == "landed":
            cursor.execute(
                "insert into dw_control.ctl_loads (load_id, source, state) values (%s, %s, %s)",
                (load_id, source, state),
            )
        else:
            cursor.execute(
                "update dw_control.ctl_loads set state = %s, updated_at = clock_timestamp() where load_id = %s",
                (state, load_id),
            )
            # a load that was never landed has no row: a bug, not a state
            if cursor.rowcount != 1:
                raise RuntimeError(f"load {load_id}: {cursor.rowcount} rows in ctl_loads, expected 1")
    connection.close()


def _make_load_dag(dataset: str) -> None:
    extractor = "tap-csv-" + dataset.replace("_", "-")

    def _record_on_failure(state: str):
        # ends the load in state. the task still fails, so airflow's failure alert is the notification
        def callback(context) -> None:
            _record(context["ti"].xcom_pull(task_ids="make_load_id"), dataset, state)

        return callback

    @dag(
        dag_id=f"load_{dataset}",
        schedule=None,
        catchup=False,
        # one load at a time per dataset, so it has at most one open load
        max_active_runs=1,
        # no retries: a failed run ends its load, the file is sent again as a new load
        default_args={"retries": 0},
        tags=["load", dataset],
    )
    def load():
        @task
        def no_open_load() -> None:
            # a load left open by an outage would sit in staging next to the new one, and the audit would judge both
            # - a person ends it in ctl_loads (refused or failed), then the file is sent again
            open_loads = _open_loads(dataset)
            if open_loads:
                listed = ", ".join(f"{load_id} ({state})" for load_id, state in open_loads)
                raise RuntimeError(f"{dataset} has an open load, end it in dw_control.ctl_loads first: {listed}")

        @task
        def make_load_id() -> str:
            # time ordered, like postgres' uuidv7()
            return str(uuid7())

        # meltano writes MELTANO_RUN_ID into every bronze row as load_id
        # - on failure no state is written: rows it may have loaded are never landed, so dbt never reads them
        ingest = BashOperator(
            task_id="ingest",
            bash_command=f"meltano run {extractor} target-postgres",
            env={"MELTANO_RUN_ID": "{{ ti.xcom_pull(task_ids='make_load_id') }}"},
            append_env=True,
        )

        @task
        def landed(load_id: str) -> None:
            # the rows are in bronze: from now on the load is under audit
            _record(load_id, dataset, "landed")

        # the staging view and every data test of the load
        # - any failure, a data test or a dbt error, refuses the whole load: the file is fixed and sent again
        # - the failing rows are in elementary's test_result_rows
        # - the tasks after a failed one end upstream_failed, which runs no callback, so the load is refused once
        audit = dbt_task_group(
            "audit",
            [f"stg_{dataset}"],
            operator_args={"on_failure_callback": _record_on_failure("refused")},
        )

        @task
        def accepted(load_id: str) -> None:
            _record(load_id, dataset, "accepted")

        # silver takes the accepted load, then gold is built on it
        # - a failure fails the load: silver may hold it already, so a person looks before the file is sent again
        publish = dbt_task_group(
            "publish",
            [f"slvr_{dataset}+"],
            operator_args={"on_failure_callback": _record_on_failure("failed"), "pool": _PUBLISH_POOL},
        )

        @task
        def published(load_id: str) -> None:
            _record(load_id, dataset, "published")

        load_id = make_load_id()
        no_open_load() >> load_id
        load_id >> ingest >> landed(load_id) >> audit >> accepted(load_id) >> publish >> published(load_id)

    load()


for _dataset in _DATASETS:
    _make_load_dag(_dataset)
