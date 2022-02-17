import unittest
import tdl_attrs as tdl


class CoreTest(unittest.TestCase):
    def test_define(self):
        @tdl.define
        class ModelA(object):
            test_a1 = tdl.pr.required()
            test_a2 = tdl.pr.optional(2.0)

            @tdl.pr
            def test_a3(self, var=None):
                return var

            def __init__(self):
                self.init_a1 = "a1"

        @tdl.define
        class ModelB(ModelA):
            @tdl.pr
            def test_b1(self, var):
                return var

            @tdl.pr(reqs=[ModelA.test_a1, test_b1])
            def test_b2(self, var):
                return var*self.test_a1*self.test_b1

        @tdl.define
        class ModelC(object):
            @tdl.pr
            def test_c1(self, var):
                return var

            def __init__(self):
                self.init_c1 = "c1"

        @tdl.define
        class ModelD(ModelB, ModelC):
            @tdl.pr(reqs=[ModelB.test_b1])
            def test_a1(self, var):
                """this is a test
                Args:
                    var: test
                """
                return var*self.test_b1

            def __init__(self):
                """This is a Docstring Test"""
                super(ModelB, self).__init__()
                self.init_d1 = 'd1'

        model_a = ModelA(test_a1=1.0)
        assert model_a.test_a1 == 1.0, model_a.test_a2 == 2.0
        model_b = ModelB(test_a1=10.0, test_a2=2.0, test_b1=1.0, test_b2=2.0)
        assert model_b.test_a1 == 10.0, model_b.test_a2 == 2.0
        assert model_b.test_b1 == 1.0, model_b.test_b2 == 2.0*10.0*1.0

        assert model_a.test_a1 == 1.0, model_a.test_a2 == 2.0

        model_c = ModelD(test_a1=4.0, test_a2=5.0,
                         test_b1=2.0, test_b2=3.0,
                         test_c1=4.5)
        assert model_c.test_a1 == 2.0*4.0
        assert model_c.test_a3 is None
