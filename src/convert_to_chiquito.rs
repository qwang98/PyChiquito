use super::deserialize_types::{
    ast::{expr::Expr, *},
    wit_gen::TraceWitness,
};

use chiquito::{
    ast::{
        expr::{query::Queriable as cQueriable, Expr as cExpr},
        Circuit as cCircuit,
    },
    dsl::{
        cb::{Constraint as cbConstraint, Typing},
        circuit, StepTypeHandler as cStepTypeHandler,
    },
    wit_gen::{StepInstance as cStepInstance, TraceWitness as cTraceWitness},
};
use std::collections::HashMap;

pub fn to_chiquito_ast<TraceArgs>(circuit_to_convert: Circuit<u32>) -> cCircuit<u32, ()> {
    let ast = circuit::<u32, (), (), _>("", |ctx| {
        let mut uuid_map: HashMap<UUID, UUID> = HashMap::new(); // Python id to Rust id
        let mut query_map: HashMap<UUID, cQueriable<u32>> = HashMap::new(); // Rust id to Rust Queriable
        let mut step_type_handler_map: HashMap<UUID, cStepTypeHandler> = HashMap::new();

        for p in circuit_to_convert.forward_signals.iter() {
            let r = ctx.forward_with_phase(p.annotation, p.phase);
            uuid_map.insert(p.id, r.uuid());
            query_map.insert(r.uuid(), r); // Queriable implements Copy.
        }

        for p in circuit_to_convert.shared_signals.iter() {
            let r = ctx.shared_with_phase(p.annotation, p.phase);
            uuid_map.insert(p.id, r.uuid());
            query_map.insert(r.uuid(), r);
        }

        for p in circuit_to_convert.fixed_signals.iter() {
            let r = ctx.fixed(p.annotation);
            uuid_map.insert(p.id, r.uuid());
            query_map.insert(r.uuid(), r);
        }

        for p in circuit_to_convert.exposed.iter() {
            let r_id = uuid_map
                .get(&p.id)
                .expect("Exposed signal not found in uuid_map.");
            let r = *query_map
                .get(r_id)
                .expect("Exposed signal not found in forward_query_map.");
            ctx.expose(r);
        }

        for (step_type_id, step_type) in circuit_to_convert.step_types.clone() {
            let handler = ctx.step_type(Box::leak(step_type.name.clone().into_boxed_str()));
            uuid_map.insert(step_type_id, handler.uuid());
            step_type_handler_map.insert(handler.uuid(), handler); // StepTypeHandler impl Copy trait.

            ctx.step_type_def(handler, |ctx| {
                for p in step_type.signals.iter() {
                    let r = ctx.internal(p.annotation);
                    uuid_map.insert(p.id, r.uuid());
                    query_map.insert(r.uuid(), r);
                }
                ctx.setup(|ctx| {
                    for p in step_type.constraints.iter() {
                        let constraint = cbConstraint {
                            annotation: p.annotation.clone(),
                            expr: to_chiquito_expr(&p.expr, &uuid_map, &query_map),
                            typing: Typing::AntiBooly,
                        };
                        ctx.constr(constraint);
                    }
                    for p in step_type.transition_constraints.iter() {
                        let constraint = cbConstraint {
                            annotation: p.annotation.clone(),
                            expr: to_chiquito_expr(&p.expr, &uuid_map, &query_map),
                            typing: Typing::AntiBooly,
                        };
                        ctx.transition(constraint);
                    }
                });

                ctx.wg(|_ctx, ()| {}) // Don't need wg for ast.
            });

            if let Some(p_id) = circuit_to_convert.first_step {
                let r_id = uuid_map
                    .get(&p_id)
                    .expect("Step type not found in uuid_map.");
                let r = *step_type_handler_map
                    .get(r_id)
                    .expect("Step type not found in step_type_handler_map.");
                ctx.pragma_first_step(r);
            }

            if let Some(p_id) = circuit_to_convert.last_step {
                let r_id = uuid_map
                    .get(&p_id)
                    .expect("Step type not found in uuid_map.");
                let r = *step_type_handler_map
                    .get(r_id)
                    .expect("Step type not found in step_type_handler_map.");
                ctx.pragma_last_step(r);
            }

            ctx.pragma_num_steps(circuit_to_convert.num_steps);
        }
    });

    ast
}

pub fn to_chiquito_expr(
    expr_to_convert: &Expr<u32>,
    uuid_map: &HashMap<UUID, UUID>,
    query_map: &HashMap<UUID, cQueriable<u32>>,
) -> cExpr<u32> {
    match expr_to_convert {
        Expr::Const(p) => cExpr::Const(*p),
        Expr::Sum(p) => cExpr::Sum(
            p.into_iter()
                .map(|p| to_chiquito_expr(p, uuid_map, query_map))
                .collect(),
        ),
        Expr::Mul(p) => cExpr::Mul(
            p.into_iter()
                .map(|p| to_chiquito_expr(p, uuid_map, query_map))
                .collect(),
        ),
        Expr::Neg(p) => cExpr::Neg(Box::new(to_chiquito_expr(p, uuid_map, query_map))),
        Expr::Pow(arg0, arg1) => cExpr::Pow(
            Box::new(to_chiquito_expr(&arg0, uuid_map, query_map)),
            *arg1,
        ),
        Expr::Query(p) => {
            let r_id = uuid_map
                .get(&p.uuid())
                .expect("Exposed signal not found in uuid_map.");
            let r = *query_map
                .get(r_id)
                .expect("Exposed signal not found in forward_query_map.");
            cExpr::Query(r)
        }
    }
}

impl TraceWitness<u32> {
    fn to_chiquito_trace_witness(
        self: TraceWitness<u32>,
        uuid_map: &HashMap<UUID, UUID>,
        query_map: &HashMap<UUID, cQueriable<u32>>,
    ) -> cTraceWitness<u32> {
        let mut step_instances: Vec<cStepInstance<u32>> = Vec::new();
        for step_instance in self.step_instances.iter() {
            let mut assignments: HashMap<cQueriable<u32>, u32> = HashMap::new();
            for (k, v) in step_instance.assignments.iter() {
                let r_id = uuid_map.get(&k).unwrap();
                let query = query_map.get(r_id).unwrap();
                assignments.insert(*query, *v);
            }
            step_instances.push(cStepInstance {
                step_type_uuid: *uuid_map
                    .get(&step_instance.step_type_uuid)
                    .expect("step_type_uuid not found in uuid_map."),
                assignments,
            });
        }
        cTraceWitness {
            step_instances,
            height: self.height,
        }
    }
}
