import inspect
import functools
import networkx as nx


class TDL(object):
    def __init__(self, graph, init=None):
        self.graph = graph
        self.init = init


class TDLobj(object):
    def __init__(self):
        self.is_init = False
        self.enable_init = True
        self.args = dict()


class TdlDescriptor(object):
    @classmethod
    def required(cls, doc=None):
        def finit(self, value):
            return value
        return cls(finit=finit, doc=doc, infer_name=False)

    @classmethod
    def optional(cls, default=None, doc=None):
        def finit(self, value=None):
            if value is None:
                return default
            return value
        return cls(finit=finit, doc=doc, infer_name=False)

    class Initializer(object):
        def __init__(self, obj, attr, finit):
            self._finit = finit
            self._obj = obj
            self._attr = attr
            self._given_args = None

            def wrap_init(initializer, finit):
                @functools.wraps(finit)
                def init(self, *args, **kargs):
                    setattr(self._obj, self._attr_name,
                            self._finit(self._obj, *args, **kargs))

        def set_args(self, given_args):
            assert isinstance(given_args, dict)
            self._given_args = given_args

        def init(self, *args, **kargs):
            if self._given_args:
                kargs.update(self._given_args)
            # set the attribute using finit method
            setattr(self._obj, self._attr,
                    self._finit(self._obj, *args, **kargs))

    def __init__(self, finit=None, order=False, reqs=None, doc=None,
                 infer_name=True):
        self.finit = finit
        self.order = order
        if infer_name is True:
            self.name = (None if self.finit is None else finit.__name__)
            self.attr = f"__tdl__{self.name}"
        else:
            self.name = None
            self.attr = None
        self.reqs = reqs
        if self.reqs is None:
            self.reqs = list()

        if not doc and finit is not None:
            if finit.__doc__:
                doc = finit.__doc__
            else:
                doc = ('Autoinit with arguments {}'.format(
                    [arg for arg in inspect.getfullargspec(finit).args
                     if arg != 'self']))
        self.__doc__ = doc

    def update_name(self, value):
        self.name = value
        self.attr = f"__tdl__{self.name}"

    def __get__(self, obj, objtype):
        if obj is None:
            return self
        assert self.attr is not None
        if not hasattr(obj, self.attr):
            value = TdlDescriptor.Initializer(
                obj=obj, attr=self.attr, finit=self.finit)
            value.__doc__ = self.finit.__doc__
            return value
        return getattr(obj, self.attr)

    def __set__(self, obj, value):
        raise AttributeError(f"can't set attribute {self.name}")

    def __call__(self, finit=None):
        assert self.finit is None,\
            'the evaluation method has already been specified'
        return type(self)(finit=finit, order=self.order, reqs=self.reqs,
                          doc=self.__doc__)


def find_tdl_attrs(cls):
    attrs = dict()
    print(cls.__mro__)
    for ci in cls.__mro__[::-1]:
        for ni, ai in ci.__dict__.items():
            if isinstance(ai, TdlDescriptor):
                attrs[ni] = ai
    return attrs


def get_tdl_graph(cls):
    graph = nx.DiGraph()
    for ci in cls.__mro__[::-1]:
        for ni, desc_i in ci.__dict__.items():
            if isinstance(desc_i, TdlDescriptor):
                if desc_i.name is None:
                    print("WARNING: updating name")
                    desc_i.update_name(ni)
                graph.add_node(ni, desc=desc_i)
    for ni in graph.nodes:
        for nj in graph.nodes[ni]['desc'].reqs:
            graph.add_edge(nj.name, ni)
    assert nx.algorithms.dag.is_directed_acyclic_graph(graph)
    return graph


def init_graph(cls, obj, **kargs):
    print("initializing graph")
    for ni in nx.algorithms.dag.topological_sort(cls.__TDL__.graph):
        if ni not in kargs:
            getattr(obj, ni).init()
        elif isinstance(kargs[ni], dict):
            getattr(obj, ni).init(**kargs[ni])
        else:
            getattr(obj, ni).init(kargs[ni])


def init_wrapper(init_fn):
    @functools.wraps(init_fn)
    def init(obj, *args, **kargs):
        if not hasattr(obj, '__tdl__'):
            obj.__tdl__ = TDLobj()

        graph = type(obj).__TDL__.graph
        graph_kargs = {ki: vi for ki, vi in kargs.items() if ki in graph}
        init_kargs = {ki: vi for ki, vi in kargs.items()
                      if ki not in graph_kargs}

        # save current value for enable graph init in case it has been set to false
        enable_init = obj.__tdl__.enable_init
        # disable graph init while calling initialization
        obj.__tdl__.enable_init = False
        init_fn(obj, *args, **init_kargs)
        obj.__tdl__.enable_init = enable_init
        if obj.__tdl__.enable_init:
            init_graph(type(obj), obj, **graph_kargs)
    return init


def prep(cls):
    graph = get_tdl_graph(cls)
    if hasattr(cls, '__TDL__') and (
            cls.__init__ in [bi.__init__ for bi in cls.__bases__]):
        base = [bi for bi in cls.__bases__
                if cls.__init__ == bi.__init__][0]
        if hasattr(base, '__TDL__'):
            init = base.__TDL__.init
        else:
            init = base.__init__
        cls.__TDL__ = TDL(graph=graph, init=init)
        # cls.__init__ = init_wrapper(init)
    else:
        cls.__TDL__ = TDL(graph=graph, init=cls.__init__)
        cls.__init__ = init_wrapper(cls.__init__)
    print([graph.nodes[ni]['desc'].name for ni in graph.nodes])
    return cls
