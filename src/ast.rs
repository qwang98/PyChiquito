pub mod expr;

use std::{collections::HashMap, fmt::Debug, rc::Rc};

use crate::{
    dsl::StepTypeHandler,
    util::uuid,
    wit_gen::{FixedGenContext, Trace, TraceContext},
};

pub use expr::*;

use halo2_proofs::plonk::{Advice, Column as Halo2Column, ColumnType, Fixed};

/// Circuit
#[derive(Clone)]
pub struct Circuit<F, TraceArgs> {
    pub step_types: HashMap<u32, Rc<StepType<F>>>,

    pub forward_signals: Vec<ForwardSignal>,
    pub shared_signals: Vec<SharedSignal>,
    pub fixed_signals: Vec<FixedSignal>,
    pub halo2_advice: Vec<ImportedHalo2Advice>,
    pub halo2_fixed: Vec<ImportedHalo2Fixed>,
    pub exposed: Vec<ForwardSignal>,

    pub annotations: HashMap<u32, String>,

    pub trace: Option<Rc<Trace<F, TraceArgs>>>,
    pub fixed_gen: Option<Rc<FixedGen<F>>>,

    pub first_step: Option<StepTypeUUID>,
    pub last_step: Option<StepTypeUUID>,
    pub num_steps: usize,
}

impl<F: Debug, TraceArgs: Debug> Debug for Circuit<F, TraceArgs> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Circuit")
            .field("forward_signals", &self.forward_signals)
            .field("halo2_advice", &self.halo2_advice)
            .field("step_types", &self.step_types)
            .field("annotations", &self.annotations)
            .finish()
    }
}

impl<F, TraceArgs> Default for Circuit<F, TraceArgs> {
    fn default() -> Self {
        Self {
            step_types: Default::default(),
            forward_signals: Default::default(),
            shared_signals: Default::default(),
            fixed_signals: Default::default(),
            halo2_advice: Default::default(),
            halo2_fixed: Default::default(),
            exposed: Default::default(),

            num_steps: Default::default(),

            annotations: Default::default(),

            trace: None,
            fixed_gen: None,

            first_step: None,
            last_step: None,
        }
    }
}

impl<F, TraceArgs> Circuit<F, TraceArgs> {
    pub fn add_forward<N: Into<String>>(&mut self, name: N, phase: usize) -> ForwardSignal {
        let name = name.into();
        let signal = ForwardSignal::new_with_phase(phase, name.clone());

        self.forward_signals.push(signal);
        self.annotations.insert(signal.uuid(), name);

        signal
    }

    pub fn add_shared<N: Into<String>>(&mut self, name: N, phase: usize) -> SharedSignal {
        let name = name.into();
        let signal = SharedSignal::new_with_phase(phase, name.clone());

        self.shared_signals.push(signal);
        self.annotations.insert(signal.uuid(), name);

        signal
    }

    pub fn add_fixed<N: Into<String>>(&mut self, name: N) -> FixedSignal {
        let name = name.into();
        let signal = FixedSignal::new(name.clone());

        self.fixed_signals.push(signal);
        self.annotations.insert(signal.uuid(), name);

        signal
    }

    pub fn expose(&mut self, forward_signal: ForwardSignal) {
        self.exposed.push(forward_signal);
    }

    pub fn add_halo2_advice(
        &mut self,
        name: &str,
        column: Halo2Column<Advice>,
    ) -> ImportedHalo2Advice {
        let advice = ImportedHalo2Advice::new(column, name.to_string());

        self.halo2_advice.push(advice);
        self.annotations.insert(advice.uuid(), name.to_string());

        advice
    }

    pub fn add_halo2_fixed(
        &mut self,
        name: &str,
        column: Halo2Column<Fixed>,
    ) -> ImportedHalo2Fixed {
        let advice = ImportedHalo2Fixed::new(column, name.to_string());

        self.halo2_fixed.push(advice);
        self.annotations.insert(advice.uuid(), name.to_string());

        advice
    }

    pub fn add_step_type<N: Into<String>>(&mut self, handler: StepTypeHandler, name: N) {
        self.annotations.insert(handler.uuid(), name.into());
    }

