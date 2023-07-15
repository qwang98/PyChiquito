// RUST
// folder frontend pychiquito in rust and the bindings there

// PYTHON
// in pychiquito have cargo toml to import the rust project (maybe also in a folder)
//  source code: 1. sub module, 2. cargo (there's no cargo package for chiquito tho, but you can import using URL without crate)
// subfolder in pychiquito, within which: 1. cargo.toml (import via url, or even just git clone)
pub mod ast;

use core::result::Result;
use pyo3::prelude::*;
use serde::de::{self, Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
use serde_json::*;
use std::{
    collections::HashMap,
    fmt::{self, Debug},
    marker::PhantomData,
};

#[derive(Clone)]
pub enum Expr<F> {
    Const(F),
    Sum(Vec<Expr<F>>),
    Mul(Vec<Expr<F>>),
    Neg(Box<Expr<F>>),
    Pow(Box<Expr<F>>, u32),
    Query(Queriable<F>),
    // Halo2Expr(Expression<F>),
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

#[derive(Clone)]
pub enum Queriable<F> {
    Internal(InternalSignal),
    Forward(ForwardSignal, bool),
    Shared(SharedSignal, i32),
    Fixed(FixedSignal, i32),
    StepTypeNext(StepTypeHandler),
    // Halo2AdviceQuery(ImportedHalo2Advice, i32),
    // Halo2FixedQuery(ImportedHalo2Fixed, i32),
    #[allow(non_camel_case_types)]
    _unaccessible(PhantomData<F>),
}

impl<F> Debug for Queriable<F> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.annotation())
    }
}

