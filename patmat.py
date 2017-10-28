from functools import wraps
from contextlib import AbstractContextManager, ExitStack, contextmanager
from abc import ABC, abstractmethod
from enum import Enum
from operator import *
from ..basics import flip, const
from functools import wraps,partial
from collections import namedtuple


def from_context(cm):
    """Extract the value produced by a context manager"""
    with cm as x:
        return x


class MatchFailure(Exception):
    """Exception raised in case of a pattern match failure"""
    # def __init__(self, matched, pattern):
    #     self.matched = matched
    #     self.pattern = pattern

    # def __repr__(self):
    #     return "MatchFailure({} ! {})".format(self.matched, self.pattern)

    # def __str__(self):
    #     return "MatchFailure: value {!r} does not match pattern {!s}".format(self.matched, self.pattern)


class MatchSuccess(Exception):
    """Exception raised in case of match success"""
    pass


class matchstatus(Enum):
    pending = 0
    failed = 1
    succeeded = 2
    

# class casecontext:
#     def __init__(self, match_context, pattern=None):
#         self._pattern = pattern
#         self._match_context = match_context

#     def __enter__(self):
#         self._match_context._activate(self)
#         self._match_context._status = matchstatus.pending
#         if self._pattern is not None:
#             return patterncontext(self._pattern, self._match_context.match_value)
#         else:
#             return None

#     def __exit__(self, tp, value, tb):
#         if tp is MatchFailure:
#             self._match_context._status = matchstatus.failed
#             self._match_context._tried += 1
#             self._match_context._exit_case()
#             return True
#         elif any((tp,value,tb)):
#             return None
#         else:

#             if self._match_context._status == matchstatus.failed:
#                 self._match_context._tried += 1
#                 self._match_context._exit_case()
#                 return True
#             else:
#                 self._match_context._status = matchstatus.succeeded
#                 self._match_context._exit_case()
#                 raise MatchSuccess()
            

class match:
    def __init__(self, value):
        self._value = value
        # self._tried = 0
        # self._actives = []
        # self._status = matchstatus.pending

    @property
    def value(self):
        return self._value

    @contextmanager
    def subcases(self):
        try:
            with match(self._value) as m:
                yield m
            raise MatchSuccess
        except MatchFailure:
            return

    @contextmanager
    def case(self, pattern=None):
        """Creates a case context.
        If an extractor is provided, binds an extractor context to the 'as' clause.
        Silence MatchFailure exceptions and raise MatchSuccess if all goes okay."""        
        try:
            if pattern:
                yield pattern.of(self._value)
            else:
                yield None
            raise MatchSuccess
        except MatchFailure:
            return

    @contextmanager
    def ignore(self):
        """Equivalent to self.case(ignore), 
        introduce a context without binding anything."""
        yield None
        raise MatchSuccess

    def __enter__(self):
        return self

    def __exit__(self, t, ex, tb):
        if t is MatchSuccess:
            return True
        if ex is None:
            raise MatchFailure("No pattern matches value {!r}".format(self._value))

    def __repr__(self):
        return "Match({})".format(self._value)


class Pattern(ABC):
    def __call__(self, x):
        return self.__match__(x)

    @abstractmethod
    def __match__(self, x):
        """Try and match its argument 
        and return a value or a tuple of values, or raise MatchFailure"""
        pass

    @contextmanager
    def of(self, x):
        yield self.__match__(x)


class ClassPattern(ABC):
    @classmethod
    @abstractmethod
    def __match__(cls, x):
        """Try and match its argument 
        and return a value or a tuple of values, or raise MatchFailure"""
        pass

    @classmethod
    @contextmanager
    def of(cls, x):
        yield cls.__match__(x)

        
class StaticPattern(ABC):
    @staticmethod
    @abstractmethod
    def __match__(x):
        """Try and match its argument 
        and return a value or a tuple of values, or raise MatchFailure"""
        pass

    @classmethod
    @contextmanager    
    def of(cls, x):
        yield cls.__match__(x)
        
        
@contextmanager    
def match_except(*exceptions):
    """Context manager that transforms 
    specified exceptions in MatchFailure exceptions
    :param exceptions: exceptions to be transformed into a match failure"""
    try:
        yield None
    except exceptions as ex:
        raise MatchFailure(repr(ex)) from None
    
    
class Key(Pattern):
    """Pattern that match a gettable object that contains a given key,
    exposing the value associated with that key"""
    def __init__(self, key):
        self.key = key

    @match_except(KeyError, TypeError)
    def __match__(self, x):
        return x[self.key]

    
class Keys(Pattern):
    """Pattern that match a gettable object that contains a given key,
    exposing the value associated with that key"""
    def __init__(self, keys):
        self.keys = keys

    @match_except(KeyError, TypeError)
    def __match__(self, x):
        return tuple(x[k] for k in self.keys)

    
