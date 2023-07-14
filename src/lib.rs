// RUST
// folder frontend pychiquito in rust and the bindings there

// PYTHON
// in pychiquito have cargo toml to import the rust project (maybe also in a folder)
//  source code: 1. sub module, 2. cargo (there's no cargo package for chiquito tho, but you can import using URL without crate)
// subfolder in pychiquito, within which: 1. cargo.toml (import via url, or even just git clone)

use std::{collections::HashMap, fmt::Debug};
use serde::Deserialize;

use pyo3::prelude::*;
// use ir::Circuit;
// use wit_gen::TraceGenerator;
// use ast::Circuit as astCircuit;
// use compiler::{
//     Compiler,
//     cell_manager::SingleRowCellManager,
//     step_selector::SimpleStepSelectorBuilder,
// };
// use halo2_proofs::arithmetic::Field;

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

// #[pyfunction]



#[pyfunction]
fn print_step_type(step_type: HashMap<u32, &PyAny>) {
    println!("{:?}", step_type);
}

/// A Python module implemented in Rust.
#[pymodule]
fn rust_chiquito(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_function(wrap_pyfunction!(print_ast, m)?)?;
    m.add_function(wrap_pyfunction!(print_step_type, m)?)?;
    Ok(())
}

// pub mod ast;
// pub mod backend;
// pub mod compiler;
// pub mod dsl;
// pub mod ir;
// pub mod stdlib;
// mod util;
// pub mod wit_gen;

#[cfg(test)]
mod tests {
    use serde::{Deserialize, Serialize};
    use halo2_proofs::halo2curves::bn256::Fr;
    use serde_json::*;
    use std::fmt::Debug;

    #[test]
    fn test() {
        #[derive(Clone, Deserialize, Serialize)]
        #[serde(tag = "t", content = "c")]
        pub enum Expr<F> {
            Const(F),
            Sum(Vec<Expr<F>>),
            Mul(Vec<Expr<F>>),
            Neg(Box<Expr<F>>),
            Pow(Box<Expr<F>>, u32),
            // Query(Queriable<F>),
        }

        impl<F: Debug> Debug for Expr<F> {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                match self {
                    Self::Const(arg0) => {
                        let formatted = format!("{:?}", arg0);
                        if formatted.starts_with("0x") {
                            let s = format!(
                                "0x{}",
                                formatted.trim_start_matches("0x").trim_start_matches('0')
                            );
                            write!(f, "{}", s)
                        } else {
                            write!(f, "{}", formatted)
                        }
                    }
                    Self::Sum(arg0) => write!(
                        f,
                        "({})",
                        arg0.iter()
                            .map(|v| format!("{:?}", v))
                            .collect::<Vec<String>>()
                            .join(" + ")
                    ),
                    Self::Mul(arg0) => write!(
                        f,
                        "({})",
                        arg0.iter()
                            .map(|v| format!("{:?}", v))
                            .collect::<Vec<String>>()
                            .join(" * ")
                    ),
                    Self::Neg(arg0) => write!(f, "-{:?}", arg0),
                    Self::Pow(arg0, arg1) => write!(f, "({:?})^{}", arg0, arg1),
                    // Self::Query(arg0) => write!(f, "{:?}", arg0),
                    // Self::Halo2Expr(arg0) => write!(f, "halo2({:?})", arg0),
                }
            }
        }

