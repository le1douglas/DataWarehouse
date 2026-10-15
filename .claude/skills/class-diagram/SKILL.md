---
name: class-diagram
description: Write the Mermaid class diagram of the Python code in src/datawarehouse to docs/CLASS_DIAGRAM.md. Runs only when the user types /class-diagram.
disable-model-invocation: true
---

# Class diagram

Write a Mermaid class diagram of the Python code in `src/datawarehouse` and save it as `docs/CLASS_DIAGRAM.md`, replacing the file that is there.

The diagram is written without the use of any external dependecies.

## Steps

1. Read every `.py` file under `src/datawarehouse`, in full. Work from the source, not from the existing `docs/CLASS_DIAGRAM.md`: that file may be out of date, and copying it forward hides what changed.
2. List what goes in the diagram (see "What to draw") and the relationships between those things.
3. If anything on the list is a judgment call, ask the user before writing the file (see "When to ask").
4. Write `docs/CLASS_DIAGRAM.md` in the shape given under "Output".
5. Check the result against the source (see "Check before reporting").
6. Report what changed compared to the previous diagram, and say that the diagram was not rendered, so the user should open the Markdown preview.

## What to draw

Draw everything the user wrote, and nothing they did not.

**Drawn:**

- Every class defined in the package, including a `Protocol`, an abstract class, a dataclass, an enum and a nested class.
- Every generic type defined in the package, such as `RecordT = TypeVar("RecordT", bound=Record)`. Mark it `<<TypeVar>>` and connect it to its bound.
- Every module that has functions of its own at module level, such as `__main__.py`. Draw it as a box marked `<<module>>`, named after the file without `.py`, with its functions listed as methods.

**Not drawn:**

- A module that is only the file around a class or a generic type. The class or type is drawn, the module is not.
- `config.py`. It holds only constants, and the user excluded it by name.
- An empty `__init__.py`.
- Anything from the standard library or from an installed library. No `BaseModel`, `Protocol`, `datetime`, `Decimal`, `Path`, `DataFrame` or `Engine` boxes, and no arrows to them. These names still appear as the type of an attribute, parameter or return value, because that is part of showing the user's own class in full.

## Library parents

A class that inherits from a library class gets no arrow, because the parent has no box. The fact still matters, so show it as a stereotype on the class itself:

- `<<pydantic model>>` on every class whose objects pydantic validates: a class that inherits from `BaseModel`, and every class below it. `BrnzRecordJournalEntries` inherits from `Record`, not from `BaseModel`, and still carries the mark, because the mark tells the reader that creating an object of this class validates it.
- `<<protocol>>` on a class that inherits from `Protocol`.
- For any other library parent, a stereotype with a short name for what the parent makes the class (`<<enum>>`, `<<dataclass>>`, `<<abstract>>`).

Mermaid shows one stereotype per box. When a class would need two, ask the user which one to show.

## Show every box in full

A box lists everything its class defines. Never shorten a class to its "interesting" members: the user reads the diagram as a complete inventory, and a member that is missing reads as a member that does not exist.

