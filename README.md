# python-multimethods
Multimethods implementation in Python 3

Dispatching algorithm is provided by user for each generic.
Some default dispatch algorithms are provided.

A dispatching algorithm "unifies" method arguments to method "dispatch parameters".
Traditionally, "dispatch parameters" can be the type/class of arguments. 
This dispatch method is provided as function "type_dispatch".
One could also dispatch on the value of a key in a dictionary, or of an attribute in an object.

One defines a multimethod as such:

```
@multimethod
def mymultimethod(*myargs, **mykwargs):
    return dispatch_function(*myargs, **mykwargs)
```
Here, the result of `dispatch_function(*myargs)` is a function of the dispatch parameters
provided by a method definition.

For example, in the case of traditional type dispatch, `dispatch_function` would look like

```
def type_dispatch(*args, **kwargs):
    def dispatcher(*postypes, **kwtypes):
        # attempt to unify each argument with a type
        # return a boolean indicating success or failure
        ...
    return dispatcher
        
```
For a simple two-arguments function, this would simplify to
```
@multimethod
def add(x,y):
    return lambda tx, ty: isinstance(x, tx) and isinstance(y, ty)
    
```

When the multimethod is called with arguments, 
this "dispatcher generator" function is called with those arguments, 
yielding a dispatch algorithm. 
The dispatch algorithm is tried on each set of dispatch parameters
specified by each method definition. If the algorithm succeeds(returns `True`), 
the corresponding method is called on the arguments, and its result returned as the result of the multimethod call.

Note that this mechanism allows different dispatch algorithm to be specified depending on the arguments
at the time of the the multimethod call.

## TODO

* Memoizing for dispatch algorithm
    * Currently, dispatching is linear in number of methods, 
      not counting the complexity of the dispatch unification
      (for simple type-based dispatch, this should be close to constant)
      Some kind of memoizing of the result of the dispatch algorithm would be great.
      
