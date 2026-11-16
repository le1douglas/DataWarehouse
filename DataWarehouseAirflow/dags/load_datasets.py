# the loads: one dag per dataset, load_<dataset>, started by hand. write, audit, publish (docs/ARCHITECTURE_PROPOSAL.md,
# SIMPLIFIED IMPLEMENTATION): meltano appends the dataset's csv to bronze, dbt tests the load, and only an accepted load
# is published to silver and gold.
# the state of every load is in dw_control.ctl_loads, one row per load, written only here: landed, then accepted or
# refused, then published or failed. dbt reads it to choose the load staging holds (stg_<dataset>) and silver publishes
# (slvr_<dataset>).
# every run ends its load: a failure refuses it (audit) or fails it (publish), and the file is sent again. so a dataset
# has at most one open load, landed or accepted, and the audit and the publish always see that one load alone. a
# database outage between a dbt step and its state write can still leave one open: the next run stops before ingest
import os
from uuid import uuid7

import psycopg2
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task

# every dataset with a load. from its name come its meltano extractor, tap-csv-<dataset> with hyphens
# (DataWarehouseMeltano/meltano.yml), and its dbt models, stg_ and slvr_<dataset>
_DATASETS = ["journal_entries", "plants_batches"]

# set by the image and by the dev container (docker/airflow/Dockerfile, docker/dev/Dockerfile). dbt reads the project
# from the folder it runs in, and DBT_PROFILES_DIR by itself
_DBT_PROJECT_DIR = os.environ["DBT_PROJECT_DIR"]

# one publish at a time across every dataset: gold joins silver tables of more than one dataset, so two publishes
# would build the same fact at once. created with one slot by airflow-init (docker/compose.yaml)
_PUBLISH_POOL = "publish"


# the states of a load still under way: staging holds it (stg_<dataset>)
_OPEN_STATES = ("landed", "accepted")


def _connect():
    # dbt's connection (DataWarehouseDbt/profiles.yml), set on the scheduler (docker/compose.yaml)
    return psycopg2.connect(
        host=os.environ["DBT_HOST"],
        port=os.environ["DBT_PORT"],
        dbname=os.environ["DBT_DBNAME"],
        user=os.environ["DBT_USER"],
        password=os.environ["DBT_ENV_SECRET_PASSWORD"],
    )

# checks if there is a load that is stuck in an open state
def _open_loads(source: str) -> list[tuple[str, str]]:
    # the load_id and state of every open load of the dataset
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
    # the new state of a load: its row is inserted when it is landed, and updated for every state after
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
            # a load that was never landed has no row: nothing to update is a mistake, not a state
            if cursor.rowcount != 1:
                raise RuntimeError(f"load {load_id}: {cursor.rowcount} rows in ctl_loads, expected 1")
    connection.close()


def _make_load_dag(dataset: str) -> None:
    extractor = "tap-csv-" + dataset.replace("_", "-")

    def _record_on_failure(state: str):
        # a failure callback that ends the load in state. the task still fails, so airflow's failure alert is the
        # notification, and nothing after it runs
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
            # a load left landed or accepted by an outage between a dbt step and its state write would sit in staging
            # next to the new one, and the audit would judge both. the run stops before anything is loaded: a person
            # looks at the open load and ends it in ctl_loads, refused or failed, then the file is sent again
            open_loads = _open_loads(dataset)
            if open_loads:
                listed = ", ".join(f"{load_id} ({state})" for load_id, state in open_loads)
                raise RuntimeError(f"{dataset} has an open load, end it in dw_control.ctl_loads first: {listed}")

        @task
        def make_load_id() -> str:
            # time ordered, the same kind of id as postgres' uuidv7()
            return str(uuid7())

        # meltano writes MELTANO_RUN_ID into every bronze row as load_id. if it fails, no event is written: rows it
        # may have loaded are never landed, so dbt never reads them
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

        # the staging view, built so it matches the code, and every data test of the load. any failure, a
        # failed data test or an error of dbt, refuses the load whole: the file is fixed where it came from and sent
        # again. what failed, row by row, is in elementary's test_result_rows
        audit = BashOperator(
            task_id="audit",
            bash_command=f"dbt build --select stg_{dataset}",
            cwd=_DBT_PROJECT_DIR,
            on_failure_callback=_record_on_failure("refused"),
        )

        @task
        def accepted(load_id: str) -> None:
            _record(load_id, dataset, "accepted")

        # silver merges the accepted load, then gold is built on it. a failure fails the load: silver may hold it
        # already, so a person looks before the file is sent again
        publish = BashOperator(
            task_id="publish",
            bash_command=f"dbt build --select slvr_{dataset}+",
            cwd=_DBT_PROJECT_DIR,
            pool=_PUBLISH_POOL,
            on_failure_callback=_record_on_failure("failed"),
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
