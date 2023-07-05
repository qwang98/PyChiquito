from typing import TypeVar, Generic, List, Dict, List
from chiquito_ast import InternalSignal, ForwardSignal, SharedSignal, FixedSignal
from expr import Expr
from query import Queriable

class Constraint:
    def __init__(self, annotation: str, expr: Expr, typing: str):
        self.annotation = annotation
        self.expr = expr
        if typing not in ["Unknown", "Boolean", "AntiBooly"]:
            raise ValueError("Invalid typing for Constraint.")
        self.typing = typing
    
    def from_expr(expr: Expr) -> Constraint: # `from` is a reserved keyword in Python
        let annotation = 

impl<F: Debug> From<Expr<F>> for Constraint<F> {
    fn from(expr: Expr<F>) -> Self {
        let annotation = format!("{:?}", &expr);
        match expr {
            Expr::Query(Queriable::StepTypeNext(_)) => Self {
                expr,
                annotation,
                typing: Typing::Boolean,
            },
            _ => Self {
                expr,
                annotation,
                typing: Typing::Unknown,
            },
        }
    }
}

impl<F> From<Queriable<F>> for Constraint<F> {
    fn from(query: Queriable<F>) -> Self {
        match query {
            Queriable::StepTypeNext(_) => {
                annotate(query.annotation(), Expr::Query(query), Typing::Boolean)
            }
            _ => annotate(query.annotation(), Expr::Query(query), Typing::Unknown),
        }
    }
}

impl<F: Field + From<u64> + Debug> From<i32> for Constraint<F> {
    fn from(v: i32) -> Self {
        v.expr().into()
    }
}

macro_rules! impl_cb_like {
    ($type:ty) => {
        impl<F: From<u64> + Debug> From<$type> for Constraint<F> {
            #[inline]
            fn from(value: $type) -> Self {
                Expr::Const(F::from(value as u64)).into()
            }
        }
    };
}

impl_cb_like!(bool);
impl_cb_like!(u8);
impl_cb_like!(u32);
impl_cb_like!(u64);
impl_cb_like!(usize);

impl<F> Debug for Constraint<F> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.annotation)
    }
}

/// Takes an iterator of input constraints and returns a new constraint representing the logical AND
/// of all input constraints. In practice, multiplies all input constraints together, i.e. A * B * C
/// * … = 0.
pub fn and<F: From<u64>, E: Into<Constraint<F>>, I: IntoIterator<Item = E>>(
    inputs: I,
) -> Constraint<F> {
    let mut annotations: Vec<String> = vec![];
    let mut expr: Expr<F> = 1u64.expr();

    for constraint in inputs.into_iter() {
        let constraint = constraint.into();
        match constraint.typing {
            Typing::Boolean | Typing::Unknown => {
                annotations.push(constraint.annotation);
                expr = expr * constraint.expr;
            }
            Typing::AntiBooly => panic!(
                "Expected Boolean or Unknown constraint, got AntiBooly (constraint: {})",
                constraint.annotation
            ),
        }
    }

    Constraint {
        annotation: format!("({})", annotations.join(" AND ")),
        expr,
        typing: Typing::Boolean,
    }
}

/// Takes an iterator of input constraints and returns a new constraint representing the logical OR
/// of all input constraints. In practice, constructs the output constraint in the format of
/// not(and(not(A), not(B), not(C), …)) = 0, which is equivalent to or(A, B, C, …).
pub fn or<
    F: From<u64> + Debug,
    E: Into<Constraint<F>> + Clone,
    I: IntoIterator<Item = E> + Clone,
>(
    inputs: I,
) -> Constraint<F> {
    let mut annotations: Vec<String> = vec![];
    let mut exprs: Vec<Expr<F>> = vec![];

    for constraint in inputs.into_iter() {
        let constraint = constraint.into();
        match constraint.typing {
            Typing::Boolean | Typing::Unknown => {
                annotations.push(constraint.annotation);
                exprs.push(constraint.expr);
            }
            Typing::AntiBooly => panic!(
                "Expected Boolean or Unknown constraint, got AntiBooly (constraint: {})",
                constraint.annotation
            ),
        }
    }

    let result = not(and(exprs.into_iter().map(not)));

    Constraint {
        annotation: format!("({})", annotations.join(" OR ")),
        expr: result.expr,
        typing: Typing::Boolean,
    }
}

