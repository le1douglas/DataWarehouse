# the loads: one dag per dataset, load_<dataset>. meltano appends the dataset's csv to bronze, then dbt judges that load
# alone and adds it to silver only when its data tests pass. one load is the two commands with one load_id, which every
# bronze row gets
from uuid import uuid7

from airflow.sdk import dag, task

# every dataset with a load. from its name come its meltano extractor, tap-csv-<dataset> with hyphens
# (DataWarehouseMeltano/meltano.yml), and its bronze table, brnz_<dataset>, the dbt source the build starts from
# (DataWarehouseDbt/models/sources.yml)
_DATASETS = ["journal_entries", "plants_batches"]


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

        @task.bash
        def build(load_id: str) -> str:
            # staging holds only this load, so its data tests judge it alone. a refused load fails this task
            return f"dbt build --select source:dw_bronze.{bronze_table}+ --vars '{{load_id: {load_id}}}'"

        load_id = make_load_id()
        extract_load(load_id) >> build(load_id)

    load()


for _dataset in _DATASETS:
    _make_load_dag(_dataset)
