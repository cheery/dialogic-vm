# This is the interpreter and all the constructs it needs in order to function.

# Weak references are used in the symbol table to track variable references.
from weakref import WeakKeyDictionary

__all__ = [
    "Atom",
    "SymbolTable",
    "Compound",
    "Variable",
    "Printer",
    "stringify",
    "stringify_bound",
    "duplicate",
    "unify",
    "trampoline",
    "solve",
    "solve_next",
    "true",
    "false",
    "eq",
    "neq",
    "pconj",
    "pdisj",
    "cconj",
    "cdisj"]

# Atoms are system-internal objects for tagging compounds.
class Atom(object):
    def __init__(self, name, arity=0):
        self.name = name
        self.arity = arity

    # maybe harmful for readability, but helps with trying things out.
    def __call__(self, *args):
        return Compound(self, list(args))

# This internal object is required for indexing and keeping track of variables.
# It's used in conjunction with stringify, eg.
#   symtab = SymbolTable({x: y, ...})
#   stringify(symtab, x)
class SymbolTable(object):
    def __init__(self, table):
        self.table = WeakKeyDictionary(table)
        self.nextvar = 100 

def label(value, symtab):
    try:
        return symtab.table[value]
    except KeyError as _:
        if isinstance(value, Variable):
            var = "V"
        else:
            var = "o"
        name = "{}{}".format(var, symtab.nextvar)
        symtab.table[value] = name
        symtab.nextvar += 1
        return name

class Printer(object):
    def __init__(self, symtab):
        self.symtab = symtab

    def println(self, *values):
        print u" ".join(
            stringify(value, self.symtab)
            if not isinstance(value, unicode) else value
            for value in values).encode('utf-8')

    def printbounds(self, bounds):
        print stringify_bound(
            bounds[0] + bounds[1], self.symtab).encode('utf-8')

# Compounds and variables form the object space for our interpreter.
class Object(object):
    def __repr__(self):
        symtab = SymbolTable({})
        return stringify(self, symtab).encode('utf-8')

class Compound(Object):
    def __init__(self, atom, args):
        self.atom = atom
        self.args = args
        self.arity = len(args)
        assert self.arity == self.atom.arity

    def __eq__(self, other):
        return (isinstance(other, Compound)
            and self.atom is other.atom
            and all(a == b for a,b in zip(self.args, other.args)))

class Variable(Object):                 # We have positively and negatively
    def __init__(self, index):          # additive quantified variables.
        self.instance = self            
        self.index = index
        self.coroutines = []

    @property                           # Odd variables are negative.
    def polarity(self):                 # Even variables are positive.
        return self.index & 1

    def __eq__(a, b):
        while isinstance(a, Variable) and a.instance is not a:
            a = a.instance
        while isinstance(b, Variable) and b.instance is not b:
            b = b.instance
        return a is b

# Subscripts are used for displaying the index in variables.
def subscript(num):
    return str(num).translate(subscript_table)

subscript_digits = dict((str(i), unichr(0x2080+i)) for i in range(10))
subscript_table = u"".join(subscript_digits.get(chr(k), chr(k)) for k in range(128))

# Stringification is essential for recognizing what the results are.
def stringify(value, symtab):
    while isinstance(value, Variable) and value.instance is not value:
        value = value.instance
    if isinstance(value, Variable):
        return label(value, symtab) + subscript(value.index)
    if isinstance(value, Compound):
        return u"".join([
            value.atom.name,
            u"(",
            u",".join(stringify(x, symtab) for x in value.args),
            u")"])
    if isinstance(value, Constant):
        return label(value, symtab) + subscript(value.index)
    return label(value, symtab)

def stringify_bound(bound, symtab):
    ss = []
    for event in bound:
        if isinstance(event, Freeze):
            var = label(event.var, symtab) + subscript(event.var.index)
            cons = stringify(event.constraint, symtab)
            s = u"freeze(" + var + u", " + cons + u")"
        elif isinstance(event, Unbind):
            var = label(event.var, symtab) + subscript(event.var.index)
            val = stringify(event.value, symtab)
            s = u"unbind(" + var + u", " + val + u")"
        elif isinstance(event, Unfreeze):
            var = label(event.var, symtab) + subscript(event.var.index)
            cons = stringify(event.constraint, symtab)
            s = u"unfreeze(" + var + u", " + cons + u")"
        else:
            var = label(event, symtab) + subscript(event.index)
            val = stringify(event,  symtab)
            s = u"bind(" + var + u")"
        ss.append(s)
    return u"[" + u", ".join(ss) + u"]"

# Duplication allows the rule database to be invoked (implements contraction).
def duplicate(value, memo, index):
    while isinstance(value, Variable) and value.instance is not value:
        value = value.instance
    try:
        return memo[value]
    except KeyError as _:
        if isinstance(value, Compound):
            copy = Compound(value.atom,
                [duplicate(a, memo, index) for a in value.args])
        elif isinstance(value, Variable):
            copy = Variable(value.index + index)
        else:
            copy = value
        memo[value] = copy
        return copy