/// Takes two expressions and returns a new expression representing the logical XOR of the input
/// expressions.
pub fn xor<F: From<u64> + Clone, LHS: Into<Constraint<F>>, RHS: Into<Constraint<F>>>(
    lhs: LHS,
    rhs: RHS,
) -> Constraint<F> {
    let mut annotations: Vec<String> = vec![];

    let lhs: Constraint<F> = lhs.into();
    let rhs: Constraint<F> = rhs.into();

    let expr = match (lhs.typing, rhs.typing) {
        (Typing::Boolean | Typing::Unknown, Typing::Boolean | Typing::Unknown) => {
            annotations.push(lhs.annotation);
            annotations.push(rhs.annotation);
            lhs.expr.clone() + rhs.expr.clone() - 2u64.expr() * lhs.expr * rhs.expr
        },
        _ => panic!("Expected Boolean or Unknown constraints, got AntiBooly in one of lhs or rhs constraints (lhs constraint: {}) (rhs constraint: {})", lhs.annotation, rhs.annotation),
    };

    Constraint {
        annotation: format!("({})", annotations.join(" XOR ")),
        expr,
        typing: Typing::Boolean,
    }
}

/// Takes two constraints and returns a new constraint representing the equality of the input
/// constraints.
pub fn eq<F, LHS: Into<Constraint<F>>, RHS: Into<Constraint<F>>>(
    lhs: LHS,
    rhs: RHS,
) -> Constraint<F> {
    let lhs = lhs.into();
    let rhs = rhs.into();

    Constraint {
        annotation: format!("{} == {}", lhs.annotation, rhs.annotation),
        expr: lhs.expr - rhs.expr,
        typing: Typing::AntiBooly,
    }
}

/// Takes a selector constraint and two other constraints, and returns a new constraint that
/// represents the value of `when_true` if the selector is true, or `when_false` if the selector is
/// false.
pub fn select<
    F: From<u64> + Clone,
    T1: Into<Constraint<F>>,
    T2: Into<Constraint<F>>,
    T3: Into<Constraint<F>>,
>(
    selector: T1,
    when_true: T2,
    when_false: T3,
) -> Constraint<F> {
    let selector = selector.into();
    let when_true = when_true.into();
    let when_false = when_false.into();

    if selector.typing == Typing::AntiBooly {
        panic!(
            "Expected Boolean or Unknown selector, got AntiBooly (selector: {})",
            selector.annotation
        )
    }

    let typing = if when_true.typing == when_false.typing {
        when_true.typing
    } else {
        Typing::Unknown
    };

    Constraint {
        annotation: format!(
            "if({})then({})else({})",
            selector.annotation, when_true.annotation, when_false.annotation
        ),
        expr: selector.expr.clone() * when_true.expr
            + (1u64.expr() - selector.expr) * when_false.expr,
        typing,
    }
}

/// Takes a selector constraint and a `when_true` constraint, and returns a new constraint that
/// represents the value of `when_true` if the selector is true, or zero if the selector is false.
pub fn when<F: From<u64> + Clone, T1: Into<Constraint<F>>, T2: Into<Constraint<F>>>(
    selector: T1,
    when_true: T2,
) -> Constraint<F> {
    let selector = selector.into();
    let when_true = when_true.into();

    if selector.typing == Typing::AntiBooly {
        panic!(
            "Expected Boolean or Unknown selector, got AntiBooly (selector: {})",
            selector.annotation
        )
    }

    Constraint {
        annotation: format!("if({})then({})", selector.annotation, when_true.annotation),
        expr: selector.expr * when_true.expr,
        typing: when_true.typing,
    }
}

/// Takes a selector constraint and a `when_false` constraint, and returns a new constraint that
/// represents the value of `when_false` unless the selector is true, in which case it returns zero.
pub fn unless<F: From<u64> + Clone, T1: Into<Constraint<F>>, T2: Into<Constraint<F>>>(
    selector: T1,
    when_false: T2,
) -> Constraint<F> {
    let selector = selector.into();
    let when_false = when_false.into();

    if selector.typing == Typing::AntiBooly {
        panic!(
            "Expected Boolean or Unknown selector, got AntiBooly (selector: {})",
            selector.annotation
        )
    }

    Constraint {
        annotation: format!(
            "unless({})then({})",
            selector.annotation, when_false.annotation
        ),
        expr: (1u64.expr() - selector.expr) * when_false.expr,
        typing: when_false.typing,
    }
}

/// Takes a constraint and returns a new constraint representing the logical NOT of the input
/// constraint. The input constraint must have a value of either 0 or 1.
pub fn not<F: From<u64>, T: Into<Constraint<F>>>(constraint: T) -> Constraint<F> {
    let constraint = constraint.into();
    if constraint.typing == Typing::AntiBooly {
        panic!(
            "Expected Boolean or Unknown constraint, got AntiBooly (constraint: {})",
            constraint.annotation
        );
    }
    let annotation = format!("NOT({})", constraint.annotation);
    let expr = 1u64.expr() - constraint.expr;

    Constraint {
        annotation,
        expr,
        typing: Typing::Boolean,
    }
}