    pub fn add_step_type_def(&mut self, step: StepType<F>) -> StepTypeUUID {
        let uuid = step.uuid();
        let step_rc = Rc::new(step);
        self.step_types.insert(uuid, step_rc);

        uuid
    }

    pub fn set_trace<D>(&mut self, def: D)
    where
        D: Fn(&mut TraceContext<F>, TraceArgs) + 'static,
    {
        match self.trace {
            None => {
                self.trace = Some(Rc::new(def));
            }
            Some(_) => panic!("circuit cannot have more than one trace generator"),
        }
    }

    pub fn set_fixed_gen<D>(&mut self, def: D)
    where
        D: Fn(&mut FixedGenContext<F>) + 'static,
    {
        match self.fixed_gen {
            None => self.fixed_gen = Some(Rc::new(def)),
            Some(_) => panic!("circuit cannot have more than one fixed generator"),
        }
    }

    pub fn get_step_type(&self, uuid: u32) -> Rc<StepType<F>> {
        let step_rc = self.step_types.get(&uuid).expect("step type not found");

        Rc::clone(step_rc)
    }
}

pub type FixedGen<F> = dyn Fn(&mut FixedGenContext<F>) + 'static;

pub type StepTypeUUID = u32;

/// Step
pub struct StepType<F> {
    id: StepTypeUUID,

    pub name: String,
    pub signals: Vec<InternalSignal>,
    pub constraints: Vec<Constraint<F>>,
    pub transition_constraints: Vec<TransitionConstraint<F>>,
    pub lookups: Vec<Lookup<F>>,
    pub annotations: HashMap<u32, String>,
}

impl<F: Debug> Debug for StepType<F> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("StepType")
            .field("id", &self.id)
            .field("signals", &self.signals)
            .field("constraints", &self.constraints)
            .field("transition_constraints", &self.transition_constraints)
            .finish()
    }
}

impl<F> StepType<F> {
    pub fn new(uuid: u32, name: String) -> Self {
        Self {
            id: uuid,
            name,
            signals: Default::default(),
            constraints: Default::default(),
            transition_constraints: Default::default(),
            lookups: Default::default(),
            annotations: Default::default(),
        }
    }
    pub fn uuid(&self) -> StepTypeUUID {
        self.id
    }

    pub fn add_signal<N: Into<String>>(&mut self, name: N) -> InternalSignal {
        let name = name.into();
        let signal = InternalSignal::new(name.clone());

        self.signals.push(signal);
        self.annotations.insert(signal.uuid(), name);

        signal
    }

    pub fn add_constr(&mut self, annotation: String, expr: Expr<F>) {
        let condition = Constraint { annotation, expr };

        self.constraints.push(condition)
    }

    pub fn add_transition(&mut self, annotation: String, expr: Expr<F>) {
        let condition = TransitionConstraint { annotation, expr };

        self.transition_constraints.push(condition)
    }
}

impl<F> PartialEq for StepType<F> {
    fn eq(&self, other: &Self) -> bool {
        self.id == other.id
    }
}

impl<F> Eq for StepType<F> {}

impl<F> core::hash::Hash for StepType<F> {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.id.hash(state);
    }
}

#[derive(Clone, Debug)]
/// Condition
pub struct Constraint<F> {
    pub annotation: String,
    pub expr: Expr<F>,
}

#[derive(Clone, Debug)]
/// TransitionCondition
pub struct TransitionConstraint<F> {
    pub annotation: String,
    pub expr: Expr<F>,
}

#[derive(Clone)]
pub struct Lookup<F> {
    pub annotation: String,
    pub exprs: Vec<(Constraint<F>, Expr<F>)>,
    pub enable: Option<Constraint<F>>,
}

impl<F> Default for Lookup<F> {
    fn default() -> Self {
        Lookup {
            annotation: String::new(),
            exprs: Vec::<(Constraint<F>, Expr<F>)>::new(),
            enable: None,
        }
    }
}