- **Attributes:** every annotated class attribute, every class-level assignment (`model_config = ...`), and every `self.x` assigned anywhere in the class.
- **Methods:** every `def`, including an `__init__` whose body is `pass`, other dunder methods, private helpers, static methods, class methods, validators, and both the getter and the setter of a property.
- **Signatures:** parameters with their types and the return type, as written in the source. Leave out `self` and `cls`.
- **Not listed:** members inherited from a library parent (pydantic's `model_dump`, for example). They are not the user's code.

Mermaid notation for members:

| Source | Diagram |
|---|---|
| public name | `+ name` |
| name starting with `_`, dunders included | `- \_name`, `- \_\_init__()` |
| attribute `rows: list[RecordT]` | `+ list[RecordT] rows` |
| method `def read(self, source: Path) -> pd.DataFrame` | `+ read(source: Path) pd.DataFrame` |
| `@staticmethod` or `@classmethod` | `$` at the end of the line |
| abstract method | `*` at the end of the line |
| generic class `RecordSet(Generic[RecordT])` | `class RecordSet~RecordT~` |

Escape a leading underscore with a backslash as shown: without it the Markdown preview reads `__init__` as bold text.

## Relationships

Only between boxes that are drawn.

- Inherits from a class in the package: `Parent <|-- Child`
- Satisfies a `Protocol` in the package, with or without inheriting from it: `Protocol <|.. Implementer`
- Has an attribute that holds another drawn type: `Owner "1" *-- "1..*" Part : attribute name`
- A `TypeVar` and its bound: `RecordT ..> Record : bound to`
- Names another drawn type in a signature as a parameter or return type, or calls it, creates it or uses its members: `User ..> Used : verb`

Label a dependency with one or two words that say what happens: `calls`, `creates`, `reads with`, `writes`.

Draw no arrow for a class or object that is only handed on as an argument. `load_bronze()` passes `CSVReader` and `BrnzRecordJournalEntries` to `BrnzLoader.load` and never touches them, so `__main__` gets no arrow to either. What matters there is the signature of `load`, which asks for an `ExternalReader` and a `RecordT`, and those arrows are drawn from the loader. Which concrete class is passed in is a detail of the call, not of the design.

A caller that reaches a class through a `Protocol` points at the protocol only. `load_bronze()` holds `BrnzLoader` in a variable typed `type[Loader]` and calls `load` on it, so `__main__` has one arrow, to `Loader`. Any loader can be chosen there; which one is a detail of the implementation, and the concrete loaders are already connected by their dashed arrow from the protocol.

Check a `Protocol` by signature. `CSVReader` does not inherit from `ExternalReader`, but it has the same `read` method and is passed where an `ExternalReader` is expected, so it gets the dashed arrow.

## Top to bottom

Put `direction TB` right after `classDiagram`. That alone is not enough: Mermaid stacks boxes along the relationship lines, and places the name written first above the name written second. So write every relationship with the upper box first:

- the caller above what it calls, starting with the entry point module at the top
- the parent above the child
- the protocol above its implementers
- the container above what it contains

Declare the boxes in the same order, entry point first and row models last.

## When to ask

Ask before writing the file whenever including, excluding or shaping something is a judgment call that these rules do not settle. Use one question that lists every doubt at once, with your recommendation for each. Typical cases:

- a new kind of thing appears that the rules do not name (a type alias, a `NewType`, a module-level object that is neither a function nor a constant)
- it is unclear whether something is the user's own code or belongs to a library (vendored or generated code, a subclass that only renames a library class)
- a module other than `__init__.py` is empty or holds only imports
- a module holds classes and also functions of its own
- a second module holds only constants, like `config.py`: the exclusion was given for that one file
- a class would need two stereotypes
- two rules pull in different directions, for example a relationship that would need a box for a library type
- the package has grown so much that one diagram may no longer be readable

Do not ask about things the rules already decide, and do not ask after the file is written.

## Output

`docs/CLASS_DIAGRAM.md` has three parts, in this order.

````markdown
# Class diagram

<Introduction: two or three sentences. What the diagram covers, how to read it
from top to bottom, and what is deliberately left out.>

```mermaid
---
title: datawarehouse
---
classDiagram
    direction TB

    <boxes, entry point first>

    <relationships, grouped, upper box first>
```

## Legend

<Bullets, see below.>
````

The legend explains the notation to someone who does not know Mermaid class diagrams. Cover only what this diagram uses:

- `+` and `-` in front of a member
- an underlined member (static or class method)
- each stereotype used: `<<module>>`, `<<protocol>>`, `<<TypeVar>>`, and `<<pydantic model>>` with what it means for the reader (pydantic validates every object of the class when it is created)
- each line style used: solid arrow with hollow head, dashed arrow with hollow head, filled diamond with its numbers, dashed arrow with a label
- **Not drawn:** `config.py`, and library and standard library types

Keep the legend to notation. Explanations of how the code works belong in the code's docstrings, not here.

Write the prose with the terms of `docs/GLOSSARY.md`, in plain sentences.

## Check before reporting

The rule that every box is complete is the one most easily broken without noticing, so verify it rather than trusting the first pass. For each file, search the source for `class `, `def `, `self.<name> =` and module-level assignments, and tick every hit off against the diagram. Then confirm:

- every class, every `TypeVar` and every module with functions of its own has a box
- every pydantic class carries `<<pydantic model>>`, including the ones that inherit from it through a class of the package
- no box and no arrow refers to a library or standard library type
- every relationship names two boxes that exist, with the upper one first
- the introduction is at the top and the legend at the bottom

Fix what is missing before reporting.
