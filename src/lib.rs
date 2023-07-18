use chiquito::ast::Circuit;
use pyo3::{prelude::*, types::PyString};

#[pyfunction]
fn convert_and_print_ast(json: &PyString) {
    let circuit: Circuit<u32, ()> =
        serde_json::from_str(json.to_str().expect("PyString convertion failed."))
            .expect("Json deserialization to Circuit failed.");
    println!("{:?}", circuit);
}

#[pymodule]
fn rust_chiquito(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(convert_and_print_ast, m)?)?;
    Ok(())
}