impl<F> Queriable<F> {
    pub fn annotation(&self) -> String {
        match self {
            Queriable::Internal(s) => s.annotation.to_string(),
            Queriable::Forward(s, rot) => {
                if !rot {
                    s.annotation.to_string()
                } else {
                    format!("next({})", s.annotation)
                }
            }
            Queriable::Shared(s, rot) => {
                if *rot != 0 {
                    format!("{}(rot {})", s.annotation, rot)
                } else {
                    s.annotation.to_string()
                }
            }
            Queriable::Fixed(s, rot) => {
                if *rot != 0 {
                    format!("{}(rot {})", s.annotation, rot)
                } else {
                    s.annotation.to_string()
                }
            }
            Queriable::StepTypeNext(s) => s.annotation.to_string(),
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
            Queriable::_unaccessible(_) => todo!(),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct ForwardSignal {
    id: UUID,
    phase: usize,
    annotation: &'static str,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct SharedSignal {
    id: UUID,
    phase: usize,
    annotation: &'static str,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct FixedSignal {
    id: UUID,
    annotation: &'static str,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct InternalSignal {
    id: UUID,
    annotation: &'static str,
}

pub type UUID = u128;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct StepTypeHandler {
    id: StepTypeUUID,
    pub annotation: &'static str,
}

pub type StepTypeUUID = UUID;

#[derive(Clone, Debug)]
pub struct Constraint<F> {
    pub annotation: String,
    pub expr: Expr<F>,
}

#[derive(Clone, Debug)]
pub struct TransitionConstraint<F> {
    pub annotation: String,
    pub expr: Expr<F>,
}

#[derive(Debug)]
pub struct StepType<F> {
    id: StepTypeUUID,

    pub name: String,
    pub signals: Vec<InternalSignal>,
    pub constraints: Vec<Constraint<F>>,
    pub transition_constraints: Vec<TransitionConstraint<F>>,
    // pub lookups: Vec<Lookup<F>>,
    pub annotations: HashMap<UUID, String>,
}

// #[derive(Clone)]
#[derive(Debug)]
pub struct Circuit<F> {
    // deleted TraceArgs
    pub step_types: HashMap<UUID, StepType<F>>, // removed Rc from StepType

    pub forward_signals: Vec<ForwardSignal>,
    pub shared_signals: Vec<SharedSignal>,
    pub fixed_signals: Vec<FixedSignal>,
    // pub halo2_advice: Vec<ImportedHalo2Advice>,
    // pub halo2_fixed: Vec<ImportedHalo2Fixed>,
    pub exposed: Vec<ForwardSignal>,

    pub annotations: HashMap<UUID, String>,

    // pub trace: Option<Rc<Trace<F, TraceArgs>>>,
    // pub fixed_gen: Option<Rc<FixedGen<F>>>,
    pub first_step: Option<StepTypeUUID>,
    pub last_step: Option<StepTypeUUID>,
    pub num_steps: usize,

    pub id: UUID,
}

macro_rules! impl_deserialize {
    ($name:ident, $type:ty) => {
        impl<'de> Deserialize<'de> for $type {
            fn deserialize<D>(deserializer: D) -> Result<$type, D::Error>
            where
                D: Deserializer<'de>,
            {
                deserializer.deserialize_map($name)
            }
        }
    };
}

impl_deserialize!(ExprVisitor, Expr<u32>);
impl_deserialize!(InternalSignalVisitor, InternalSignal);
impl_deserialize!(FixedSignalVisitor, FixedSignal);
impl_deserialize!(ForwardSignalVisitor, ForwardSignal);
impl_deserialize!(SharedSignalVisitor, SharedSignal);
impl_deserialize!(StepTypeHandlerVisitor, StepTypeHandler);
impl_deserialize!(ConstraintVisitor, Constraint<u32>);
impl_deserialize!(TransitionConstraintVisitor, TransitionConstraint<u32>);
impl_deserialize!(StepTypeVisitor, StepType<u32>);
impl_deserialize!(CircuitVisitor, Circuit<u32>);

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
        let key: String = map
            .next_key()?
            .ok_or_else(|| de::Error::custom("map is empty"))?;
        match key.as_str() {
            "Const" => map.next_value().map(Expr::Const),
            "Sum" => map.next_value().map(Expr::Sum),
            "Mul" => map.next_value().map(Expr::Mul),
            "Neg" => map.next_value().map(Expr::Neg),
            "Pow" => map.next_value().map(|(expr, pow)| Expr::Pow(expr, pow)),
            "Internal" => map
                .next_value()
                .map(|signal| Expr::Query(Queriable::Internal(signal))),
            "Forward" => map
                .next_value()
                .map(|(signal, rotation)| Expr::Query(Queriable::Forward(signal, rotation))),
            "Shared" => map
                .next_value()
                .map(|(signal, rotation)| Expr::Query(Queriable::Shared(signal, rotation))),
            "Fixed" => map
                .next_value()
                .map(|(signal, rotation)| Expr::Query(Queriable::Fixed(signal, rotation))),
            "StepTypeNext" => map
                .next_value()
                .map(|step_type| Expr::Query(Queriable::StepTypeNext(step_type))),
            _ => Err(de::Error::unknown_variant(
                &key,
                &[
                    "Const",
                    "Sum",
                    "Mul",
                    "Neg",
                    "Pow",
                    "Internal",
                    "Forward",
                    "Shared",
                    "Fixed",
                    "StepTypeNext",
                ],
            )),
        }
    }
}

macro_rules! impl_visitor_internal_fixed_steptypehandler {
    ($name:ident, $type:ty, $display:expr) => {
        struct $name;

        impl<'de> Visitor<'de> for $name {
            type Value = $type;

            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
                formatter.write_str($display)
            }

            fn visit_map<A>(self, mut map: A) -> Result<$type, A::Error>
            where
                A: MapAccess<'de>,
            {
                let mut id = None;
                let mut annotation = None;
                while let Some(key) = map.next_key::<String>()? {
                    match key.as_str() {
                        "id" => {
                            if id.is_some() {
                                return Err(de::Error::duplicate_field("id"));
                            }
                            id = Some(map.next_value()?);
                        }
                        "annotation" => {
                            if annotation.is_some() {
                                return Err(de::Error::duplicate_field("annotation"));
                            }
                            annotation = Some(map.next_value::<String>()?);
                        }
                        _ => return Err(de::Error::unknown_field(&key, &["id", "annotation"])),
                    }
                }
                let id = id.ok_or_else(|| de::Error::missing_field("id"))?;
                let annotation =
                    annotation.ok_or_else(|| de::Error::missing_field("annotation"))?;
                Ok(Self::Value {
                    id,
                    annotation: Box::leak(annotation.into_boxed_str()),
                })
            }
        }
    };
}

impl_visitor_internal_fixed_steptypehandler!(
    InternalSignalVisitor,
    InternalSignal,
    "struct InternalSignal"
);
impl_visitor_internal_fixed_steptypehandler!(FixedSignalVisitor, FixedSignal, "struct FixedSignal");
impl_visitor_internal_fixed_steptypehandler!(
    StepTypeHandlerVisitor,
    StepTypeHandler,
    "struct StepTypeHandler"
);

