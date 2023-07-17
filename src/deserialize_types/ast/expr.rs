pub mod query;

use query::*;

use std::fmt::Debug;

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
