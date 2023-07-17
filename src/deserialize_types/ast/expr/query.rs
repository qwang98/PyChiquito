use crate::deserialize_types::{
    ast::{FixedSignal, ForwardSignal, InternalSignal, SharedSignal, UUID},
    dsl::StepTypeHandler,
};

use std::{fmt::Debug, marker::PhantomData};

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
            Queriable::_unaccessible(_) => todo!(),
        }
    }

    pub fn uuid(&self) -> UUID {
        match self {
            Queriable::Internal(s) => s.uuid(),
            Queriable::Forward(s, _) => s.uuid(),
            Queriable::Shared(s, _) => s.uuid(),
            Queriable::Fixed(s, _) => s.uuid(),
            Queriable::StepTypeNext(s) => s.uuid(),
            // Queriable::Halo2AdviceQuery(s, _) => s.uuid(),
            // Queriable::Halo2FixedQuery(s, _) => s.uuid(),
            _ => panic!("Invalid Queriable enum type."),
        }
    }
}
