# -*- encoding: utf-8 -*-
from divm import *

# Not sure about what kind of programs I should try first.
program = {
}

X = Variable(0)
Y = Variable(0)
Z = Variable(0)
P = pconj(X, Y)
J = duplicate(P, {}, 0)

log = Printer(SymbolTable({X: u"X", Y: u"Y"}))

bounds = ([], [])
choicepoints = []
log.println(u"solve", neq(P, J))
result = solve(neq(P, J), bounds, (None, None), choicepoints, program)
print sum(x[0] == 0 for x in choicepoints), sum(x[0] == 1 for x in choicepoints)
log.println(u"X =", X)
log.println(u"Y =", X)
log.println(result)
log.printbounds(bounds)
while len(choicepoints) > 0:
    result, choicepoints = solve_next(bounds, choicepoints, program)
    print sum(x[0] == 0 for x in choicepoints), sum(x[0] == 1 for x in choicepoints)
    log.println(u"X =", X)
    log.println(u"Y =", X)
    log.println(result)
    log.printbounds(bounds)