        let json = r#"{"t": "Sum", "c": [{"t": "Const", "c": 0}, {"t": "Mul", "c": [{"t": "Const", "c": 1}, {"t": "Const", "c": 2}, {"t": "Neg", "c": {"t": "Const", "c": 3}}]}, {"t": "Pow", "c": [{"t": "Const", "c": 4}, 5]}] }"#;
        let expr: Expr::<u8> = serde_json::from_str(json).unwrap();
        // println!("{}", serde_json::to_string(&expr).unwrap());
        println!("{:?}", expr);
    }

    // #[test]
    // fn test_query() {
    //     use serde::de::{self, Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
    //     use std::fmt;
    //     use core::result::Result;
    //     use serde_json::*;
    //     use chiquito::ast::{
    //         expr::query::Queriable,
    //         InternalSignal, ForwardSignal, SharedSignal, FixedSignal,
    //     };

    //     // #[derive(Clone, Deserialize, Serialize)]
    //     // #[serde(tag = "t", content = "c")]
    //     // pub enum Queriable<F> {
    //     //     Internal(InternalSignal),
    //     //     Forward(ForwardSignal, bool),
    //     //     Shared(SharedSignal, i32),
    //     //     Fixed(FixedSignal, i32),
    //     //     StepTypeNext(StepTypeHandler),
    //     //     Halo2AdviceQuery(ImportedHalo2Advice, i32),
    //     //     Halo2FixedQuery(ImportedHalo2Fixed, i32),
    //     //     #[allow(non_camel_case_types)]
    //     //     _unaccessible(PhantomData<F>),
    //     // }

    //     let json = r#"{"t": "Sum", "c": [{"t": "Const", "c": 0}, {"t": "Mul", "c": [{"t": "Const", "c": 1}, {"t": "Const", "c": 2}, {"t": "Neg", "c": {"t": "Const", "c": 3}}]}, {"t": "Pow", "c": [{"t": "Const", "c": 4}, 5]}] }"#;
    //     let query: Queriable::<u32> = serde_json::from_str(json).unwrap();
    //     // println!("{}", serde_json::to_string(&expr).unwrap());
    //     println!("{:?}", query);
    // }

    #[test]
    fn test_custom_deserialize() {
        use serde::de::{self, Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
        use std::fmt;
        use core::result::Result;
        use serde_json::*;

        pub enum Expr<F> {
            Const(F),
            Sum(Vec<Expr<F>>),
            Mul(Vec<Expr<F>>),
            Neg(Box<Expr<F>>),
            Pow(Box<Expr<F>>, u32),
            Query(Queriable),
        }

        pub enum Queriable {
            // Internal(InternalSignal),
            // Forward(ForwardSignal, bool),
            Shared(String, i32),
            // Fixed(FixedSignal, i32),
            // StepTypeNext(StepTypeHandler),
            // Halo2AdviceQuery(ImportedHalo2Advice, i32),
            // Halo2FixedQuery(ImportedHalo2Fixed, i32),
            // #[allow(non_camel_case_types)]
            // _unaccessible(PhantomData<F>),
        }


        impl Debug for Queriable {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                write!(f, "{}", self.annotation())
            }
        }

        impl Queriable {

            pub fn annotation(&self) -> String {
                match self {
                    // Queriable::Internal(s) => s.annotation.to_string(),
                    // Queriable::Forward(s, rot) => {
                    //     if !rot {
                    //         s.annotation.to_string()
                    //     } else {
                    //         format!("next({})", s.annotation)
                    //     }
                    // }
                    Queriable::Shared(s, rot) => {
                        if *rot != 0 {
                            format!("{}(rot {})", s, rot)
                        } else {
                            s.clone()
                        }
                    }
                    // Queriable::Fixed(s, rot) => {
                    //     if *rot != 0 {
                    //         format!("{}(rot {})", s.annotation, rot)
                    //     } else {
                    //         s.annotation.to_string()
                    //     }
                    // }
                    // Queriable::StepTypeNext(s) => s.annotation.to_string(),
                    // Queriable::Halo2AdviceQuery(s, rot) => {
                    //     if *rot != 0 {
                    //         format!("{}(rot {})", s.annotation, rot)
                    //     } else {
                    //         s.annotation.to_string()
                    //     }
                    // }
                    // Queriable::Halo2FixedQuery(s, rot) => {
                    //     if *rot != 0 {
                    //         format!("{}(rot {})", s.annotation, rot)
                    //     } else {
                    //         s.annotation.to_string()
                    //     }
                    // }
                    // Queriable::_unaccessible(_) => todo!(),
                }
            }
        } 

        impl<F: Debug> Debug for Expr<F> {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                match self {
                    Self::Const(arg0) => {
                        let formatted = format!("{:?}", arg0);
                        if formatted.starts_with("0x") {
                            let s = format!(
                                "0x{}",
                                formatted.trim_start_matches("0x").trim_start_matches('0')
                            );
                            write!(f, "{}", s)
                        } else {
                            write!(f, "{}", formatted)
                        }
                    }
                    Self::Sum(arg0) => write!(
                        f,
                        "({})",
                        arg0.iter()
                            .map(|v| format!("{:?}", v))
                            .collect::<Vec<String>>()
                            .join(" + ")
                    ),
                    Self::Mul(arg0) => write!(
                        f,
                        "({})",
                        arg0.iter()
                            .map(|v| format!("{:?}", v))
                            .collect::<Vec<String>>()
                            .join(" * ")
                    ),
                    Self::Neg(arg0) => write!(f, "-{:?}", arg0),
                    Self::Pow(arg0, arg1) => write!(f, "({:?})^{}", arg0, arg1),
                    Self::Query(arg0) => write!(f, "{:?}", arg0),
                    // Self::Halo2Expr(arg0) => write!(f, "halo2({:?})", arg0),
                }
            }
        }

        struct ExprVisitor;

        impl<'de> Visitor<'de> for ExprVisitor {
            type Value = Expr<u32>;

            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
                formatter.write_str("enum Expr")
            }

            fn visit_map<A>(self, mut map: A) -> Result<Expr<u32>, A::Error>
            where
                A: MapAccess<'de>,
            {
                let key: String = map.next_key()?.ok_or_else(|| de::Error::custom("map is empty"))?;
                match key.as_str() {
                    "Const" => map.next_value().map(Expr::Const),
                    "Sum" => map.next_value().map(Expr::Sum),
                    "Mul" => map.next_value().map(Expr::Mul),
                    "Neg" => map.next_value().map(Expr::Neg),
                    "Pow" => map.next_value().map(|(expr, pow)| Expr::Pow(expr, pow)),
                    "Shared" => map.next_value().map(|(signal, rotation)| Expr::Query(Queriable::Shared(signal, rotation))),
                    _ => Err(de::Error::unknown_variant(&key, &["Const", "Sum", "Mul", "Neg", "Pow", "Shared"])),
                }
            }
        }

        impl<'de> Deserialize<'de> for Expr<u32> {
            fn deserialize<D>(deserializer: D) -> Result<Expr<u32>, D::Error>
            where
                D: Deserializer<'de>,
            {
                deserializer.deserialize_map(ExprVisitor)
            }
        }

        let json = r#"
        {
            "Sum": [
              {
                "Shared": [
                    "a",
                    2
                ]
              },
              {
                "Const": 3
              },
              {
                "Mul": [
                  {
                    "Const": 4
                  },
                  {
                    "Const": 5
                  }
                ]
              },
              {
                "Neg": {
                  "Const": 2
                }
              },
              {
                "Pow": [
                  {
                    "Const": 3
                  },
                  4
                ]
              }
            ]
          }"#;
        let expr: Expr::<u32> = serde_json::from_str(json).unwrap();
        // println!("{}", serde_json::to_string(&expr).unwrap());
        println!("{:?}", expr);

    }
}






