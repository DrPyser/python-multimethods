from collections import OrderedDict, deque
from abc import ABC
from funklib.core.prelude import identity
from multimethods.patmat import predicate_method, MatchFailure, getmatch, Any
from functools import reduce
from itertools import repeat, chain

class DispatchFailure(Exception):
    def __init__(self, generic, call_args, call_kwargs, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generic = generic
        self.args = call_args
        self.kwargs = call_kwargs

    def __str__(self):
        return "Missing implementation of multimethod {!r} for arguments ({}, {})".format(
            self.generic.__name__,
            ", ".join(map(str, self.args)),
            ", ".join("{}={}".format(k, v) for k,v in self.kwargs.items())
        )


def raise_dispatch_failure(generic, args, kwargs):
    raise DispatchFailure(generic, args, kwargs)
            
class MethodCombiner:
    def __init__(self, generic):
        self.generic = generic

    def fail(self, args, kwargs):
        raise_dispatch_failure(self.generic, args, kwargs)

    def combine(self, methods, args, kwargs):
        raise NotImplementedError()


class ApplyFirst(MethodCombiner):
    """Apply first method and return result"""
    def combine(self, methods, args, kwargs):
        try:
            (m, xargs, xkwargs) = next(methods)
            return m(*xargs, **xkwargs)
        except StopIteration:
            self.fail(args, kwargs)
        

class ApplyLast(MethodCombiner):
    """Apply last method and return result"""
    def combine(self, methods, args, kwargs):
        try:
            (method, xargs, xkwargs) = deque(methods, maxlen=1).pop()
            return method(*xargs, **xkwargs)
        except IndexError:
            self.fail(args, kwargs)
        

class ApplyAll(MethodCombiner):
    """Apply all and yield all results"""
    def combine(self, methods, args, kwargs):
        #choices = tuple(methods)
        for (method, xargs, xkwargs) in methods:
            yield method(*xargs, **xkwargs)
        else:
            self.fail(args, kwargs)


class ApplyReduce(ApplyAll):
    """Apply all and reduce"""
    def __init__(self, generic, op):
        super().__init__(generic)
        self.op = op

    def combine(self, methods, args, kwargs):
        results = super().combine(methods, args, kwargs)
        return reduce(self.op, results)
    
        
class multimethod:
    """A generic function object supporting multiple dispatch"""
    def __init__(self, fn, pattern=None, combiner=None):
        """
        Creates a multimethod object
        :param fn: function used in declaration
        :param pattern: callable that can construct a pattern matcher from the method dispatch specifiers
        :param method_combiner: MethodCombiner object that will be used to compute final result from matched methods
        """
        self.pattern_constructor = pattern 
        self.func = fn
        self.method_combiner = combiner or ApplyFirst(self)
        self.methods = OrderedDict(())
        self.__name__ = fn.__name__
        self.__doc__ = fn.__doc__

    def __call__(self, *args, **kwargs):
        """Dispatch appropriate method on arguments"""
        methods = self.dispatch(*args, **kwargs)
        return self.method_combiner.combine(methods, args, kwargs)

    def add_method(self, specs, kwspecs,  method):
        #todo: verify that patterns are hashable
        self.methods[(specs, tuple(sorted(kwspecs.items())))] = method

    def get_method(self, specs):
        return self.methods.get(specs)

    def dispatch(self, *args, **kwargs):
        patternfn = self.pattern_constructor or self.func(*args, **kwargs) or identity
        for ((specs, kwspecs), method) in self.methods.items():
            try:
                yield (
                    method,
                    tuple(getmatch(arg, p) for (arg, p) in zip(args, chain(map(patternfn, specs), repeat(Any())))),
                    {k:getmatch(kwarg, patternfn(kwspecs[k]) if k in kwspecs else Any()) for k, kwarg in kwargs}
                )
            except MatchFailure:
                continue

    def method(self, *specs, **kwspecs):
        return lambda f: self.add_method(specs, kwspecs, f) or self


def generic(fn=None, **kwargs):
    def decorator(f):
        return multimethod(f, **kwargs)
   
    if fn is not None:
        return multimethod(fn, **kwargs)
    else:
        return decorator


method = multimethod.method

if __name__ == "__main__":
    from multimethods.patmat import Compose, Equal, Key, AsPredicate, With
    @generic(pattern=lambda k: AsPredicate(Compose(Equal(k), Key("type"))))
    def describe(x): pass

    @describe.method("particle")
    def describe(x):
        print(x)
        return "It's not important"

    @describe.method("triangle")
    def describe(x):
        print(x)
        return "Hates particle man, hates person man"

    @describe.method("universe")
    def describe(x):
        print(x)
        return "Size of the entire universe"

    @describe.method("person")
    def describe(x):
        print(x)
        return "Lives his life in a garbage can"

    print(describe({"type": "particle"}))
    print(describe({"type": "triangle"}))
    print(describe({"type": "universe"}))
    print(describe({"type": "person"}))

    @generic
    def get_name(x): pass

    @get_name.method(With(Key("type")))
    def get_name(x):
        print(x)
        return "{} man".format(x.match)

    print(get_name({"type": "particle", "id": 1}))
    print(get_name({"type": "triangle", "kind": "obtuse"}))
    print(get_name({"type": "universe", "size": "big"}))
    print(get_name({"type": "person", "age": "45"}))
