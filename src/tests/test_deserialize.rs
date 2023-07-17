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
    fn test_python_circuit_json() {
        use crate::Circuit;
        let json = r#"
        {
            "step_types": {
                "10": {
                    "id": 10,
                    "name": "fibo_step",
                    "signals": [
                        {
                            "id": 11,
                            "annotation": "c"
                        }
                    ],
                    "constraints": [
                        {
                            "annotation": "((a + b) == c)",
                            "expr": {
                                "Sum": [
                                    {
                                        "Forward": [
                                            {
                                                "id": 8,
                                                "phase": 0,
                                                "annotation": "a"
                                            },
                                            false
                                        ]
                                    },
                                    {
                                        "Forward": [
                                            {
                                                "id": 9,
                                                "phase": 0,
                                                "annotation": "b"
                                            },
                                            false
                                        ]
                                    },
                                    {
                                        "Neg": {
                                            "Internal": {
                                                "id": 11,
                                                "annotation": "c"
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "transition_constraints": [
                        {
                            "annotation": "(b == next(a))",
                            "expr": {
                                "Sum": [
                                    {
                                        "Forward": [
                                            {
                                                "id": 9,
                                                "phase": 0,
                                                "annotation": "b"
                                            },
                                            false
                                        ]
                                    },
                                    {
                                        "Neg": {
                                            "Forward": [
                                                {
                                                    "id": 8,
                                                    "phase": 0,
                                                    "annotation": "a"
                                                },
                                                true
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            "annotation": "(c == next(b))",
                            "expr": {
                                "Sum": [
                                    {
                                        "Internal": {
                                            "id": 11,
                                            "annotation": "c"
                                        }
                                    },
                                    {
                                        "Neg": {
                                            "Forward": [
                                                {
                                                    "id": 9,
                                                    "phase": 0,
                                                    "annotation": "b"
                                                },
                                                true
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "annotations": {
                        "11": "c"
                    }
                },
                "12": {
                    "id": 12,
                    "name": "fibo_last_step",
                    "signals": [
                        {
                            "id": 13,
                            "annotation": "c"
                        }
                    ],
                    "constraints": [
                        {
                            "annotation": "((a + b) == c)",
                            "expr": {
                                "Sum": [
                                    {
                                        "Forward": [
                                            {
                                                "id": 8,
                                                "phase": 0,
                                                "annotation": "a"
                                            },
                                            false
                                        ]
                                    },
                                    {
                                        "Forward": [
                                            {
                                                "id": 9,
                                                "phase": 0,
                                                "annotation": "b"
                                            },
                                            false
                                        ]
                                    },
                                    {
                                        "Neg": {
                                            "Internal": {
                                                "id": 13,
                                                "annotation": "c"
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "transition_constraints": [],
                    "annotations": {
                        "13": "c"
                    }
                }
            },
            "forward_signals": [
                {
                    "id": 8,
                    "phase": 0,
                    "annotation": "a"
                },
                {
                    "id": 9,
                    "phase": 0,
                    "annotation": "b"
                }
            ],
            "shared_signals": [],
            "fixed_signals": [],
            "exposed": [],
            "annotations": {
                "8": "a",
                "9": "b",
                "10": "fibo_step",
                "12": "fibo_last_step"
            },
            "first_step": 10,
            "last_step": null,
            "num_steps": 0,
            "id": 1
        }
        "#;
        let circuit: Circuit<u32> = serde_json::from_str(json).unwrap();
        // print!("{:?}", circuit);
        println!("{:?}", circuit.to_chiquito_ast::<()>());
    }

    #[test]
    fn test_python_steptype_json() {
        use crate::StepType;
        let json = r#"{"id": 1, "name": "fibo", "signals": [{"id": 1, "annotation": "a"}, {"id": 2, "annotation": "b"}], "constraints": [{"annotation": "constraint", "expr": {"Sum": [{"Const": 1}, {"Mul": [{"Internal": {"id": 3, "annotation": "c"}}, {"Const": 3}]}]}}, {"annotation": "constraint", "expr": {"Sum": [{"Const": 1}, {"Mul": [{"Shared": [{"id": 4, "phase": 2, "annotation": "d"}, 1]}, {"Const": 3}]}]}}], "transition_constraints": [{"annotation": "trans", "expr": {"Sum": [{"Const": 1}, {"Mul": [{"Forward": [{"id": 5, "phase": 1, "annotation": "e"}, true]}, {"Const": 3}]}]}}, {"annotation": "trans", "expr": {"Sum": [{"Const": 1}, {"Mul": [{"Fixed": [{"id": 6, "annotation": "e"}, 2]}, {"Const": 3}]}]}}], "annotations": {"5": "a", "6": "b", "7": "c"}}"#;
        let step_type: StepType<u32> = serde_json::from_str(json).unwrap();
        // println!("{}", serde_json::to_string(&expr).unwrap());
        println!("{:?}", step_type);
    }

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
