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

        assert ModelA.test_a1.name == 'test_a1'
        assert ModelA.test_a2.name == 'test_a2'

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

    def test_isinitialized(self):
        @tdl.define
        class ModelA(object):
            test_a1 = tdl.pr.required()
            test_a2 = tdl.pr.optional(2.0)

            @tdl.pr(reqs=[test_a1, test_a2], order=tdl.INIT)
            def test_a3(self, value):
                return value*self.test_a1*self.test_a2

            @tdl.pr(reqs=[test_a1, test_a2], order=tdl.BUILD)
            def test_a4(self, value):
                return value*self.test_a1*self.test_a2

        model_a = ModelA(test_a1=1.0, test_a3=3.0)
        assert tdl.is_initialized(model_a, "test_a1")
        assert tdl.is_initialized(model_a, "test_a4") is False

    def test_build(self):
        @tdl.define
        class ModelA(object):
            test_a1 = tdl.pr.required()
            test_a2 = tdl.pr.optional(2.0)

            @tdl.pr(reqs=[test_a1, test_a2], order=tdl.INIT)
            def test_a3(self, value):
                return value*self.test_a1*self.test_a2

            @tdl.pr(reqs=[test_a1, test_a2], order=tdl.BUILD)
            def test_a4(self, value):
                return value*self.test_a1*self.test_a2

            @tdl.pr(reqs=[test_a1, test_a4], order=tdl.BUILD)
            def test_a5(self, value, bias):
                return value*self.test_a1*self.test_a4 + bias

        model_a1 = ModelA(test_a1=1.0, test_a3=3.0)
        assert tdl.is_initialized(model_a1, "test_a1")
        assert tdl.is_initialized(model_a1, "test_a4") is False
        tdl.build(model_a1, test_a4=4.0, test_a5={"value": 5.0, "bias": 1.5})
        assert tdl.is_initialized(model_a1, "test_a4")
        assert model_a1.test_a4 == 4.0*1.0*2.0

        model_a2 = ModelA(test_a1=1.0, test_a3=3.0, test_a4=4.0,
                          test_a5={'bias': 1.5})
        assert tdl.is_initialized(model_a2, "test_a4") is False
        tdl.build(model_a2, test_a5=5.0)
        assert tdl.is_initialized(model_a2, "test_a4")
        assert tdl.is_initialized(model_a2, "test_a5")
        assert model_a2.test_a4 == 4.0*1.0*2.0
        assert model_a2.test_a5 == 5.0*model_a2.test_a4 + 1.5
