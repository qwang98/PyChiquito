pub mod convert_to_chiquito;
pub mod deserialize;
pub mod deserialize_types;

use pyo3::prelude::*;
use std::collections::HashMap;

#[pyfunction]
// fn simple_compile<F: Field + Hash, TraceArgs>(
//     ast: &astCircuit<F, TraceArgs>
// ) -> (Circuit<F>, Option<TraceGenerator<F, TraceArgs>>) {
//     let compiler = Compiler::new(SingleRowCellManager {}, SimpleStepSelectorBuilder {});
//     compiler.compile(ast)
// }
fn print_ast(ast: &PyAny) {
    println!("{:?}", ast);
}

#[pyfunction]
fn print_step_type(step_type: HashMap<u32, &PyAny>) {
    println!("{:?}", step_type);
}

/// A Python module implemented in Rust.
#[pymodule]
fn rust_chiquito(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(print_ast, m)?)?;
    m.add_function(wrap_pyfunction!(print_step_type, m)?)?;
    Ok(())
}
