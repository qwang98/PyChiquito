# Quick Start
PyChiquito uses PyO3 to expose Rust APIs to Python. Please install a companion Python package `maturin` using the following command:
```
pip install maturin --user
```
If the above doesn't work, follow the guide here: https://pyo3.rs/main/getting_started#building

After `git clone`, use the following command to activate Python virtual environment, which PyO3 projects use.
```
source .env/bin/activate
```

Then, run the following to build the rust bindings.
```
maturin develop
```

Finally, run fibonacci.py file in the virtual environment using the following command:
```
python3 .env/fibonacci.py
```

You should see a print out of the parsed Rust AST circuit using the Debug trait. Run the command again if it errors out, as it's not super stable for reasons I'm still investigating.

# Technical Design
Python front end -> Python AST object -> serialize to JSON string -> pass JSON string to Rust using PyO3 -> deserialize JSON string to Rust AST defined in deserialize_types.rs -> convert to Chiquito AST
Notes:
- Likewise for `TraceWitness`.
- Types in deserialize_types.rs are almost identical to Chiquito AST. They are created so that I can implement `Deserialize` trait for them. I cannot implement `Deserialize` trait for Chiquito types, because it's not allowed to implement a trait for a type in a third file in Rust
- `Deserialize` trait is implemented in deserialize.rs
- AST defined in deserialize_types.rs is converted to Chiquito AST using functions in convert_to_chiquito.rs

# TODOs
- Python functions for creating AST in PyChiquito
  - Status: DONE and debugged with Fibo example.
- Python functions for creating WG object and FG in PyChiquito
  - Status: DONE and debugged WG with Fibo example. FG not debugged yet.
- Convert Rust module to Python library using PyO3 and Maturin
  - Status: DONE for AST.
- Design Json serialization standard in Python.
  - Status: DONE for AST and TraceWitness.
- Implement Json deserialization with Serde in Rust.
  - Status: DONE for AST and TraceWitness.
- Call Chiquito rust functions from Python with AST and WG object in Python
  - Status: DONE for AST and TraceWitness.
- Convert TraceWitness to assignment in Rust.
  - Status: Still researching due to the complexity of `AssignmentGenerator`.
- Create Rust bindings for generating and verifiying proof, using Halo2 boilerplate.
  - Status: Not started.
