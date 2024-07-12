# Copyright (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

from threading import RLock


# 单例
class Singleton(type):
    """Metaclass for classes that wish to implement Singleton
    functionality.  If an instance of the class exists, it's returned,
    otherwise a single instance is instantiated and returned.
    """

    def __init__(cls, name, bases, dct):
        super(Singleton, cls).__init__(name, bases, dct)
        cls.__instance = None
        cls.__rlock = RLock()

    # 来自官方文档：
    # object.__call__(self[, args...])
    #     此方法会在实例作为一个函数被“调用”时被调用；
    #     如果定义了此方法，则 x(arg1, arg2, ...) 就大致可以被改写为 type(x).__call__(x, arg1, ...)。
    def __call__(cls, *args, **kw):
        # 如果这个类的实例已经存在，直接返回这个实例
        if cls.__instance is not None:
            return cls.__instance

        # 在加锁的情况下，如果实例不存在，调用父类的__call__创建一个实例并返回
        with cls.__rlock:
            if cls.__instance is None:
                cls.__instance = super(Singleton, cls).__call__(*args, **kw)

        return cls.__instance

# 按我简单的理解，具体的使用方法类似应该是下面这样：
# 可以看到，a和b是同一个实例，修改一个也会影响另一个
'''
if __name__ == "__main__":

    class example(metaclass=Singleton):
        def __init__(self):
            self.x = 0
            self.y = 0
        def __str__(self):
            return "x:%s, y:%s" % (self.x ,self.y)

    a = example()
    b = example()
    print(a is b)

    print("a:", a)
    print("b:", b)

    b.y = 1

    print("a:", a)
    print("b:", b)
'''
