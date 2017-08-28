
# coding: utf-8

# In[33]:

class multimethod:
    """A generic function object supporting multiple dispatch"""
    def __init__(self, dispatcher):
        self._dispatch = dispatcher
        self._methods = []

    def __call__(self, *args, **kwargs):
        """Dispatch appropriate method on arguments"""
        dispatch = self._dispatch(*args, **kwargs)
        for (specs, kwspecs, method) in self._methods:
            if dispatch(*specs, **kwspecs):
                return method(*args, **kwargs)

    def add_method(self, specs, kwspecs,  method):
        self._methods.append((specs, kwspecs, method))

def method(generic, *specs, **kwspecs):
    def decorator(method):
        generic.add_method(specs, kwspecs, method)
        return generic
    return decorator

def type_dispatch(*args, **kwargs):
    def dispatcher(*targs, **kwtargs):
        posdispatch = all(map(isinstance, args, targs))
        kwdispatch = all(isinstance(x,kwtargs[kx]) for (kx,x) in kwargs.items())
        return posdispatch and kwdispatch
    return dispatcher

def key_dispatch(key):
    def key_dispatch2(*args, **kwargs):        
        def dispatcher(*values, **kwvalues):
            posdispatch = all(arg[key] == value for (arg, value) in zip(args, values))
            kwdispatch = all(arg[key] == kwvalues[karg] for (karg, arg) in kwargs.items())
            return posdispatch and kwdispatch
        return dispatcher
    return key_dispatch2
    

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




