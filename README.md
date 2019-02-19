# Dialogic logic programming VM prototype

It will likely take few more attempts to get this right.
The parallel disjunction rule is difficult to implement.

I used a variation of
[Alan Mycroft's prolog interpreter](https://www.cl.cam.ac.uk/~am21/research/funnel/prolog.c)
as a basis.
Dmiles had made the interpreter more flexible.
I translated that one into Python.
That translated version was my starting point for this interpreter.
There's not much left from the original interpreter though!

At the moment I got to write few demonstrations and maybe minor bugfixes.


# Sample program results

## Append

    append([], A, A).
    append([A|B], C, [A|D]) :- append(B, C, D).

    ?- append(X, Y, Y).

    X = nil()
    Y = Y₀
    true()
    ... program goes into infinite loop ...

This vm has the occurs check, this means that when the
interpreter tries to unify `A = cons(_,A)`,
it fails and the program stops being inductive.

It might be possible to prove mechanically that
this program no longer produces any more results.

Another append-related query we might like to try is.

    ?- append(X, Y, Z).

    X = nil()
    Y = Y₀
    Z = Y₀
    true()

    X = cons(V103₀,nil())
    Y = Y₀
    Z = cons(V103₀,Y₀)
    true()

    X = cons(V103₀,cons(V106₀,nil()))
    Y = Y₀
    Z = cons(V103₀,cons(V106₀,Y₀))
    true()

How about we ask settings where the X, Y, Z do not append?
Stopped using prolog prompt, because this is where
this system and the Prolog should differ.

    !append(X₀,Y₀,Z₀)

    X = X₀
    Y = Y₀
    Z = Z₀
    pdisj(!=(nil(),X₀),!=(Y₀,Z₀))
    pdisj(
        !=(cons(V100₁,V101₁),X₀),
        pdisj(
            !=(Z₀,cons(V100₁,V102₁)),
            !append(V101₁,Y₀,V102₁)))
    true()

    X = X₀
    Y = Y₀
    Z = Z₀
    pdisj(!=(Y₀,Z₀),!=(X₀,nil()))
    pdisj(
        !=(cons(V100₁,V101₁),X₀),
        pdisj(
            !=(Z₀,cons(V100₁,V102₁)),
            !append(V101₁,Y₀,V102₁)))
    true()

    X = X₀
    Y = Y₀
    Z = Z₀
    pdisj(!=(Y₀,Z₀),!=(X₀,nil()))
    pdisj(
        !=(cons(V100₁,V102₁),Z₀),
        pdisj(
            !append(V101₁,Y₀,V102₁),
            !=(X₀,cons(V100₁,V101₁))))
    true()

    X = X₀
    Y = Y₀
    Z = Z₀
    pdisj(!=(Y₀,Z₀),!=(X₀,nil()))
    sdisj()

    X = X₀
    Y = Y₀
    Z = Z₀
    pdisj(!=(Y₀,Z₀),!=(X₀,nil()))
    pdisj(
        !=(cons(V100₁,V102₁),Z₀),
        pdisj(
            !append(V101₁,Y₀,V102₁),
            !=(X₀,cons(V100₁,V101₁))))
    true()

If we skip the conjunctive choices after "sdisj()" result,
it appears to produce yet another true result.
Unfortunately all of these seem to be small variations from
each other.
Backtracking doesn't seem to do good
with parallel/multiplicative disjunction.

These slight permutations are annoying.
I suppose there would be a way to prevent them.

## Discovered & Fixed bugs

### Backtracking corruption

In `temporevert(event, now)` -function.

The `event.instance = event.instance` caused
variable bindings to not end up being unbound.

This bug revealed another which resulted in
occurrence check being jammed.
The likely issue was the code that calls temporevert.

    for i in range(len(bound)-1, point[side]-1, -1):
        bound.append(temporevert(bound[i], True))

This was building a reversed binding list.

There are likely other binding-related bugs present there.

