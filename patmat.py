from functools import wraps
from contextlib import AbstractContextManager, ExitStack, contextmanager
from abc import ABC, abstractmethod
from enum import Enum
from operator import *
from .basics import flip

class OptionalGeneratorContext(AbstractContextManager):
    def __init__(self, generator):
        self._gen = generator

    def __enter__(self):
        return next(self._gen)

    def __exit__(self, *excs):
        try:
            x = next(self._gen)
            return x
        except StopIteration:
            return None


def optionalcontextmanager(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return OptionalGeneratorContext(f(*args, **kwargs))
    return wrapper
        

class MatchFailure(Exception):
    """Exception raised in case of a pattern match failure"""
    pass

class MatchSuccess(Exception):
    """Exception raised in case of match success"""
    pass


class matchstatus(Enum):
    pending = 0
    failed = 1
    succeeded = 2
    

class casecontext:
    def __init__(self, match_context, pattern=None):
        self._pattern = pattern
        self._match_context = match_context

    def __enter__(self):
        self._match_context._activate(self)
        self._match_context._status = matchstatus.pending
        if self._pattern is not None:
            return patterncontext(self._pattern, self._match_context.match_value)
        else:
            return None

    def __exit__(self, tp, value, tb):
        if tp is MatchFailure:
            self._match_context._status = matchstatus.failed
            self._match_context._tried += 1
            self._match_context._exit_case()
            return True
        elif any((tp,value,tb)):
            return None
        else:
            if self._match_context._status == matchstatus.failed:
                self._match_context._tried += 1
                self._match_context._exit_case()
                return True
            else:
                self._match_context._status = matchstatus.succeeded
                self._match_context._exit_case()
                raise MatchSuccess()
            

class match:
    def __init__(self, value):
        self._matching = value
        self._tried = 0
        self._actives = []
        self._status = matchstatus.pending

    @property
    def match_value(self):
        return self._matching
    
    def case(self, pattern=None):
        """Generates a case context.
        If an extractor is provided, binds an extractor context to the 'as' clause.
        Silence MatchFailure exceptions and raise MatchSuccess if all goes okay."""        
        context = casecontext(self, pattern)
        return context
   
    def ignore(self):
        """Equivalent to self.case(ignore), introduce a context without binding anything."""
        return casecontext(self)

    def _activate(self, case):
        self._actives.append(case)

    def _exit_case(self):
        self._actives.pop()
    
    def __enter__(self):
        return self
    
    def __exit__(self, tp, value, trace):
        if tp is MatchSuccess:
            return True
        elif tp is None and value is None and trace is None:
            raise MatchFailure("No provided pattern matched value {!r}".format(self._matching)) from None


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

        
def getmatch(pattern, matched):
    return pattern.__match__(matched)


class pattern(Pattern):
    """Wrapper class to wrap match functions"""
    def __init__(self, f):
        self._matchf = f

    def __match__(self, x):
        return self._matchf(x)

    def __call__(self, x):
        return patterncontext(self, x)

    @classmethod
    def from_exceptions(cls, *exceptions):
        """Generate a decorator to build an extractor 
        from a function that might fail with specified exceptions"""
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                try:
                    return f(*args, **kwargs)
                except exceptions:
                    raise MatchFailure() from None
            return wraps(f)(cls(wrapper))
        return decorator

    @classmethod
    def from_predicate(cls, f):
        """Generate a decorator to build an extractor from a predicate function"""
        @wraps(f)
        def wrapper(arg):
            if f(arg):
                return arg
            else:
                raise MatchFailure()
        return wraps(f)(cls(wrapper))


class patterncontext:
    """Context manager generator for creating a block
    binding the result of a successful pattern"""

    def __init__(self, pattern, value):
        self._pattern = pattern
        self._match = value

    def __match__(self, x):
        return self._pattern.__match__(x)
        
    def __enter__(self):
        return self._pattern.__match__(self._match)

    def __exit__(self, *excs):
        return None

    def __call__(self):
        return self._pattern.__match__(self._match)

    
@contextmanager    
def match_except(*exceptions):
    """Context manager that transforms 
    specified exceptions in MatchFailure exceptions
    :param exceptions: exceptions to be transformed into a match failure"""
    try:
        yield None
    except exceptions as ex:
        raise MatchFailure(str(ex)) from None
    
    
class Key(Pattern):
    """Pattern that match a gettable object containing a given key"""
    def __init__(self, key):
        self._key = key

    @match_except(KeyError, TypeError)
    def __match__(self, x):
        return x[self._key]

class Attr(Pattern):
    """Pattern that match an object which has a specified attribute"""
    def __init__(self, attribute):
        self._attribute = attribute

    @match_except(AttributeError)
    def __match__(self, x):
        return getattr(x, self._attribute)

class Attrs(Pattern):
    """Pattern that match an object which has all specified attributes"""
    def __init__(self, *attributes):
        self._attributes = attributes

    @match_except(AttributeError)
    def __match__(self, x):
        return tuple(getattr(x, attr) for attr in self._attributes)


def _ignore(x):
    return None
        
ignore = pattern(_ignore)


def ismatch(value, pattern):
    """Evaluate a match pattern, return True if match else False"""
    try:
        pattern.__match__(value)
        return True
    except MatchFailure:
        return False

    
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
        self._identity = identity
        self.predicate = partial(is_, identity)

    @predicate_method
    def __match__(self, x):
       return x is self._identity

    
class Equal(Predicate):
    def __init__(self, equal):
        self._equal = equal

    @predicate_method
    def __match__(self, x):
        return x == self._equal

    
class In(Predicate):
    def __init__(self, iterable):
        self._container = iterable

    @predicate_method
    def __match__(self, x):
        return x in self._container

    
class All(Predicate):
    """Predicates combiner that match a value which is matched by all subpredicates"""
    def __init__(self, *predicates):
        self.predicates = predicates

    @predicate_method
    def __match__(self, x):
        return all(ismatch(x, p) for p in self.predicates)

    
class Any(Predicate):
    """Predicates combiner that match a value which is matched by any(at least one) subpredicates"""
    def __init__(self, *predicates):
        self.predicates = predicates

    @predicate_method
    def __match__(self, x):
        return any(ismatch(x, p) for p in self.predicates)

    
class OneOf(Predicate):
    """Predicates combiner that match a value which is matched by one and only one subpredicate"""
    def __init__(self, *predicates):
        self.predicates = predicates

    @predicate_method
    def __match__(self, x):
        return len(tuple(map(partial(ismatch, x), self.predicates))) == 1


class Type(Predicate):
    """Predicate that match a value by its type"""
    def __init__(self, t):
        self._type = t
        self.predicate = partial(flip(isinstance), t)

    @predicate_method
    def __match__(self, x):
        return isinstance(x, self._type)
