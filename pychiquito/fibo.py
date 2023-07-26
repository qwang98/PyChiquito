class Fibonacci(Circuit):
    def __init__(self: Fibonacci):
        super().__init__()
        self.a: Queriable = self.forward(
            "a"
        )  # `self.a` is required instead of `a`, because steps need to access `circuit.a`.
        self.b: Queriable = self.forward("b")

        self.fibo_step: StepType = self.step_type(FiboStep(self, "fibo_step"))
        self.fibo_last_step: StepType = self.step_type(
            FiboLastStep(self, "fibo_last_step")
        )

        self.pragma_first_step(self.fibo_step)
        self.pragma_last_step(self.fibo_last_step)
        self.pragma_num_steps(11)
        # self.pragma_disable_q_enable()

        # self.expose(self.b, First())
        # self.expose(self.a, Last())
        # self.expose(self.a, Step(1))

    def trace(self: Fibonacci):
        def trace_def(ctx: TraceContext, _: Any):  # Any instead of TraceArgs
            ctx.add(self, self.fibo_step, (1, 1))
            a = 1
            b = 2
            for i in range(1, 10):
                ctx.add(self, self.fibo_step, (a, b))
                prev_a = a
                a = b
                b += prev_a
            ctx.add(self, self.fibo_last_step, (a, b))

        super().trace(trace_def)


FiboStep = ASTStepType(circuit: Fibonacci, step_type_name: "fibo_step")

class FiboStep(StepType):
    def setup

    def __init__(self: FiboStep, circuit: Fibonacci, step_type_name: str):
        super().__init__(
            step_type_name
        )  # Pass the id and annotation of handler to a new StepType instance.
        self.c = self.internal(
            "c"
        )  # `self.c` is required instead of `c`, because wg needs to access `self.c`.

        def setup_def(ctx: StepTypeSetupContext):
            ctx.constr(eq(circuit.a + circuit.b, self.c))
            ctx.transition(eq(circuit.b, circuit.a.next()))
            ctx.transition(eq(self.c, circuit.b.next()))

        self.setup(setup_def)

    def wg(self: FiboStep, circuit: Fibonacci):
        def wg_def(ctx: StepInstance, values: Tuple[int, int]):  # Any instead of Args
            a_value, b_value = values
            # print(f"fib step wg: {a_value}, {b_value}, {a_value + b_value}")
            ctx.assign(circuit.a, F(a_value))
            ctx.assign(circuit.b, F(b_value))
            ctx.assign(self.c, F(a_value + b_value))

        super().wg(wg_def)


class FiboLastStep(StepType):
    def __init__(self: FiboStep, circuit: Fibonacci, step_type: ASTStepType):
        super().__init__(step_type)
        self.c = self.internal("c")

        def setup_def(ctx: StepTypeSetupContext):
            ctx.constr(eq(circuit.a + circuit.b, self.c))

        self.setup(setup_def)

    def wg(self: FiboLastStep, circuit: Fibonacci):
        def wg_def(ctx: StepInstance, values: Tuple[int, int]):  # Any instead of Args
            a_value, b_value = values
            print(f"fib last step wg: {a_value}, {b_value}, {a_value + b_value}\n")
            ctx.assign(circuit.a, F(a_value))
            ctx.assign(circuit.b, F(b_value))
            ctx.assign(self.c, F(a_value + b_value))

        super().wg(wg_def)