macro_rules! impl_visitor_forward_shared {
    ($name:ident, $type:ty, $display:expr) => {
        struct $name;

        impl<'de> Visitor<'de> for $name {
            type Value = $type;

            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
                formatter.write_str($display)
            }

            fn visit_map<A>(self, mut map: A) -> Result<$type, A::Error>
            where
                A: MapAccess<'de>,
            {
                let mut id = None;
                let mut phase = None;
                let mut annotation = None;
                while let Some(key) = map.next_key::<String>()? {
                    match key.as_str() {
                        "id" => {
                            if id.is_some() {
                                return Err(de::Error::duplicate_field("id"));
                            }
                            id = Some(map.next_value()?);
                        }
                        "phase" => {
                            if phase.is_some() {
                                return Err(de::Error::duplicate_field("phase"));
                            }
                            phase = Some(map.next_value()?);
                        }
                        "annotation" => {
                            if annotation.is_some() {
                                return Err(de::Error::duplicate_field("annotation"));
                            }
                            annotation = Some(map.next_value::<String>()?);
                        }
                        _ => {
                            return Err(de::Error::unknown_field(
                                &key,
                                &["id", "phase", "annotation"],
                            ))
                        }
                    }
                }
                let id = id.ok_or_else(|| de::Error::missing_field("id"))?;
                let phase = phase.ok_or_else(|| de::Error::missing_field("phase"))?;
                let annotation =
                    annotation.ok_or_else(|| de::Error::missing_field("annotation"))?;
                Ok(Self::Value {
                    id,
                    phase,
                    annotation: Box::leak(annotation.into_boxed_str()),
                })
            }
        }
    };
}

impl_visitor_forward_shared!(ForwardSignalVisitor, ForwardSignal, "struct ForwardSignal");
impl_visitor_forward_shared!(SharedSignalVisitor, SharedSignal, "struct SharedSignal");

macro_rules! impl_visitor_constraint_transition {
    ($name:ident, $type:ty, $display:expr) => {
        struct $name;

        impl<'de> Visitor<'de> for $name {
            type Value = $type;

            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
                formatter.write_str($display)
            }

            fn visit_map<A>(self, mut map: A) -> Result<$type, A::Error>
            where
                A: MapAccess<'de>,
            {
                let mut annotation = None;
                let mut expr = None;
                while let Some(key) = map.next_key::<String>()? {
                    match key.as_str() {
                        "annotation" => {
                            if annotation.is_some() {
                                return Err(de::Error::duplicate_field("annotation"));
                            }
                            annotation = Some(map.next_value::<String>()?);
                        }
                        "expr" => {
                            if expr.is_some() {
                                return Err(de::Error::duplicate_field("expr"));
                            }
                            expr = Some(map.next_value::<Expr<u32>>()?);
                        }
                        _ => return Err(de::Error::unknown_field(&key, &["annotation", "expr"])),
                    }
                }
                let annotation =
                    annotation.ok_or_else(|| de::Error::missing_field("annotation"))?;
                let expr = expr.ok_or_else(|| de::Error::missing_field("expr"))?;
                Ok(Self::Value { annotation, expr })
            }
        }
    };
}

impl_visitor_constraint_transition!(ConstraintVisitor, Constraint<u32>, "struct Constraint");
impl_visitor_constraint_transition!(
    TransitionConstraintVisitor,
    TransitionConstraint<u32>,
    "struct TransitionConstraint"
);

struct StepTypeVisitor;

impl<'de> Visitor<'de> for StepTypeVisitor {
    type Value = StepType<u32>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("enum StepType")
    }

    fn visit_map<A>(self, mut map: A) -> Result<StepType<u32>, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut id = None;
        let mut name = None;
        let mut signals = None;
        let mut constraints = None;
        let mut transition_constraints = None;
        let mut annotations = None;

        while let Some(key) = map.next_key::<String>()? {
            match key.as_str() {
                "id" => {
                    if id.is_some() {
                        return Err(de::Error::duplicate_field("id"));
                    }
                    id = Some(map.next_value()?);
                }
                "name" => {
                    if name.is_some() {
                        return Err(de::Error::duplicate_field("name"));
                    }
                    name = Some(map.next_value::<String>()?);
                }
                "signals" => {
                    if signals.is_some() {
                        return Err(de::Error::duplicate_field("signals"));
                    }
                    signals = Some(map.next_value::<Vec<InternalSignal>>()?);
                }
                "constraints" => {
                    if constraints.is_some() {
                        return Err(de::Error::duplicate_field("constraints"));
                    }
                    constraints = Some(map.next_value::<Vec<Constraint<u32>>>()?);
                }
                "transition_constraints" => {
                    if transition_constraints.is_some() {
                        return Err(de::Error::duplicate_field("transition_constraints"));
                    }
                    transition_constraints =
                        Some(map.next_value::<Vec<TransitionConstraint<u32>>>()?);
                }
                "annotations" => {
                    if annotations.is_some() {
                        return Err(de::Error::duplicate_field("annotations"));
                    }
                    annotations = Some(map.next_value::<HashMap<UUID, String>>()?);
                }
                _ => {
                    return Err(de::Error::unknown_field(
                        &key,
                        &[
                            "id",
                            "name",
                            "signals",
                            "constraints",
                            "transition_constraints",
                            "annotations",
                        ],
                    ))
                }
            }
        }
        let id = id.ok_or_else(|| de::Error::missing_field("id"))?;
        let name = name.ok_or_else(|| de::Error::missing_field("name"))?;
        let signals = signals.ok_or_else(|| de::Error::missing_field("signals"))?;
        let constraints = constraints.ok_or_else(|| de::Error::missing_field("constraints"))?;
        let transition_constraints = transition_constraints
            .ok_or_else(|| de::Error::missing_field("transition_constraints"))?;
        let annotations = annotations.ok_or_else(|| de::Error::missing_field("annotations"))?;
        Ok(Self::Value {
            id,
            name,
            signals,
            constraints,
            transition_constraints,
            annotations,
        })
    }
}