# '='  -> side=0
# '!=' -> side=1
def unify(a, b, bounds, weakenings, side):
    while isinstance(a, Variable) and a.instance is not a:
        a = a.instance
    while isinstance(b, Variable) and b.instance is not b:
        b = b.instance
    if a is b:
        return [true, false][side]
    # Sort the variables
    if (isinstance(a, Variable)
        and (not isinstance(b, Variable) or a.index > b.index)):
        a, b = b, a
    # If the rightmost variable is ours, we can win by unifying it.
    # Otherwise opponent wins by constraining it.
    if isinstance(b, Variable):
        pol = b.polarity
        bound = bounds[pol]
        if pol == side:
            # With compound terms we want to do an occurs check and refinement.
            if not isinstance(a, Variable) and not refine(b, a, bound):
                return [false, true][side]
            b.instance = a
            bound.append(b)
            return join(b.coroutines, side)
        else:
            constraint = Compound(neq, [a, b])
            weakening = weakenings[pol]
            if weakening is not None:
                constraint = Compound([pdisj, pconj][pol],
                    [constraint, weakening])
            b.coroutines.append(constraint)
            bound.append(Freeze(b, constraint))
            if isinstance(a, Variable) and a.polarity == pol:
                a.coroutines.append(constraint)
                bound.append(Freeze(a, constraint))
            return [false, true][side]
    # If we could prove that we only have variables and compounds,
    # we could just drop these conditions.
    # Finally if it's a compound term, it expands into multiple unifications.
    if isinstance(a, Compound) and isinstance(b, Compound):
        constraints = []
        if expand_compound(a, b, constraints, [eq, neq][side]):
            return join(constraints, side)
    return [false, true][side]

# Joins a sequence of constraints into compound expression.
def join(seq, side):
    if len(seq) == 0:
        return [true, false][side]
    op = [pconj, pdisj][side]
    head = seq.pop()
    while len(seq) > 0:
        head = Compound(op, [seq.pop(), head])
    return head

# Expands a compound statement into constraint sequences.
def expand_compound(a, b, constraints, op):
    if a.atom != b.atom:
        return False
    for x,y in zip(a.args, b.args):
        if isinstance(x, Compound) and isinstance(y, Compound):
            if not expand_compound(x, y, constraints, side):
                return False
        else:
            constraints.append(Compound(op, [x, y]))
    return True

# The refine is a merged occurrence check and variable lowering.
def refine(var, value, bound):
    while isinstance(value, Variable) and value.instance is not value:
        value = value.instance
    if var is value: # occurrence check fails
        return False
    if isinstance(value, Variable): # We got to refine our variables if their indices do not match.
        if value.polarity == var.polarity:
            if var.index < value.index:
                value.instance = Variable(var.index)
                value.instance.coroutines.extend(value.coroutines)
                bound.append(value)
            return True
        else:
            return var.index > value.index # Opponent variables represent 'skolemized' variables.
    if isinstance(value, Compound):
        for arg in value.args:
            if not refine(var, arg, bound):
                return False
        return True
    return False

# Added to 'bound' when something was appended to .coroutines
class Freeze(object):
    def __init__(self, var, constraint):
        self.var = var
        self.constraint = constraint # For debugging purposes.

# Added to 'bound' if the variable was unbound.
class Unbind(object):
    def __init__(self, var, value):
        self.var = var
        self.value = value

# Added to 'bound' if the variable is unfreezed.
class Unfreeze(object):
    def __init__(self, var, constraint):
        self.var = var
        self.constraint = constraint

# If the unification fails, the effects have to be reversed, revert does it.
def revert(bound):
    for event in reversed(bound):
        if isinstance(event, Freeze):
            event.var.coroutines.pop()
        elif isinstance(event, Unbind):
            event.var.instance = var
        elif isinstance(event, Unfreeze):
            event.var.coroutines.append(event.constraint)
        else:
            event.instance = event # If variable is bound, it's added to the
                                   # list as itself.

def temporevert(event, now):
    if isinstance(event, Freeze):
        if now:
            event.var.coroutines.pop()
        return Unfreeze(event.var, event.constraint)
    elif isinstance(event, Unbind):
        if now:
            event.var.instance = var
        return var
    elif isinstance(event, Unfreeze):
        if now:
            event.var.coroutines.append(event.constraint)
        return Freeze(event.var, event.constraint)
    else:
        val = event.var.instance
        if now:
            event.var.instance = event.var
        return Unbind(event.var, val)

def solve(goal, bounds, weakenings, choicepoints, program):
    return trampoline(solve_head,
        (goal, bounds, weakenings, None, choicepoints, 0, program))

def solve_next(bounds, choicepoints, program):
    side, goal, extra, point, weakenings, cont, scope = choicepoints.pop(0)
    revert(bounds[0][point[0]:])
    revert(bounds[1][point[1]:])
    bounds[0][point[0]:] = []
    bounds[1][point[1]:] = []
    revert(extra)
    for event in extra:
        bounds[side^1].append(temporevert(event, False))
    next_choicepoints = []
    result = trampoline(solve_head,
        (goal, bounds, weakenings, cont, next_choicepoints, scope, program))
    next_choicepoints.extend(choicepoints)
    return result, next_choicepoints

