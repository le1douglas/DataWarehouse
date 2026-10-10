# Data flow

How a journal entry moves from the CSV file to silver, and how a correction comes back in.

```mermaid
flowchart TD
    csv[/"CSV file<br/>edenic export"/]
    brnz[("Bronze<br/><span style='color: #e6b800'>dev_bronze</span>.brnz_#lt;dataset#gt;")]
    corr[("Corrections<br/><span style='color: #e6b800'>dev_corrections</span>.corr_#lt;dataset#gt;")]
    stg("Staging<br/><span style='color: #e6b800'>dev_staging</span>.stg_#lt;dataset#gt;")
    cand("Candidate<br/><span style='color: #e6b800'>dev_candidate</span>.cand_#lt;dataset#gt;")
    tests{"Data tests"}
    fail@{ shape: st-rect, label: "Audit, failure tables<br/><span style='color: #e6b800'>dev_audit</span>.aud_#lt;dataset#gt;__#lt;rule#gt;<br/>one table per data test" }
    aud("Audit, view<br/><span style='color: #e6b800'>dev_audit</span>.aud_#lt;dataset#gt;")
    slvr["Silver<br/><span style='color: #e6b800'>dev_silver</span>.slvr_#lt;dataset#gt;"]

    subgraph xlsx["Excel workbook"]
        qcols{{"Power Query<br/>staging's column names"}}
        qcand{{"Power Query<br/>candidate's rows, but only the columns that exist in staging"}}
        qaud{{"Power Query<br/>the audit view's flagged rows"}}
        comb{{"Power Query<br/>combine context and flagged rows"}}
        review["Excel sheet_name1<br/>where the user actually modifies the values"]
        qsel{{"Power Query<br/>read the whole corrected table,<br/>keep only the rows from the audit view"}}
        corrected["Excel sheet_name2<br/>only the corrected rows, with no context"]
    end

    csv -->|"python"| brnz
    brnz -->|"dbt"| stg
    stg -->|"dbt"| cand
    corr -->|"dbt"| cand
    cand -->|"dbt data tests"| tests
    tests -->|"all pass: dbt"| slvr
    tests -->|"failing rows"| fail
    fail -->|"dbt on-run-end"| aud
    stg -.->|"Excel via ODBC (column structure, no data)"| qcols
    cand -.->|"Excel via ODBC"| qcand
    aud -->|"Excel via ODBC"| qaud
    qcols -.-> qcand
    qcand -.->|"context"| comb
    qaud -->|"flagged rows"| comb
    comb --> review
    review --> qsel
    qsel --> corrected
    corrected -->|"python"| corr

    linkStyle 0,1,2,4,5 stroke:#2e9e44
```


## Legend

| Drawing | Meaning |
|---|---|
| Slanted box | A file outside the database |
| Cylinder | An input: a table filled from outside the warehouse |
| Rounded box | A view built by dbt |
| Rectangle | A table built by dbt |
| Stacked rectangle | Several tables of the same kind |
| Diamond | The gate: silver is built only when every data test passes |
| Frame | The Excel workbook, a file outside the database, and what is inside it |
| Hexagon | A Power Query query inside the workbook |
| Rectangle in the frame | A table in the workbook |
| Solid arrow | Data moves, and the label says what moves it |
| Dotted arrow | A dependency that is not part of the flow |
