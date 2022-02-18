import inspect
import functools
import networkx as nx
from enum import Enum

from types import SimpleNamespace


class OrderType(Enum):
    INIT = 1
    MANUAL = 2
    BUILD = 3


class TDL(object):
    def __init__(self, graph, init=None):
        self.graph = graph
        self.init = init


class TDLobj(object):
    def __init__(self):
        self.enabled = True
        self.user_args = dict()


class TdlArgs(object):
    @classmethod
    def infer(cls, args, finit=None):
        if isinstance(args, TdlArgs):
            return args
        elif isinstance(args, dict):
            return TdlArgs(**args)
        else:
            return TdlArgs(args)

    def __init__(self, *args, **kargs):
        self.args = args
        self.kargs = kargs

    def update_infer(self, args):
        if isinstance(args, TdlArgs):
            self.args = args.args + self.args
            self.kargs.update(args.kargs)
        elif isinstance(args, dict):
            self.kargs.update(args)
        else:
            self.args = (args,) + self.args

    def __repr__(self):
        return f"{self.args}, {self.kargs}"


def _default_setter(self, value):
    return value


class TdlDescriptor(object):
    @classmethod
    def required(cls, order=OrderType.INIT, doc=None):
        def finit(self, value):
            return value
        return cls(finit=finit, order=order, doc=doc, infer_name=False)

    @classmethod
    def optional(cls, default=None, order=OrderType.INIT, doc=None):
        def finit(self, value=None):
            if value is None:
                return default
            return value
        return cls(finit=finit, order=order, doc=doc, infer_name=False)

    def setter(self, fset):
        prop = type(self)(self.finit, self.reqs, self.order,
                          fset=fset,
                          doc=self.__doc__,
                          infer_name=False)
        prop.update_name(self.name)
        return prop

    class Initializer(object):
        def __init__(self, obj, attr, finit):
            self._finit = finit
            self._obj = obj
            self._attr = attr

        def init(self, *args, **kargs):
            setattr(self._obj, self._attr,
                    self._finit(self._obj, *args, **kargs))

    def __init__(self, finit=None, reqs=None, order=OrderType.INIT,
                 fset=None, doc=None, infer_name=True, allow_set=False):
        self.finit = finit
        self.fset = fset
        if allow_set and fset is None:
            self.fset = _default_setter
        self.order = order
        if infer_name is True:
            self.name = (None if self.finit is None else finit.__name__)
            self.private_name = f"__tdl__{self.name}"
        else:
            self.name = None
            self.private_name = None
        self.reqs = reqs
        if self.reqs is None:
            self.reqs = list()

        if not doc and finit is not None:
            if finit.__doc__:
                doc = finit.__doc__
            else:
                finit_args = [
                    arg for arg in inspect.getfullargspec(finit).args
                    if arg != 'self']
                doc = (f'Initializer of order {self.order} \n'
                       f'Args: {finit_args}')
        self.__doc__ = doc

    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f"__tdl__{self.name}"

    def update_name(self, value):
        self.name = value
        self.private_name = f"__tdl__{self.name}"

    def __get__(self, obj, objtype):
        if obj is None:
            return self
        assert self.private_name is not None
        if not hasattr(obj, self.private_name):
            value = TdlDescriptor.Initializer(
                obj=obj, attr=self.private_name, finit=self.finit)
            value.__doc__ = self.finit.__doc__
            return value
        return getattr(obj, self.private_name)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError(f"can't set attribute {self.name}. "
                                 "No setter specified.")
        if hasattr(obj, self.private_name):
            raise AttributeError(f"can't set attribute {self.name}. "
                                 "Attribute has been already initialized")
        setattr(obj, self.private_name, self.fset(obj, value))

    def __call__(self, finit=None):
        assert self.finit is None,\
            'the evaluation method has already been specified'
        return type(self)(finit=finit, reqs=self.reqs, order=self.order,
                          fset=self.fset,
                          doc=self.__doc__)


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


def is_initialized(obj, attr):
    # return hasattr(obj, getattr(type(obj), attr).attr)
    return not isinstance(getattr(obj, attr), TdlDescriptor.Initializer)


def initialize_attr(obj, attr, user_args=None):
    if attr not in user_args:
        getattr(obj, attr).init()
    elif isinstance(user_args[attr], dict):
        getattr(obj, attr).init(**user_args[attr])
    elif isinstance(user_args[attr], TdlArgs):
        getattr(obj, attr).init(*user_args[attr].args, **user_args[attr].kargs)
    else:
        getattr(obj, attr).init(user_args[attr])


def init_graph(cls, obj, _tdl_order=OrderType.INIT, **kargs):
    # print("initializing graph")
    graph = cls.__TDL__.graph
    for ni in nx.algorithms.dag.topological_sort(graph):
        desc = graph.nodes[ni]['desc']
        if desc.order != _tdl_order:
            continue
        if is_initialized(obj, ni):
            continue
        # check reqs are initialized
        assert all([is_initialized(obj, ri.name) for ri in desc.reqs]), \
            f"requirements have not been initialized for {cls}.{ni}"
        # initialize
        initialize_attr(obj, ni, kargs)


def format_user_args(graph, args, kargs):
    graph_kargs = {ki: TdlArgs.infer(vi) for ki, vi in kargs.items()
                   if ki in graph}
    init_kargs = TdlArgs(
        *args,
        ** {ki: vi for ki, vi in kargs.items()
            if ki not in graph_kargs})
    return SimpleNamespace(
        init=init_kargs,
        graph=graph_kargs,
        )


def init_wrapper(init_fn):
    @functools.wraps(init_fn)
    def init(obj, *args, **kargs):
        if not hasattr(obj, '__tdl__'):
            obj.__tdl__ = TDLobj()

        if obj.__tdl__.enabled is False:
            init_fn(obj, *args, **kargs)
            return

        graph = type(obj).__TDL__.graph
        user_args = format_user_args(graph, args, kargs)

        # disable graph init while calling initialization
        obj.__tdl__.enabled = False
        init_fn(obj, *user_args.init.args, **user_args.init.kargs)
        obj.__tdl__.enabled = True
        # run graph initialization
        init_graph(type(obj), obj, **user_args.graph)
        obj.__tdl__.user_args = user_args
    return init


def build(obj, **kargs):
    user_args = obj.__tdl__.user_args.graph
    for ki, vi in kargs.items():
        if ki in user_args:
            # user_args[ki] should be TdlArgs
            user_args[ki].update_infer(vi)
        else:
            user_args[ki] = vi

    init_graph(type(obj), obj, _tdl_order=OrderType.BUILD, **user_args)


def define(cls):
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
    # print([graph.nodes[ni]['desc'].name for ni in graph.nodes])
    return cls