/// Takes a constraint and returns a new constraint representing whether the input constraint is
/// zero.
pub fn isz<F, T: Into<Constraint<F>>>(constraint: T) -> Constraint<F> {
    let constraint = constraint.into();

    Constraint {
        annotation: format!("0 == {}", constraint.annotation),
        expr: constraint.expr,
        typing: Typing::AntiBooly,
    }
}

/// Takes a `StepTypeHandler` and a constraint, and returns a new constraint that is only applied if
/// the next step is of the given step type.
pub fn if_next_step<F: Clone, T: Into<Constraint<F>>, ST: Into<StepTypeHandler>>(
    step_type: ST,
    constraint: T,
) -> Constraint<F> {
    let constraint = constraint.into();
    let step_type = step_type.into();

    let annotation = format!(
        "if(next step is {})then({})",
        step_type.annotation, constraint.annotation
    );

    Constraint {
        expr: step_type.next() * constraint.expr,
        annotation,
        typing: constraint.typing,
    }
}

/// Takes a `StepTypeHandler` and returns a new constraint that requires the next step to be of the
/// given step type.
pub fn next_step_must_be<F: From<u64>, ST: Into<StepTypeHandler>>(step_type: ST) -> Constraint<F> {
    let step_type = step_type.into();

    annotate(
        format!("next_step_must_be({})", step_type.annotation),
        not(step_type.next()),
        Typing::AntiBooly,
    )
}

/// Takes a `StepTypeHandler` and returns a new constraint that requires the next step to not be of
/// the given step type.
pub fn next_step_must_not_be<F: From<u64>, ST: Into<StepTypeHandler>>(
    step_type: ST,
) -> Constraint<F> {
    let step_type = step_type.into();

    annotate(
        format!("next_step_must_not_be({})", step_type.annotation),
        step_type.next(),
        Typing::AntiBooly,
    )
}

/// Takes a string annotation and an expression, and returns a new constraint with the given
/// annotation and expression.
pub fn annotate<F, E: Into<Expr<F>>>(annotation: String, expr: E, typing: Typing) -> Constraint<F> {
    Constraint {
        annotation,
        expr: expr.into(),
        typing,
    }
}

/// Computes the randomized linear combination of the given expressions and randomness.
pub fn rlc<F: From<u64>, E: Into<Expr<F>> + Clone, R: Into<Expr<F>> + Clone>(
    exprs: &[E],
    randomness: R,
) -> Expr<F> {
    if !exprs.is_empty() {
        let mut exprs = exprs.iter().rev().map(|e| e.clone().into());
        let init = exprs.next().expect("should not be empty");

        exprs.fold(init, |acc, expr| acc * randomness.clone().into() + expr)
    } else {
        0u64.expr()
    }
}

/// A helper struct for building lookup tables.
pub struct LookupBuilder<F> {
    pub lookup: Lookup<F>,
}

impl<F> Default for LookupBuilder<F> {
    fn default() -> Self {
        LookupBuilder {
            lookup: Lookup::default(),
        }
    }
}

impl<F: Debug + Clone> LookupBuilder<F> {
    /// Adds a source column-lookup column pair to the lookup table. Because the function returns a
    /// mutable reference to the `LookupBuilder<F>`, it can an chain multiple `add` and `enable`
    /// function calls to build the lookup table. Requires calling `lookup` to create an empty
    /// `LookupBuilder` instance at the very front.
    pub fn add<C: Into<Constraint<F>>, E: Into<Expr<F>>>(
        &mut self,
        constraint: C,
        expression: E,
    ) -> &mut Self {
        let constraint = constraint.into();
        self.lookup
            .add(constraint.annotation, constraint.expr, expression.into());
        self
    }

    /// Adds a selector column specific to the lookup table. Because the function returns a mutable
    /// reference to the `LookupBuilder<F>`, it can an chain multiple `add` and `enable` function
    /// calls to build the lookup table. Requires calling `lookup` to create an
    /// empty `LookupBuilder` instance at the very front.
    pub fn enable<C: Into<Constraint<F>>>(&mut self, enable: C) -> &mut Self {
        let enable = enable.into();
        self.lookup.enable(enable.annotation, enable.expr);
        self
    }
}

/// Creates a new empty `LookupBuilder` object and returns it. Can an chain multiple `add` and
/// `enable` function calls after to build the lookup table.
pub fn lookup<F: Debug + Clone>() -> LookupBuilder<F> {
    LookupBuilder::default()
}