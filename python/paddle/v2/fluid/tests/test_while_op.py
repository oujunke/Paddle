import unittest
import paddle.v2.fluid.layers as layers
from paddle.v2.fluid.executor import Executor
import paddle.v2.fluid.core as core
from paddle.v2.fluid.backward import append_backward_ops
import numpy


class TestWhileOp(unittest.TestCase):
    def test_simple_forward(self):
        d0 = layers.data(
            "d0", shape=[10], append_batch_size=False, dtype='float32')
        d1 = layers.data(
            "d1", shape=[10], append_batch_size=False, dtype='float32')
        d2 = layers.data(
            "d2", shape=[10], append_batch_size=False, dtype='float32')
        i = layers.zeros(shape=[1], dtype='int64')
        i.stop_gradient = True
        init = layers.zeros(shape=[10], dtype='float32')
        mem_array = layers.array_write(x=init, i=i)
        data_array = layers.array_write(x=d0, i=i)

        i = layers.increment(i)
        layers.array_write(d1, i, array=data_array)

        i = layers.increment(i)
        layers.array_write(d2, i, array=data_array)

        i = layers.zeros(shape=[1], dtype='int64')
        i.stop_gradient = True

        array_len = layers.fill_constant(shape=[1], dtype='int64', value=3)
        array_len.stop_gradient = True
        cond = layers.less_than(x=i, y=array_len)

        while_op = layers.While(cond=cond)
        with while_op.block():
            d = layers.array_read(array=data_array, i=i)
            prev = layers.array_read(array=mem_array, i=i)
            result = layers.sums(input=[d, prev])

            i = layers.increment(x=i, in_place=True)
            layers.array_write(result, i=i, array=mem_array)
            layers.less_than(x=i, y=array_len, cond=cond)

        sum_result = layers.array_read(array=mem_array, i=i)
        loss = layers.mean(x=sum_result)

        append_backward_ops(loss)

        cpu = core.CPUPlace()
        exe = Executor(cpu)
        d = []

        for i in xrange(3):
            d.append(numpy.random.random(size=[10]).astype('float32'))

        d_tensor = []
        for item in d:
            t = core.LoDTensor()
            t.set(item, cpu)
            d_tensor.append(t)

        outs = map(numpy.array,
                   exe.run(feed={
                       'd0': d_tensor[0],
                       'd1': d_tensor[1],
                       'd2': d_tensor[2]
                   },
                           fetch_list=[sum_result]))
        self.assertAlmostEqual(numpy.sum(d), numpy.sum(outs[0]), delta=0.01)


if __name__ == '__main__':
    unittest.main()
