# -*- encoding: utf-8 -*-
from divm import *

cons = Atom("cons", 2)
nil  = Atom("nil", 0)()

# append([], A, A).
# append([A|B], C, [A|D]) :- append(B, C, D).

# This implementation of 'append' is usually not treated as entirely correct,
# because it accepts things such as append([], 1,1).
program = {}

append     = Atom("append", 3)
not_append = Atom("!append", 3)

A = Variable(0)
B = Variable(0)
C = Variable(0)
AA = Variable(0)
AB = Variable(0)
AC = Variable(0)

program[append] = (append(A, B, C),
    cdisj(
        pconj(eq(A, nil), eq(B,C)),
        pconj(eq(A, cons(AA,AB)),
            pconj(eq(C, cons(AA,AC)),
                append(AB, B, AC)))
    )
)

A = Variable(1)
B = Variable(1)
C = Variable(1)
AA = Variable(1)
AB = Variable(1)
AC = Variable(1)

program[not_append] = (not_append(A, B, C),
    cconj(
        pdisj(neq(A, nil), neq(B,C)),
        pdisj(neq(A, cons(AA,AB)),
            pdisj(neq(C, cons(AA,AC)),
                not_append(AB, B, AC)))
    )
)

X = Variable(0)
Y = Variable(0)
Z = Variable(0)
log = Printer(SymbolTable({X: u"X", Y: u"Y", Z: u"Z"}))

goal = not_append(X, Y, Z)

bounds = ([], [])
choicepoints = []
log.println(u"solve", goal)
result = solve(goal, bounds, (None, None), choicepoints, program)
print sum(x[0] == 0 for x in choicepoints), sum(x[0] == 1 for x in choicepoints)
log.println(u"X =", X)
log.println(u"Y =", Y)
log.println(u"Z =", Z)
log.printconstraints([X,Y,Z])
log.println(result)
log.printbounds(bounds)
for point in choicepoints:
    log.println(u"choicepoint", point[1])
count = 0
while len(choicepoints) > 0 and count < 5:
    result, choicepoints = solve_next(bounds, choicepoints, program, result)
    print sum(x[0] == 0 for x in choicepoints), sum(x[0] == 1 for x in choicepoints)
    log.println(u"X =", X)
    log.println(u"Y =", Y)
    log.println(u"Z =", Z)
    log.printconstraints([X,Y,Z])
    log.println(result)
    for point in choicepoints:
        log.println(u"choicepoint", point[1])
    log.printbounds(bounds)
    count += 1
