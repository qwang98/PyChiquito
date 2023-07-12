// RUST
// folder frontend pychiquito in rust and the bindings there

// PYTHON
// in pychiquito have cargo toml to import the rust project (maybe also in a folder)
//  source code: 1. sub module, 2. cargo (there's no cargo package for chiquito tho, but you can import using URL without crate)
// subfolder in pychiquito, within which: 1. cargo.toml (import via url, or even just git clone)

use std::{collections::HashMap, fmt::Debug};

use pyo3::prelude::*;
use ir::Circuit;
use wit_gen::TraceGenerator;
use ast::Circuit as astCircuit;
use compiler::{
    Compiler,
    cell_manager::SingleRowCellManager,
    step_selector::SimpleStepSelectorBuilder,
};
use halo2_proofs::arithmetic::Field;

/// Formats the sum of two numbers as string.
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

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
fn PyChiquito(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_function(wrap_pyfunction!(print_ast, m)?)?;
    m.add_function(wrap_pyfunction!(print_step_type, m)?)?;
    Ok(())
}

pub mod ast;
pub mod backend;
pub mod compiler;
pub mod dsl;
pub mod ir;
pub mod stdlib;
mod util;
pub mod wit_gen;
