from collections import OrderedDict
from abc import ABC
from ..basics import identity
from .patmat import predicate_method, MatchFailure, getmatch
from functools import reduce
from collections import deque


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


class FirstMethod(MethodCombiner):
    def combine(self, methods, args, kwargs):
        try:
            (m, xargs, xkwargs) = next(methods)
            return m(*xargs, **xkwargs)
        except StopIteration:
            self.fail(args, kwargs)
        

class LastMethod(MethodCombiner):
    def combine(self, methods, args, kwargs):
        try:
            (method, xargs, xkwargs) = dequeue(methods, maxlen=1).pop()
            return method(*xargs, **xkwargs)
        except IndexError:
            self.fail(args, kwargs)
        

class AllMethod(MethodCombiner):
    def combine(self, methods, args, kwargs):
        choices = tuple(methods)
        if any(methods):
            for (method, xargs, xkwargs) in methods:
                yield method(*xargs, **xkwargs)
        else:
            self.fail(args, kwargs)


class OpMethod(AllMethod):
    def __init__(self, generic, op):
        super().__init__(generic)
        self.op = op

    def combine(self, methods, args, kwargs):
        results = super().combine(methods, args, kwargs)
        return reduce(self.op, results)
    
        
class multimethod:
    """A generic function object supporting multiple dispatch"""
    def __init__(self, fn, pattern=None, method_combiner=None):
        """
        Creates a multimethod object
        :param fn: function used in declaration
        :param pattern: callable that can construct a pattern from the method dispatch specifiers
        :param method_combiner: MethodCombiner object that will be used to compute final result from matched methods
        """
        self.pattern_constructor = pattern 
        self.func = fn
        self.method_combiner = method_combiner or FirstMethod(self)
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
                    tuple(getmatch(arg, patternfn(p)) for (arg, p) in zip(args, specs)),
                    {k:getmatch(kwargs[k], patternfn(p)) for k, p in kwspecs}
                )
            except MatchFailure:
                continue


def generic(*args, **kwargs):
    def decorator(f):
        return multimethod(f, **kwargs)
   
    if len(args) == 1 and len(kwargs) == 0:
        return multimethod(*args)
    elif len(args) == 0:
        return decorator


def method(generic, *specs, **kwspecs):
    def decorator(method):
        generic.add_method(specs, kwspecs, method)
        return generic
    return decorator

