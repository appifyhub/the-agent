import unittest
from threading import Thread

from util.singleton import Singleton


class SingletonTestClass(metaclass = Singleton):

    pass


class SingletonTest(unittest.TestCase):

    def test_instance_safety(self):
        instances = []

        def create_instance():
            instances.append(SingletonTestClass())

        threads = [Thread(target = create_instance) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # check if it's the same instance or not
        for instance in instances:
            self.assertIs(instance, instances[0])
