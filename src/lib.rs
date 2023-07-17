pub mod convert_to_chiquito;
pub mod deserialize;
pub mod deserialize_types;

use deserialize_types::ast::Circuit;
use convert_to_chiquito::to_chiquito_ast;

use pyo3::{prelude::*, types::PyString};
use chiquito::ast::Circuit as cCircuit;


#[pyfunction]
fn print_ast(json: &PyString) {
    let deserialized_ast: Circuit<u32> = serde_json::from_str(json.to_str().expect("PyString convertion failed.")).expect("Json deserialization to Circuit failed.");
    let chiquito_ast: cCircuit<u32, ()> = to_chiquito_ast::<()>(deserialized_ast);
    println!("{:?}", chiquito_ast);
}

#[pymodule]
fn rust_chiquito(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(print_ast, m)?)?;
    Ok(())
}