def trampoline(func, result):
    func, result = func(*result)
    while func is not None:
        func, result = func(*result)
    return result

def solve_head(goal, bounds, weakenings, cont, choicepoints, scope, program):
    if is_compound(eq, goal) or is_compound(neq, goal):
        a, b = goal.args
        goal = unify(a, b, bounds, weakenings, int(goal.atom is neq))
        return solve_head, (goal, bounds, weakenings, cont, choicepoints, scope, program)
    if is_compound(pdisj, goal) or is_compound(pconj, goal):
        side = int(goal.atom is pconj)
        a, b = goal.args
        point = (len(bounds[0]), len(bounds[1]))
        cont = cont, "parallel", side, (
            b, point, weaken(weakenings, a, side), scope)
        return solve_head, (a, bounds, weaken(weakenings, b, side),
            cont, choicepoints, scope, program)
        # parallel-cont
    if is_compound(cdisj, goal) or is_compound(cconj, goal):
        side = int(goal.atom is cconj)
        scope = scope_increment(scope, side)
        a, b = goal.args
        point = (len(bounds[0]), len(bounds[1]))
        cont = cont, "choice", side, (b, point, weakenings, scope)
        return solve_head, (a, s_bounds, weakenings, cont, choicepoints, scope, program)
        # choice-cont
    # Scope-increment is used when quantifiers are introduced.
    # It's needed for proper implementation of rule instantiation.
    if is_compound(idisj, goal) or is_compound(iconj, goal):
        side = int(goal.atom is iconj)
        scope = scope_increment(scope, side)
        return solve_head, (goal.args[0], bounds, weakenings,
            cont, choicepoints, scope, program)
    if goal is false or goal is true:
        return solve_cont, (goal, cont, bounds, choicepoints, program)
    if goal.atom in program:
        head, body = program[goal.atom]
        # Determining the properties of the rule from the name.
        side = int(goal.atom.name.startswith("!"))
        # Negated rules do not use the zeroeth variable index.
        index = scope_increment(scope, side) - side
        memo = {}
        head = duplicate(head, memo, index)
        body = Compound([idisj, iconj][side], [duplicate(body, memo, index)])
        pgoal = Compound([pconj, pdisj][side],
            [Compound([eq,neq][side], [goal, head]), body])
        return solve_head, (pgoal, bounds, weakenings,
            cont, choicepoints, scope, program)
    assert False, goal

def solve_cont(result, cont, bounds, choicepoints, program):
    if cont is None:
        return None, result
    cont, which, side, block = cont
    if which == "parallel":
        b, point, weakenings, scope = block
        if result is [false, true][side]:
            return solve_head(b, bounds, weakenings, cont, choicepoints, scope, program)
        # Guarded backtracking point.
        ccont = cont, "guard", side, None
        choicepoints.append((side, b, [], point, weakenings, ccont, scope))
        return solve_cont, (result, cont, bounds, choicepoints, program)
    if which == "guard":
        if result is [false, true][side]:
            return [sdisj, sconj][side]
        return solve_cont, (result, cont, bounds, choicepoints, program)
    if which == "choice":
        b, point, weakenings, scope = block
        if result is [false, true][side]:
            bound = bounds[side]
            apoint = len(bound)
            for i in range(len(bound)-1, point[side]-1, -1):
                bound.append(temporevert(bound[i], True))
            return solve_head, (a, bounds, weakenings, cont, choicepoints, scope, program)
        # A "normal" backtracking point.
        extra = []
        cbound = bounds[side^1]
        for i in range(point[side^1], bounds[side^1]):
            extra.append(temporevert(cbound[i], False))
        choicepoints.append((side, b, extra, point, weakenings, cont, scope))
        return solve_cont, (result, cont, bounds, choicepoints, program)
    assert False, cont

def scope_increment(scope, side):
    return scope + (scope & 1 ^ side)

def weaken(weakenings, constraint, side):
    a, b = weakenings
    if side == 0:
        if a is None:
            return (constraint, b)
        else:
            return (Compound(pdisj, [constraint, a]), b)
    else:
        if b is None:
            return (a, constraint)
        else:
            return (a, Compound(pconj, [constraint, b]))

def is_compound(atom, a):
    return isinstance(a, Compound) and a.atom is atom

true  = Atom("true", 0)()
false = Atom("false", 0)()
eq    = Atom("=", 2)
neq   = Atom("!=", 2)
pconj = Atom("pconj", 2)
pdisj = Atom("pdisj", 2)
cconj = Atom("cconj", 2)
cdisj = Atom("cdisj", 2)
iconj = Atom("iconj", 1) # Scope for quantifiers.
idisj = Atom("idisj", 1)

sdisj = Atom("sdisj", 0)()
sconj = Atom("sconj", 0)()
