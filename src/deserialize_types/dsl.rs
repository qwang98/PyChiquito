use crate::deserialize_types::ast::{StepTypeUUID, UUID};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct StepTypeHandler {
    pub id: StepTypeUUID,
    pub annotation: &'static str,
}

impl StepTypeHandler {
    pub fn uuid(&self) -> UUID {
        self.id
    }
}
