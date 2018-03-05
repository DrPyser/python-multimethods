# python-multimethods
Multimethods implementation in Python 3

Multimethods implement multiple dispatch function overloading.

The dispatching algorithm tries to unify the arguments of a multimethod call
to the dispatch specifiers specified for every implementation(overloading) of the multimethod.

Traditionally, "dispatch specifiers" are the type/class of the parameters.

```python
@generic(pattern=Type)
def add(a,b): pass

@add.method(int, int)
def add(a,b): return a+b

@add.method(float, float)
def add(a,b): return a+b

@add.method(str, str)
def add(a,b): return a+b

...
```

However, the dispatch specifiers can ultimately be arbitrary complex functions of the arguments.
For example, one could also dispatch based on the value of a key in a dictionary, or of an attribute in an object.

```python
from multimethods.patmat import AsPredicate, Compose, Equal, Key
@generic(pattern=lambda k: AsPredicate(Compose(Equal(k), Key("shape"))))
def area(s): pass

@area.method("circle")
def area(c): return 2*pi*c["radius"]**2

@area.method("square")
def area(c): return c["length"]*c["length"]

@area.method("triangle")
def area(c): return c["base"]*c["height"]/2

@area.method("rectangle")
def area(c): return c["length"]*c["height"]

print(area({"shape": "circle", "radius": 2})) # 12.566370614359172
print(area({"shape": "square", "length": 3})) # 9
print(area({"shape": "triangle", "base": 3, "height": 4})) # 6
print(area({"shape": "rectangle", "height": 2, "length": 6})) # 12

```

The dispatch specifiers can act as predicates on the arguments, restricting the set of inputs
a particar multimethod implementation can handle, but also as "preprocessors",
for example extracting a value from a complex object.

```python
from multimethods.patmat import Key

@generic(pattern=Key("shape"))
def describe(x): pass

@describe.method("circle")
def describe(c): return "A {} is round".format(c)

@describe.method("square")
def describe(c): return "A {} is like a box".format(c)

@describe.method("triangle")
def describe(c): return "{} man hates particle man".format(c)

@describe.method("rectangle")
def describe(c): return "A {} is like a square, but longer".format(c)
```

To keep a reference to the original value as well as the result of an extraction,
one can use `With`.

```python
from multimethods.patmat import With, Key

@generic(pattern=lambda k: With(Key("name")))
def bio(x): pass

@detail.method("particle")
def bio(c): return "Nobody knows, it's not important"

@bio.method("triangle")
def bio(c): return "{} man hates {}".format(c.match, c.value["hates"])

@bio.method("universe")
def bio(c): return "{} man, size of {} man".format(c.match,c.value["size"])

@bio.method("person")
def bio(c): return "{} man, hit on the head with {}, lives his life {}".format(c.match, c.value["hit with"], c.value["lives"])

print(bio({"name": "particle"}))
print(bio({"name": "triangle", "hates": ("particle man", "person man")}))
print(bio({"name": "universe", "size": "the entire universe"}))
print(bio({"name": "particle", "hit with": "a frying pan", "lives": "a garbage can"}))

```

The dispatch algorithm will select applicable implementations by trying to match
each methods' set of specifiers to the arguments, in the order each method was registered.
If a methods' specifiers match the arguments, the method is "applicable".
By default, only the first applicable method is used to compute the result of the multimethod call.
However, it is possible to override this behavior by specifying a "method combination" algorithm.

```python
from numbers import Number
from multimethods.patmat import Type

@generic(combiner=ApplyLast)
def at_last(x): pass

@at_last.method(Type(int))
def at_last(x): return "First, an int: {}".format(x)

@at_last.method(Type(float))
def at_last(x): return "Then, a float: {}".format(x)

@at_last.method(Type(Number))
def at_last(x): return "Finally, a Number: {}".format(x)

print(at_last(1)) # Finally, a Number: 1
print(at_last(2.0)) # Finally, a Number: 2.0

```

~~~python
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
~~~
