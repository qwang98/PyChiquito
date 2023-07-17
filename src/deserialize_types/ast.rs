pub mod expr;

use expr::*;

use std::{collections::HashMap, fmt::Debug};

pub type StepTypeUUID = UUID;
pub type UUID = u128;

#[derive(Debug)]
pub struct Circuit<F> {
    // Deleted TraceArgs
    pub step_types: HashMap<UUID, StepType<F>>, // Removed Rc from StepType

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

#[derive(Clone, Debug)]
pub struct StepType<F> {
    pub id: StepTypeUUID,

    pub name: String,
    pub signals: Vec<InternalSignal>,
    pub constraints: Vec<Constraint<F>>,
    pub transition_constraints: Vec<TransitionConstraint<F>>,
    // pub lookups: Vec<Lookup<F>>,
    pub annotations: HashMap<UUID, String>,
}

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

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct ForwardSignal {
    pub id: UUID,
    pub phase: usize,
    pub annotation: &'static str,
}

impl ForwardSignal {
    pub fn uuid(&self) -> UUID {
        self.id
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct SharedSignal {
    pub id: UUID,
    pub phase: usize,
    pub annotation: &'static str,
}

impl SharedSignal {
    pub fn uuid(&self) -> UUID {
        self.id
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct FixedSignal {
    pub id: UUID,
    pub annotation: &'static str,
}

impl FixedSignal {
    pub fn uuid(&self) -> UUID {
        self.id
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct InternalSignal {
    pub id: UUID,
    pub annotation: &'static str,
}

impl InternalSignal {
    pub fn uuid(&self) -> UUID {
        self.id
    }
}