impl<F: Debug + Clone> Lookup<F> {
    // Function: adds (constraint, expression) to exprs if there's no enabler, OR add (enabler *
    // constraint, expression) to exprs if there's enabler Note that constraint_annotation and
    // constraint_expr are passed in as separate parameters, and then reconstructed as Constraint,
    // because dsl uses cb::Constraint while ast uses ast::Constraint
    pub fn add(
        &mut self,
        constraint_annotation: String,
        constraint_expr: Expr<F>,
        expression: Expr<F>,
    ) {
        let constraint = Constraint {
            annotation: constraint_annotation,
            expr: constraint_expr,
        };
        self.annotation += &format!("match({} => {:?}) ", &constraint.annotation, &expression); // expression: Expr<F> is formatted using the fmt method defined in the Debug trait
        match self.enable {
            None => {
                self.exprs.push((constraint, expression));
            }
            Some(_) => {
                self.exprs.push((
                    Self::multiply_constraints(self.enable.clone().unwrap(), constraint),
                    expression,
                ));
            }
        }
    }

    // Function: setup the enabler field and multiply all LHS constraints by the enabler if there's
    // no enabler, OR panic if there's an enabler already
    pub fn enable(&mut self, enable_annotation: String, enable_expr: Expr<F>) {
        let enable = Constraint {
            annotation: enable_annotation.clone(),
            expr: enable_expr,
        };
        match self.enable {
            None => {
                // Multiply all LHS constraints by the enabler
                for (constraint, _) in &mut self.exprs {
                    *constraint = Self::multiply_constraints(enable.clone(), constraint.clone());
                }
                self.enable = Some(enable);
                self.annotation = format!("if {}, ", enable_annotation) + &self.annotation;
            }
            Some(_) => panic!("Enable constraint already exists"),
        }
    }

    // Function: helper function for multiplying enabler to constraint
    fn multiply_constraints(enable: Constraint<F>, constraint: Constraint<F>) -> Constraint<F> {
        Constraint {
            annotation: constraint.annotation.clone(), /* annotation only takes the constraint's
                                                        * annotation, because enabler's
                                                        * annotation is already included in the
                                                        * enable function above in the format of
                                                        * "if {enable}" */
            expr: enable.expr * constraint.expr,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
/// ForwardSignal
pub struct ForwardSignal {
    id: u32,
    phase: usize,
    annotation: &'static str,
}

impl ForwardSignal {
    pub fn new_with_phase(phase: usize, annotation: String) -> ForwardSignal {
        ForwardSignal {
            id: uuid(),
            phase,
            annotation: Box::leak(annotation.into_boxed_str()),
        }
    }

    pub fn uuid(&self) -> u32 {
        self.id
    }

    pub fn phase(&self) -> usize {
        self.phase
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct SharedSignal {
    id: u32,
    phase: usize,
    annotation: &'static str,
}

impl SharedSignal {
    pub fn new_with_phase(phase: usize, annotation: String) -> SharedSignal {
        SharedSignal {
            id: uuid(),
            phase,
            annotation: Box::leak(annotation.into_boxed_str()),
        }
    }

    pub fn uuid(&self) -> u32 {
        self.id
    }

    pub fn phase(&self) -> usize {
        self.phase
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct FixedSignal {
    id: u32,
    annotation: &'static str,
}

impl FixedSignal {
    pub fn new(annotation: String) -> FixedSignal {
        FixedSignal {
            id: uuid(),
            annotation: Box::leak(annotation.into_boxed_str()),
        }
    }

    pub fn uuid(&self) -> u32 {
        self.id
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct InternalSignal {
    id: u32,
    annotation: &'static str,
}

impl InternalSignal {
    pub fn new(annotation: String) -> InternalSignal {
        InternalSignal {
            id: uuid(),
            annotation: Box::leak(annotation.into_boxed_str()),
        }
    }

    pub fn uuid(&self) -> u32 {
        self.id
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct ImportedHalo2Column<CT: ColumnType> {
    id: u32,
    pub column: Halo2Column<CT>,
    annotation: &'static str,
}

impl<CT: ColumnType> ImportedHalo2Column<CT> {
    pub fn new(column: Halo2Column<CT>, annotation: String) -> ImportedHalo2Column<CT> {
        ImportedHalo2Column {
            id: uuid(),
            column,
            annotation: Box::leak(annotation.into_boxed_str()),
        }
    }

    pub fn uuid(&self) -> u32 {
        self.id
    }
}

pub type ImportedHalo2Advice = ImportedHalo2Column<Advice>;
pub type ImportedHalo2Fixed = ImportedHalo2Column<Fixed>;
