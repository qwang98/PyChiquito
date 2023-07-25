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

Finally, run fibonacci.py file using the following command:
```
python3 pychiquito/fibonacci.py
```

You should see a print out of the parsed Rust AST circuit and TraceWitness. All Halo2 and Chiquito Debug messages for generating and verifying proof should also appear in the terminal.

# Technical Design
Python front end -> Python AST object/TraceWitness -> serialize to JSON string -> pass JSON string to Rust using PyO3 -> deserialize JSON string to Chiquito AST/TraceWitness -> store AST in Rust HashMap<UUID, AST> -> pass back UUID to Python -> generate and verify proof from Python with AST UUID and TraceWitness JSON
## Notes:
- Rust bindings to expose to Python are in lib.rs
- Boilerplate functions and `Deserialize` trait implementations for Rust Chiquito AST, TraceWitness, and their sub types are in frontend.rs of Rust Chiquito: https://github.com/privacy-scaling-explorations/chiquito