struct CircuitVisitor;

impl<'de> Visitor<'de> for CircuitVisitor {
    type Value = Circuit<u32>;

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("enum Cricuit")
    }

    fn visit_map<A>(self, mut map: A) -> Result<Circuit<u32>, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut step_types = None;
        let mut forward_signals = None;
        let mut shared_signals = None;
        let mut fixed_signals = None;
        let mut exposed = None;
        let mut annotations = None;
        let mut first_step = None;
        let mut last_step = None;
        let mut num_steps = None;
        let mut id = None;

        while let Some(key) = map.next_key::<String>()? {
            match key.as_str() {
                "step_types" => {
                    if step_types.is_some() {
                        return Err(de::Error::duplicate_field("step_types"));
                    }
                    step_types = Some(map.next_value::<HashMap<UUID, StepType<u32>>>()?);
                }
                "forward_signals" => {
                    if forward_signals.is_some() {
                        return Err(de::Error::duplicate_field("forward_signals"));
                    }
                    forward_signals = Some(map.next_value::<Vec<ForwardSignal>>()?);
                }
                "shared_signals" => {
                    if shared_signals.is_some() {
                        return Err(de::Error::duplicate_field("shared_signals"));
                    }
                    shared_signals = Some(map.next_value::<Vec<SharedSignal>>()?);
                }
                "fixed_signals" => {
                    if fixed_signals.is_some() {
                        return Err(de::Error::duplicate_field("fixed_signals"));
                    }
                    fixed_signals = Some(map.next_value::<Vec<FixedSignal>>()?);
                }
                "exposed" => {
                    if exposed.is_some() {
                        return Err(de::Error::duplicate_field("exposed"));
                    }
                    exposed = Some(map.next_value::<Vec<ForwardSignal>>()?);
                }
                "annotations" => {
                    if annotations.is_some() {
                        return Err(de::Error::duplicate_field("annotations"));
                    }
                    annotations = Some(map.next_value::<HashMap<UUID, String>>()?);
                }
                "first_step" => {
                    if first_step.is_some() {
                        return Err(de::Error::duplicate_field("first_step"));
                    }
                    first_step = Some(map.next_value::<Option<StepTypeUUID>>()?);
                }
                "last_step" => {
                    if last_step.is_some() {
                        return Err(de::Error::duplicate_field("last_step"));
                    }
                    last_step = Some(map.next_value::<Option<StepTypeUUID>>()?);
                }
                "num_steps" => {
                    if num_steps.is_some() {
                        return Err(de::Error::duplicate_field("num_steps"));
                    }
                    num_steps = Some(map.next_value::<usize>()?);
                }
                "id" => {
                    if id.is_some() {
                        return Err(de::Error::duplicate_field("id"));
                    }
                    id = Some(map.next_value()?);
                }
                _ => {
                    return Err(de::Error::unknown_field(
                        &key,
                        &[
                            "step_types",
                            "forward_signals",
                            "shared_signals",
                            "fixed_signals",
                            "exposed",
                            "annotations",
                            "first_step",
                            "last_step",
                            "num_steps",
                            "id",
                        ],
                    ))
                }
            }
        }
        let step_types = step_types.ok_or_else(|| de::Error::missing_field("step_types"))?;
        let forward_signals =
            forward_signals.ok_or_else(|| de::Error::missing_field("forward_signals"))?;
        let shared_signals =
            shared_signals.ok_or_else(|| de::Error::missing_field("shared_signals"))?;
        let fixed_signals =
            fixed_signals.ok_or_else(|| de::Error::missing_field("fixed_signals"))?;
        let exposed = exposed.ok_or_else(|| de::Error::missing_field("exposed"))?;
        let annotations = annotations.ok_or_else(|| de::Error::missing_field("annotations"))?;
        let first_step = first_step.ok_or_else(|| de::Error::missing_field("first_step"))?;
        let last_step = last_step.ok_or_else(|| de::Error::missing_field("last_step"))?;
        let num_steps = num_steps.ok_or_else(|| de::Error::missing_field("num_steps"))?;
        let id = id.ok_or_else(|| de::Error::missing_field("id"))?;

        Ok(Circuit {
            step_types,
            forward_signals,
            shared_signals,
            fixed_signals,
            exposed,
            annotations,
            first_step,
            last_step,
            num_steps,
            id,
        })
    }
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
fn rust_chiquito(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(print_ast, m)?)?;
    m.add_function(wrap_pyfunction!(print_step_type, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use halo2_proofs::{halo2curves::bn256::Fr, plonk::Fixed};
    use serde::{Deserialize, Serialize};
    use serde_json::*;
    use std::{collections::HashMap, fmt::Debug, rc::Rc};

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
        let expr: Expr<u8> = serde_json::from_str(json).unwrap();
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
    fn test_convert_same_type() {
        use chiquito::ast::expr::Expr as cExpr;

        #[derive(Clone)]
        pub enum Expr<F> {
            Const(F),
            Sum(Vec<Expr<F>>),
            Mul(Vec<Expr<F>>),
            Neg(Box<Expr<F>>),
            Pow(Box<Expr<F>>, u32),
            // Query(Queriable<F>),
            // Halo2Expr(Expression<F>),
        }

        impl<F> Expr<F> {
            fn to_cexpr(expr: Expr<F>) -> cExpr<F> {
                match expr {
                    Self::Const(arg0) => cExpr::Const(arg0),
                    Self::Sum(arg0) => cExpr::Sum(arg0.into_iter().map(Self::to_cexpr).collect()),
                    Self::Mul(arg0) => cExpr::Mul(arg0.into_iter().map(Self::to_cexpr).collect()),
                    Self::Neg(arg0) => cExpr::Neg(Box::new(Self::to_cexpr(*arg0))),
                    Self::Pow(arg0, arg1) => {
                        cExpr::Pow(Box::new(Self::to_cexpr(*arg0)), arg1)
                    }
                    // Self::Query(arg0) => cExpr::Query(arg0),
                    // Self::Halo2Expr(arg0) => cExpr::Halo2Expr(arg0),
                }
            }
        }

        let expr: Expr<u32> = Expr::Sum(vec![
            Expr::Const(1),
            Expr::Mul(vec![
                Expr::Const(2),
                Expr::Const(3),
                Expr::Neg(Box::new(Expr::Const(4))),
            ]),
            Expr::Pow(Box::new(Expr::Const(5)), 6),
        ]);
        let cexpr = Expr::<u32>::to_cexpr(expr);
        println!("{:?}", cexpr);
    }

    #[test]
    fn test_custom_deserialize() {
        use crate::{Circuit, Constraint, Expr, StepType, TransitionConstraint};
        use core::result::Result;
        use pyo3::prelude::*;
        use serde::de::{self, Deserialize, Deserializer, MapAccess, SeqAccess, Visitor};
        use serde_json::*;
        use std::{
            collections::HashMap,
            fmt::{self, Debug},
            marker::PhantomData,
        };

        let json_circuit = r#"
        {
        "step_types": {
            "0": {
                "id": 3,
                "name": "fibo step",
                "signals": [
                    {
                        "id": 4,
                        "annotation": "a"
                    },
                    {
                        "id": 5,
                        "annotation": "b"
                    }
                ],
                "constraints": [
                    {
                        "annotation": "constraint 1",
                        "expr": 
                        {
                            "Sum": [
                                {
                                "Internal": {
                                    "id": 27,
                                    "annotation": "a"
                                }
                                },
                                {
                                "Fixed": [
                                    {
                                        "id": 28,
                                        "annotation": "b"
                                    },
                                    1
                                ]
                                },
                                {
                                "Shared": [
                                    {
                                        "id": 29,
                                        "phase": 1,
                                        "annotation": "c"
                                    },
                                    2
                                ]
                                },
                                {
                                "Forward": [
                                    {
                                        "id": 30,
                                        "phase": 2,
                                        "annotation": "d"
                                    },
                                    true
                                ]
                                },
                                {
                                "StepTypeNext": {
                                    "id": 31,
                                    "annotation": "e"
                                }
                                },
                                {
                                "Const": 3
                                },
                                {
                                "Pow": [
                                    {
                                        "Internal": {
                                            "id": 32,
                                            "annotation": "f"
                                        }
                                    },
                                    4
                                ]
                                },
                                {
                                "Mul": [
                                    {
                                        "Fixed": [{
                                            "id": 33,
                                            "annotation": "g"
                                        }, 2]
                                    },
                                    {
                                        "Internal": {
                                            "id": 34,
                                            "annotation": "h"
                                        }
                                    }
                                ]
                                },
                                {
                                "Neg": {
                                    "Internal": {
                                        "id": 35,
                                        "annotation": "i"
                                    }
                                }
                                }
                            ]
                        }
                    }, 
                    {
                        "annotation": "constraint 2",
                        "expr": 
                        {
                            "Mul": [
                                {
                                "Internal": {
                                    "id": 27,
                                    "annotation": "a"
                                }
                                },
                                {
                                "Fixed": [
                                    {
                                        "id": 28,
                                        "annotation": "b"
                                    },
                                    1
                                ]
                                }
                            ]
                        }
                    }
                ],
                "transition_constraints": [
                    {
                        "annotation": "transition constraint 1",
                        "expr": 
                        {
                            "Sum": [
                                {
                                "Internal": {
                                    "id": 27,
                                    "annotation": "a"
                                }
                                },
                                {
                                "Fixed": [
                                    {
                                        "id": 28,
                                        "annotation": "b"
                                    },
                                    1
                                ]
                                },
                                {
                                "Shared": [
                                    {
                                        "id": 29,
                                        "phase": 1,
                                        "annotation": "c"
                                    },
                                    2
                                ]
                                },
                                {
                                "Forward": [
                                    {
                                        "id": 30,
                                        "phase": 2,
                                        "annotation": "d"
                                    },
                                    true
                                ]
                                },
                                {
                                "StepTypeNext": {
                                    "id": 31,
                                    "annotation": "e"
                                }
                                },
                                {
                                "Const": 3
                                },
                                {
                                "Neg": {
                                    "Internal": {
                                        "id": 35,
                                        "annotation": "i"
                                    }
                                }
                                }
                            ]
                        }
                    }, 
                    {
                        "annotation": "transition constraint 2",
                        "expr": 
                        {
                            "Mul": [
                                {
                                "Internal": {
                                    "id": 27,
                                    "annotation": "a"
                                }
                                },
                                {
                                "Fixed": [
                                    {
                                        "id": 28,
                                        "annotation": "b"
                                    },
                                    1
                                ]
                                }
                            ]
                        }
                    }
                ],
                "annotations": {
                    "40": "test annotation 1",
                    "41": "test annotation 2"
                }
            }, 
            "1": {
                "id": 3,
                "name": "fibo step",
                "signals": [
                    {
                        "id": 4,
                        "annotation": "a"
                    },
                    {
                        "id": 5,
                        "annotation": "b"
                    }
                ],
                "constraints": [
                    {
                        "annotation": "constraint 1",
                        "expr": 
                        {
                            "Sum": [
                                {
                                "Internal": {
                                    "id": 27,
                                    "annotation": "a"
                                }
                                },
                                {
                                "Fixed": [
                                    {
                                        "id": 28,
                                        "annotation": "b"
                                    },
                                    1
                                ]
                                },
                                {
                                "Shared": [
                                    {
                                        "id": 29,
                                        "phase": 1,
                                        "annotation": "c"
                                    },
                                    2
                                ]
                                },
                                {
                                "Forward": [
                                    {
                                        "id": 30,
                                        "phase": 2,
                                        "annotation": "d"
                                    },
                                    true
                                ]
                                },
                                {
                                "StepTypeNext": {
                                    "id": 31,
                                    "annotation": "e"
                                }
                                },
                                {
                                "Const": 3
                                },
                                {
                                "Pow": [
                                    {
                                        "Internal": {
                                            "id": 32,
                                            "annotation": "f"
                                        }
                                    },
                                    4
                                ]
                                },
                                {
                                "Mul": [
                                    {
                                        "Fixed": [{
                                            "id": 33,
                                            "annotation": "g"
                                        }, 2]
                                    },
                                    {
                                        "Internal": {
                                            "id": 34,
                                            "annotation": "h"
                                        }
                                    }
                                ]
                                },
                                {
                                "Neg": {
                                    "Internal": {
                                        "id": 35,
                                        "annotation": "i"
                                    }
                                }
                                }
                            ]
                        }
                    }, 
                    {
                        "annotation": "constraint 2",
                        "expr": 
                        {
                            "Mul": [
                                {
                                "Internal": {
                                    "id": 27,
                                    "annotation": "a"
                                }
                                },
                                {
                                "Fixed": [
                                    {
                                        "id": 28,
                                        "annotation": "b"
                                    },
                                    1
                                ]
                                }
                            ]
                        }
                    }
                ],
                "transition_constraints": [
                    {
                        "annotation": "transition constraint 1",
                        "expr": 
                        {
                            "Sum": [
                                {
                                "Internal": {
                                    "id": 27,
                                    "annotation": "a"
                                }
                                },
                                {
                                "Fixed": [
                                    {
                                        "id": 28,
                                        "annotation": "b"
                                    },
                                    1
                                ]
                                },
                                {
                                "Shared": [
                                    {
                                        "id": 29,
                                        "phase": 1,
                                        "annotation": "c"
                                    },
                                    2
                                ]
                                },
                                {
                                "Forward": [
                                    {
                                        "id": 30,
                                        "phase": 2,
                                        "annotation": "d"
                                    },
                                    true
                                ]
                                },
                                {
                                "StepTypeNext": {
                                    "id": 31,
                                    "annotation": "e"
                                }
                                },
                                {
                                "Const": 3
                                },
                                {
                                "Neg": {
                                    "Internal": {
                                        "id": 35,
                                        "annotation": "i"
                                    }
                                }
                                }
                            ]
                        }
                    }, 
                    {
                        "annotation": "transition constraint 2",
                        "expr": 
                        {
                            "Mul": [
                                {
                                "Internal": {
                                    "id": 27,
                                    "annotation": "a"
                                }
                                },
                                {
                                "Fixed": [
                                    {
                                        "id": 28,
                                        "annotation": "b"
                                    },
                                    1
                                ]
                                }
                            ]
                        }
                    }
                ],
                "annotations": {
                    "40": "test annotation 1",
                    "41": "test annotation 2"
                }
            }
        },

        "forward_signals": [
            {
                "id": 80,
                "phase": 1,
                "annotation": "l"
            },
            {
                "id": 81,
                "phase": 2,
                "annotation": "m"
            }
        ],
        "shared_signals": [
            {
                "id": 82,
                "phase": 1,
                "annotation": "n"
            },
            {
                "id": 83,
                "phase": 2,
                "annotation": "o"
            }
        ],
        "fixed_signals": [
            {
                "id": 84,
                "annotation": "p"
            },
            {
                "id": 85,
                "annotation": "q"
            }
        ],
        "exposed": [
            {
                "id": 86,
                "phase": 1,
                "annotation": "r"
            },
            {
                "id": 87,
                "phase": 2,
                "annotation": "s"
            }
        ],
        "annotations": {
            "88": "test annotation 3",
            "89": "test annotation 4"
        },
        "first_step": null,
        "last_step": 21,
        "num_steps": 10,
        "id": 100

        }
        "#;

        let json_circuit: Circuit<u32> = serde_json::from_str(json_circuit).unwrap();
        println!("{:?}", json_circuit);

        let json_steptype = r#"
        {
            "id": 3,
            "name": "fibo step",
            "signals": [
                {
                    "id": 4,
                    "annotation": "a"
                },
                {
                    "id": 5,
                    "annotation": "b"
                }
            ],
            "constraints": [
                {
                    "annotation": "constraint 1",
                    "expr": 
                    {
                        "Sum": [
                            {
                            "Internal": {
                                "id": 27,
                                "annotation": "a"
                            }
                            },
                            {
                            "Fixed": [
                                {
                                    "id": 28,
                                    "annotation": "b"
                                },
                                1
                            ]
                            },
                            {
                            "Shared": [
                                {
                                    "id": 29,
                                    "phase": 1,
                                    "annotation": "c"
                                },
                                2
                            ]
                            },
                            {
                            "Forward": [
                                {
                                    "id": 30,
                                    "phase": 2,
                                    "annotation": "d"
                                },
                                true
                            ]
                            },
                            {
                            "StepTypeNext": {
                                "id": 31,
                                "annotation": "e"
                            }
                            },
                            {
                            "Const": 3
                            },
                            {
                            "Pow": [
                                {
                                    "Internal": {
                                        "id": 32,
                                        "annotation": "f"
                                    }
                                },
                                4
                            ]
                            },
                            {
                            "Mul": [
                                {
                                    "Fixed": [{
                                        "id": 33,
                                        "annotation": "g"
                                    }, 2]
                                },
                                {
                                    "Internal": {
                                        "id": 34,
                                        "annotation": "h"
                                    }
                                }
                            ]
                            },
                            {
                            "Neg": {
                                "Internal": {
                                    "id": 35,
                                    "annotation": "i"
                                }
                            }
                            }
                        ]
                    }
                }, 
                {
                    "annotation": "constraint 2",
                    "expr": 
                    {
                        "Mul": [
                            {
                            "Internal": {
                                "id": 27,
                                "annotation": "a"
                            }
                            },
                            {
                            "Fixed": [
                                {
                                    "id": 28,
                                    "annotation": "b"
                                },
                                1
                            ]
                            }
                        ]
                    }
                }
            ],
            "transition_constraints": [
                {
                    "annotation": "transition constraint 1",
                    "expr": 
                    {
                        "Sum": [
                            {
                            "Internal": {
                                "id": 27,
                                "annotation": "a"
                            }
                            },
                            {
                            "Fixed": [
                                {
                                    "id": 28,
                                    "annotation": "b"
                                },
                                1
                            ]
                            },
                            {
                            "Shared": [
                                {
                                    "id": 29,
                                    "phase": 1,
                                    "annotation": "c"
                                },
                                2
                            ]
                            },
                            {
                            "Forward": [
                                {
                                    "id": 30,
                                    "phase": 2,
                                    "annotation": "d"
                                },
                                true
                            ]
                            },
                            {
                            "StepTypeNext": {
                                "id": 31,
                                "annotation": "e"
                            }
                            },
                            {
                            "Const": 3
                            },
                            {
                            "Neg": {
                                "Internal": {
                                    "id": 35,
                                    "annotation": "i"
                                }
                            }
                            }
                        ]
                    }
                }, 
                {
                    "annotation": "transition constraint 2",
                    "expr": 
                    {
                        "Mul": [
                            {
                            "Internal": {
                                "id": 27,
                                "annotation": "a"
                            }
                            },
                            {
                            "Fixed": [
                                {
                                    "id": 28,
                                    "annotation": "b"
                                },
                                1
                            ]
                            }
                        ]
                    }
                }
            ],
            "annotations": {
                "40": "test annotation 1",
                "41": "test annotation 2"
            }
        }
        "#;
        let json_steptype: StepType<u32> = serde_json::from_str(json_steptype).unwrap();
        println!("{:?}", json_steptype);

        let json_constraint = r#"
        {"annotation": "constraint",
        "expr": 
        {
            "Sum": [
                {
                "Internal": {
                    "id": 27,
                    "annotation": "a"
                }
                },
                {
                "Fixed": [
                    {
                        "id": 28,
                        "annotation": "b"
                    },
                    1
                ]
                },
                {
                "Shared": [
                    {
                        "id": 29,
                        "phase": 1,
                        "annotation": "c"
                    },
                    2
                ]
                },
                {
                "Forward": [
                    {
                        "id": 30,
                        "phase": 2,
                        "annotation": "d"
                    },
                    true
                ]
                },
                {
                "StepTypeNext": {
                    "id": 31,
                    "annotation": "e"
                }
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
            }
        }"#;
        let constraint: Constraint<u32> = serde_json::from_str(json_constraint).unwrap();
        println!("{:?}", constraint);
        let transition_constraint: TransitionConstraint<u32> =
            serde_json::from_str(json_constraint).unwrap();
        println!("{:?}", transition_constraint);

        let json_expr = r#"
        {
            "Sum": [
                {
                "Internal": {
                    "id": 27,
                    "annotation": "a"
                }
                },
                {
                "Fixed": [
                    {
                        "id": 28,
                        "annotation": "b"
                    },
                    1
                ]
                },
                {
                "Shared": [
                    {
                        "id": 29,
                        "phase": 1,
                        "annotation": "c"
                    },
                    2
                ]
                },
                {
                "Forward": [
                    {
                        "id": 30,
                        "phase": 2,
                        "annotation": "d"
                    },
                    true
                ]
                },
                {
                "StepTypeNext": {
                    "id": 31,
                    "annotation": "e"
                }
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
        let expr: Expr<u32> = serde_json::from_str(json_expr).unwrap();
        // println!("{}", serde_json::to_string(&expr).unwrap());
        println!("{:?}", expr);
    }
}
