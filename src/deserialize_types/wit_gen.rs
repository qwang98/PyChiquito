use crate::deserialize_types::ast::{StepTypeUUID, UUID};

use std::{collections::HashMap, fmt::Debug};

#[derive(Debug, Default)]
pub struct StepInstance<F> {
    pub step_type_uuid: StepTypeUUID,
    pub assignments: HashMap<UUID, F>, // UUID instead of Queriable.
}

pub type Witness<F> = Vec<StepInstance<F>>;

#[derive(Debug, Default)]
pub struct TraceWitness<F> {
    pub step_instances: Witness<F>,
    pub height: usize,
}
