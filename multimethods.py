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
    def __init__(self, dispatcher):
        self._dispatch = dispatcher
        self._methods = OrderedDict(())
        self.__name__ = dispatcher.__name__
        self.__doc__ = dispatcher.__doc__

    def __call__(self, *args, **kwargs):
        """Dispatch appropriate method on arguments"""        
        method = self.dispatch(*args, **kwargs)
        return method(*args, **kwargs)

    def add_method(self, specs, kwspecs,  method):
        self._methods[(specs, tuple(sorted(kwspecs.items())))] = method

    def get_method(self, specs):
        return self._methods.get(specs)

    def dispatch(self, *args, **kwargs):
        dispatcher = self._dispatch(*args, **kwargs)
        dispatcher = dispatcher if dispatcher is not None else identity        
            
        for ((specs, kwspecs), method) in self._methods.items():
            if all(ismatch(arg, dispatcher(p)) for (arg, p) in zip(args, specs))\
               and all(ismatch(kwargs[k], dispatcher(p)) for k, p in kwspecs):
                return method
        else:
            raise DispatchFailure(self, args, kwargs)


def method(generic, *specs, **kwspecs):
    def decorator(method):
        generic.add_method(specs, kwspecs, method)
        return generic
    return decorator

# def type_dispatch(*args, **kwargs):
#     """Dispatching based on an 'isinstance' relation"""
#     def dispatcher(*targs, **kwtargs):
#         posdispatch = all(map(isinstance, args, targs))
#         kwdispatch = all(isinstance(x,kwtargs[kx]) for (kx,x) in kwargs.items())
#         return posdispatch and kwdispatch
#     return dispatcher

# def key_dispatch(key):
#     """Dispatching based on the value of a key in a mapping"""
#     def key_dispatch2(*args, **kwargs):        
#         def dispatcher(*values, **kwvalues):
#             posdispatch = all(arg[key] == value for (arg, value) in zip(args, values))
#             kwdispatch = all(arg[key] == kwvalues[karg] for (karg, arg) in kwargs.items())
#             return posdispatch and kwdispatch
#         return dispatcher
#     return key_dispatch2


# def pred_dispatch(*args, **kwargs):
#     """Dispatching based on arbitrary predicates"""
#     def dispatcher(*conds, **kwconds):
#         posdispatch = all(f(x) for (f,x) in zip(conds, args))
#         kwdispatch = all(kwconds[k](arg) for (k, arg) in kwargs.items())
#         return posdispatch and kwdispatch
#     return dispatcher


if __name__ == "__main__":
   
    # In[28]:
    # Multimethod defined with dispatching done on arguments' class(i.e. using "isinstance")
    @multimethod
    def add(x,y):
        return type_dispatch(x,y)


    # In[29]:
    # method specialized on integer arguments
    @method(add, int, int)
    def add(x,y):
        return x + y


    # In[30]:

    add(1,2) # returns 3


    # In[31]:

    # method specialized on int and string arguments
    @method(add, int, str)
    def add(x,y):
        return x+int(y) 


    # In[32]:

    add(1,"10") # returns 11


    # In[35]:

    # Multimethod defined with dispatching done on the value at key "type"
    @multimethod
    def say(x, y):
        return key_dispatch("type")(x, y)


    # In[37]:
    # Method for both arguments with "person" as value for key "type" 
    @method(say, "person", "person")
    def say(x,y):
        return "I say '{}', you say '{}'".format(x.get("what"), y.get("what"))


    # In[38]:
    
    say({"type": "person", "what": "Hello!"}, {"type": "person", "what": "goodbye!"}) 


    # In[39]:

    # method for "person" and "robot" as values for key "type"
    @method(say, "person", "robot")
    def say(x,y):
        return "I say '{}', you say 'bip boop {} bip boop'".format(x.get("what"), y.get("what"))


    # In[41]:

    say({"type": "person", "what": "Hello!"}, {"type": "robot", "what": "GOODBYE!"})

