use chiquito::{ast::Circuit, wit_gen::TraceWitness};
use halo2_proofs::halo2curves::bn256::Fr;
use pyo3::{prelude::*, types::PyString};

#[pyfunction]
fn convert_and_print_ast(json: &PyString) {
    let circuit: Circuit<Fr, ()> =
        serde_json::from_str(json.to_str().expect("PyString convertion failed."))
            .expect("Json deserialization to Circuit failed.");
    println!("{:?}", circuit);
}

#[pyfunction]
fn convert_and_print_trace_witness(json: &PyString) {
    let trace_witness: TraceWitness<Fr> =
        serde_json::from_str(json.to_str().expect("PyString convertion failed."))
            .expect("Json deserialization to TraceWitness failed.");
    println!("{:?}", trace_witness);
}

#[pymodule]
fn rust_chiquito(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(convert_and_print_ast, m)?)?;
    m.add_function(wrap_pyfunction!(convert_and_print_trace_witness, m)?)?;
    Ok(())
}
