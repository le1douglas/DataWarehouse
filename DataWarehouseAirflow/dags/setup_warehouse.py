# the setup of the warehouse: dbt build of everything no load builds, the seeds, the ref_ models, the dims over them and
# elementary's tables. started by hand, on a new database after its ddl (Database/01_create_schemas_and_tables.sql) and
# before its first load, and again after a seed or one of these models changes. elementary in one plain task first, then
# a cosmos task group, one airflow task per dbt node, as the load dags (load_datasets.py)
import os
from datetime import datetime

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag
from utils.dbt_task_group import dbt_task_group

# the reference data and what is built on it: the seeds, ref_ models and gold. without anything downstream of silver:
# silver takes the accepted load, so only a load's publish builds it and what reads it, and writes published
_SELECT = ["resource_type:seed", "path:models/ref", "path:models/gold"]
_EXCLUDE = ["path:models/silver+"]


@dag(
    dag_id="setup_warehouse",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    # a failed build is looked at before it runs again
    default_args={"retries": 0},
    tags=["setup"],
)
def setup_warehouse():
    # elementary's own tables, about thirty models nobody needs to see one by one: one dbt build. first, so the
    # tables its on-run-end hook writes to exist before the dbt builds of the group
    elementary = BashOperator(
        task_id="elementary",
        bash_command="dbt build --select package:elementary",
        # dbt reads the project from the folder it runs in, and DBT_PROFILES_DIR by itself. set by the image and by the
        # dev container (docker/airflow/Dockerfile, docker/dev/Dockerfile)
        cwd=os.environ["DBT_PROJECT_DIR"],
    )

    # cautious: staging's tests read ref_ models too, and are left to the audit of a load. the relationships between
    # ref_ models still run, each in its own task
    build = dbt_task_group("build", _SELECT, _EXCLUDE, cautious=True)

    elementary >> build


setup_warehouse()
