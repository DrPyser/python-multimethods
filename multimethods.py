from collections import OrderedDict
from abc import ABC
from ..basics import identity


def ismatch(value, predicate):
    return predicate.__match__(value)


def ismatch(value, predicate):
    return predicate.__match__(value)


class predicate(ABC):
    """Base class for 'predicate' objects implementing the predicate protocol"""
    def __init__(self, predicate):
        self.predicate = predicate

    def __match__(self, x):
        return self.predicate(x)


class Is(predicate):
    def __init__(self, identity):
        self._identity = identity

    def __match__(self, x):
        return x is self._identity

class Equal(predicate):
    def __init__(self, equal):
        self._equal = equal

    def __match__(self, x):
        return x == self._equal

class In(predicate):
    def __init__(self, iterable):
        self._container = iterable

    def __match__(self, x):
        return x in self._container
    
class All(predicate):
    """Predicates combiner that match a value which is matched by all subpredicates"""
    def __init__(self, *predicates):
        self.predicates = predicates
    
    def __match__(self, x):
        return all(ismatch(x, p) for p in self.predicates)
    
class Any(predicate):
    """Predicates combiner that match a value which is matched by any(at least one) subpredicates"""
    def __init__(self, *predicates):
        self.predicates = predicates
    
    def __match__(self, x):
        return any(ismatch(x, p) for p in self.predicates)
    
class OneOf(predicate):
    """Predicates combiner that match a value which is matched by one and only one subpredicate"""
    def __init__(self, *predicates):
        self.predicates = predicates
    
    def __match__(self, x):
        return len(tuple(True for p in self.predicates if ismatch(x, p))) == 1


class Type(predicate):
    """Predicate that match a value by its type"""
    def __init__(self, t):
        self._type = t
        
    def __match__(self, x):
        return isinstance(x, self._type)


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

class multimethod:
    """A generic function object supporting multiple dispatch"""
    def __init__(self, fn, dispatcher=None):
        self._dispatcher = dispatcher
        self._original = fn
        self._methods = OrderedDict(())
        self.__name__ = fn.__name__
        self.__doc__ = fn.__doc__

    def __call__(self, *args, **kwargs):
        """Dispatch appropriate method on arguments"""        
        method = self.dispatch(*args, **kwargs)
        return method(*args, **kwargs)

    def add_method(self, specs, kwspecs,  method):
        self._methods[(specs, tuple(sorted(kwspecs.items())))] = method

    def get_method(self, specs):
        return self._methods.get(specs)

    def dispatch(self, *args, **kwargs):
        dispatcher = self._dispatcher or self._original(*args, **kwargs) or identity
            
        for ((specs, kwspecs), method) in self._methods.items():
            if all(ismatch(arg, dispatcher(p)) for (arg, p) in zip(args, specs))\
               and all(ismatch(kwargs[k], dispatcher(p)) for k, p in kwspecs):
                return method
        else:
            raise DispatchFailure(self, args, kwargs)


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