class Attr(Pattern):
    """Pattern that match an object which has a specified attribute, 
    exposing that attribute"""
    def __init__(self, attribute):
        self.attribute = attribute

    @match_except(AttributeError)
    def __match__(self, x):
        return getattr(x, self.attribute)

    
class Attrs(Pattern):
    """Pattern that match an object which has all specified attributes,
    exposing all those attributes"""
    def __init__(self, *attributes):
        self.attributes = attributes

    @match_except(AttributeError)
    def __match__(self, x):
        return tuple(getattr(x, attr) for attr in self.attributes)


def pattern(Pattern):
    def __init__(self, func):
        self.pattern = func

    def __match__(self, x):
        return self.pattern(x)

    
_ignore = const(None)
ignore = pattern(_ignore)


def ismatch(value, pattern):
    """Evaluate a match pattern, return True if match else False"""
    try:
        pattern.__match__(value)
        return True
    except MatchFailure:
        return False


def getmatch(value, pattern):
    return pattern.__match__(value)
    
    
def predicate_method(f):
    @wraps(f)
    def wrapper(self, arg):
        if f(self, arg):
            return arg
        else:
            raise MatchFailure()
    return wrapper


def predicate_classmethod(f):
    @wraps(f)
    def wrapper(cls, arg):
        if f(cls, arg):
            return arg
        else:
            raise MatchFailure()
    return wrapper


def predicate_function(f):
    @wraps(f)
    def wrapper(arg):
        if f(arg):
            return arg
        else:
            raise MatchFailure()
    return wrapper
    
    
class Predicate(Pattern):
    """Base class for 'predicate' objects implementing the match protocol"""
    def __init__(self, predicate):
        self.predicate = predicate

    @predicate_method
    def __match__(self, x):
        return self.predicate(x)


class Is(Predicate):
    def __init__(self, identity):
        self.identity = identity
        self.predicate = partial(is_, identity)

    @predicate_method
    def __match__(self, x):
        return x is self.identity

    
class Equal(Predicate):
    def __init__(self, value):
        self.equal = value
        self.predicate = partial(eq, value)

    @predicate_method
    def __match__(self, x):
        return x == self.equal    
    
    
class In(Predicate):
    def __init__(self, iterable):
        self.container = iterable
        self.predicate = partial(contains, iterable)

    @predicate_method
    def __match__(self, x):
        return x in self.container


class Compose(Pattern):
    """
    Pattern combiner that applies patterns in chain, 
    matching the composition of all patterns,
    and failing if any of them fails
    """
    def __init__(self, *patterns):
        self.patterns = patterns

    def __match__(self, x):
        m = x
        for p in reversed(tuple(self.patterns)):
            m = getmatch(m, p)
        return m


class AsPredicate(Pattern):
    def __init__(self, pattern):
        self.pattern = pattern
    
    def __match__(self, x):
        if ismatch(x, self.pattern):
            return x
        else:
            raise MatchFailure


WithMatch = namedtuple("WithMatch", ("value", "match"))


class With(Pattern):
    def __init__(self, pattern):
        self.pattern = pattern

    def __match__(self, x):
        m = getmatch(x, self.pattern)
        return WithMatch(value=x, match=m)
    
    
class All(Predicate):
    """Predicate combiner that match a value which is matched by all subpredicates"""
    def __init__(self, *predicates):
        def _all(x):
            return all(map(partial(ismatch, x), predicates))
        self.predicates = predicates
        self.predicate = _all 

    @predicate_method
    def __match__(self, x):
        return all(map(partial(ismatch, x), self.predicates))

    
class Any(Predicate):
    """Predicates combiner that match a value which is matched by any(at least one) subpredicates"""
    def __init__(self, *predicates):
        def _any(x):
            return any(map(partial(ismatch, x), predicates))
        self.predicates = predicates
        self.predicate = _any

    @predicate_method
    def __match__(self, x):
        return any(map(partial(ismatch, x), self.predicates))

    
class OneOf(Predicate):
    """Predicates combiner that match a value which is matched by one and only one subpredicate"""
    def __init__(self, *predicates):
        def _oneof(x):
            return len(tuple(map(partial(ismatch, x), self.predicates))) == 1
        self.predicates = predicates
        self.predicate = _oneof

    @predicate_method
    def __match__(self, x):
        return len(tuple((partial(ismatch, x), self.predicates))) == 1


class Type(Predicate):
    """Predicate that match a value by its type"""
    def __init__(self, t):
        self.type = t
        self.predicate = partial(flip(isinstance), t)

    @predicate_method
    def __match__(self, x):
        return isinstance(x, self.type)


class Many(Pattern):
    def __init__(self, patterns):
        self.patterns = patterns

    def __match__(self, x):
        return tuple(map(partial(getmatch, x), self.patterns))
    
