# Architecture proposal: loads without dbt as the gate

Many sources (csv, Excel, APIs), always batches. Under 10k rows per load, under 50M rows per table: Postgres stays.

**The idea:** the orchestrator owns the gate and the state. dbt transforms and tests, and holds no state.

## 1. Overview

```mermaid
flowchart LR
    subgraph sources["Sources"]
        csv["csv"]
        xls["Excel"]
        api["API"]
    end

    subgraph orch["Orchestrator"]
        pre["Pre-load checks<br/>files only"]
        conn["Connector<br/>Meltano / dlt"]
        verdict["Verdict"]
    end

    archive[("File archive<br/>every file, by checksum")]

    subgraph pg["Postgres"]
        ctl[("dw_control.loads<br/>the ledger")]
        bronze[("dw_bronze<br/>append-only")]
        stg["dw_staging<br/>typed views"]
        silver[("dw_silver<br/>incremental, by load order")]
        gold[("dw_gold")]
    end

    csv & xls --> pre --> archive
    pre -->|ok| conn
    api --> conn
    conn --> bronze
    conn -.->|landed| ctl
    bronze --> stg -->|dbt test| verdict
    verdict -.->|accepted / refused / quarantined| ctl
    stg -->|dbt build: accepted loads| silver --> gold
    silver -.->|in_silver| ctl
```

## 2. One load

```mermaid
sequenceDiagram
    autonumber
    participant O as Orchestrator
    participant C as Connector
    participant L as dw_control.loads
    participant D as dbt
    participant S as dw_silver

    O->>O: pre-load checks (files)
    O->>C: extract, load_id = uuidv7
    C->>C: rows into dw_bronze
    O->>L: landed
    O->>D: dbt test, this load only (--vars load_id)
    D-->>O: run_results.json
    alt every test passes
        O->>L: accepted
    else a test fails, policy strict
        O->>L: refused
        O->>O: notify the source owner
    else a test fails, policy quarantine
        O->>L: quarantined + failing row_ids
    else an error
        O->>O: retry, the load stays landed
    end
    O->>D: dbt build silver+ (no var)
    D->>S: add accepted loads not yet in_silver, in load_id order
    O->>L: in_silver
```

The var only filters the tests of that run. No saved object holds it.

## 3. A load's life

```mermaid
stateDiagram-v2
    [*] --> rejected: pre-load checks fail
    [*] --> landed: connector finished
    landed --> landed: error, retry
    landed --> accepted: tests pass
    landed --> refused: tests fail, strict
    landed --> quarantined: tests fail, quarantine
    accepted --> in_silver
    quarantined --> in_silver: without the failing rows
    rejected --> [*]
    refused --> [*]
    in_silver --> [*]
```

`accepted` = allowed into silver. `in_silver` = its rows are in silver now: new keys inserted, existing keys replaced.

One row per event in `dw_control.loads`, never updated. Not `landed` yet = invisible to dbt.

## 4. Per-source settings

```mermaid
flowchart TD
    src["A source"] --> pol{"Refusal policy"}
    pol -->|strict| s["A failing load is refused whole<br/>own files: fixed at the source"]
    pol -->|quarantine| q["Failing rows held back, rest goes on<br/>external sources, APIs"]
    src --> drift{"Schema drift"}
    drift -->|refuse| r["New column = load rejected"]
    drift -->|evolve| e["Column added to bronze, alert"]
    src --> lim["Row limit per load<br/>below the connector's batch size"]
```

## 5. dbt, stateless

```mermaid
flowchart LR
    bronze[("bronze")] --> stg["staging<br/>view, every landed row, no filter"]
    stg --> slv[("silver<br/>incremental: accepted, not yet in_silver,<br/>ordered by load_id")]
    seeds[("seeds")] --> ref["ref_<br/>views"] --> dims[("gold dims<br/>full tables, small")]
    slv --> facts[("gold facts<br/>incremental, by load")]
    dims --> facts
    ctl[("dw_control.loads")] -.->|which loads| slv
```

- Every output = f(bronze, ledger, seeds, code).
- Silver rebuild = replay accepted loads in `load_id` order. Minutes, recovery only.
- History = the accepted versions in bronze. No snapshots.

## 6. DAGs (or jobs)

```mermaid
flowchart LR
    subgraph perSource["Per source, one load at a time"]
        a1["pre-load"] --> a2["extract"] --> a3["test"] --> a4["verdict"] --> a5["add to silver+"]
    end
    subgraph sched["Scheduled"]
        b1["refresh<br/>seeds, ref_, dims"] --> b2["catalog<br/>docs generate, OpenMetadata"]
    end
    subgraph catch["Catch-up"]
        c1["landed loads without a verdict"] --> a3
    end
```

Sources run in parallel; one dataset never runs two loads at once.

## 7. Roles

```mermaid
flowchart LR
    admin(["admin"]) -->|owns, DDL| bronze[("dw_bronze")]
    conn(["connector"]) -->|INSERT, SELECT| bronze
    orch(["orchestrator"]) -->|INSERT, SELECT| ctl[("dw_control")]
    dbt(["dbt"]) -->|SELECT| bronze
    dbt -->|SELECT| ctl
    dbt -->|CREATE| out[("dw_staging, dw_silver, dw_gold")]
    readers(["Excel, web apps, catalog"]) -->|SELECT| gold[("dw_gold")]
```

## 8. What goes away

| Today | Replaced by |
|---|---|
| `load_id` var typed by hand, a build failing on purpose without it | orchestrator passes it to tests only |
| dbt skip-on-failure as the gate, `-- depends_on: ref_*` | verdict in the ledger |
| Tests reading silver from the graph | plain `ref`, test and build are separate runs |
| Staging view holding one load's id | staging over all landed rows |
| Bootstrap build, "never `seed_x+`" | scheduled refresh job |
| Silver `full_refresh: false`, not rebuildable | replay from bronze + ledger |
| Snapshots | history from bronze by load |
| Rollback by rebuilding an old id (4.2) | loads added in `load_id` order |
| Two builds at once (6.5) | one load at a time per dataset |
| Gold facts rebuilt in full per load | incremental facts |
| `aud_issues` load from `invocation_vars` | join the ledger; audit is observability only |

## 9. Migration, one step each

```mermaid
flowchart TD
    m1["1. dw_control.loads"] --> m2["2. Orchestrator runs today's two commands, writes verdicts"]
    m2 --> m3["3. Test and build split; gate workarounds removed"]
    m3 --> m4["4. Staging unfiltered, silver filled in ledger order"]
    m4 --> m5["5. Snapshots retired, history from bronze"]
    m5 --> m6["6. Gold facts incremental"]
    m6 --> m7["7. Pre-load checks, checksum, per-source policy"]
```

Each step leaves a working pipeline.

## Open decisions

- Orchestrator: Dagster (assets, blocking checks) or Airflow (most common).
- Connector: keep Meltano, or dlt (ledger built in).
- Where quarantined rows live, and who reviews them.
