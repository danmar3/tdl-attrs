# tdl-attrs


This library is inspired by attrs and a predecesor of this library called twodlearn.

Some of the goals with this library are:
- Reduce the use of hidden/private variable names
- Allow to specify different configuration arguments in sub-components of a class
- Encapsulate initialization code for each sub-component of a class
- Simplify initialization when using class inheritance


Toy example:

```python
import tdl_attrs as tdl
import random

# Start by using the @tdl.define decorator, which looks for tdl.pr attributes
# and configures the default initialization and build functions for the class
@tdl.define
class Dense(object):
    # Declare 'activation' as an attribute with default value None
    activation = tdl.pr.optional(None)
    # Declare 'units' as an attribute that needs to be explicitly
    # provided (no default value)
    units = tdl.pr.required(order=tdl.BUILD)

    def _init_vec(self, units, method):
        assert method in ("zeros", "random")
        if method == "zeros":
            return [0]*units
        elif method == "random":
            return [random.random() for _ in range(units)]

    @tdl.pr(reqs=[units], order=tdl.BUILD)
    def weights(self, method="random"):
        """ Initialization method for the attribute 'weights'.
        The argument 'order=tdl.BUILD' in the descriptor tells tdl
        that 'weights' should be initialized when calling tdl.build.
        The default value of 'order' is tdl.INIT, which initializes
        attributes when __init__ is called
        """
        return self._init_vec(self.units, method)

    @tdl.pr(reqs=[units], order=tdl.BUILD)
    def bias(self, method="zeros"):
        """ Initialization method for attribute bias.
        The 'reqs' argument in the descriptor indicates that the
        initialization requires 'units' to be initialized first.
        """
        return self._init_vec(self.units, method)

    def __call__(self, value):
        if not tdl.is_initialized(self, "units"):
            tdl.build(self, units=len(value))
        output = sum(
            [vi*wi + bi for vi, wi, bi
             in zip(value, self.weights, self.bias)]
             )
        if self.activation is None:
            return output
        elif self.activation == "relu":
            return 0 if output < 0 else output

# Initialize object with given arguments
dense = Dense(activation="relu")
assert dense.activation == "relu"
dense([1, 2, 3, 4])  # call object with an input array
# The attribute "units" is infered from the input length
assert dense.units == 4
assert len(dense.weights) == 4
# The default initialization of weights is 'random', hence the values
# should not be zero
assert all(wi != 0 for wi in dense.weights)

# We can specify different initialization options to each subcomponent
# initialized with the @tdl.pr descriptor.
# In this example, we set the initialization method of 'weights'
# to 'zeros'
dense = Dense(weights={'method': 'zeros'})
# Because 'activation' was not provided in the initialization call,
# tdl uses the default value (i.e. None)
assert dense.activation is None
assert dense([1, 2, 3, 4]) == 0
assert all(wi == 0 for wi in dense.weights)
```
