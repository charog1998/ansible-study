# Copyright (c) 2019 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations


# 直译为 "哨兵"
# 感觉这个类主要作用是用来辅助一些判断
class Sentinel:
    """
    Object which can be used to mark whether an entry as being special

    A sentinel value demarcates a value or marks an entry as having a special meaning.  In C, the
    Null byte is used as a sentinel for the end of a string.  In Python, None is often used as
    a Sentinel in optional parameters to mean that the parameter was not set by the user.

    You should use None as a Sentinel value any Python code where None is not a valid entry.  If
    None is a valid entry, though, then you need to create a different value, which is the purpose
    of this class.

    Example of using Sentinel as a default parameter value::

        def confirm_big_red_button(tristate=Sentinel):
            if tristate is Sentinel:
                print('You must explicitly press the big red button to blow up the base')
            elif tristate is True:
                print('Countdown to destruction activated')
            elif tristate is False:
                print('Countdown stopped')
            elif tristate is None:
                print('Waiting for more input')

    Example of using Sentinel to tell whether a dict which has a default value has been changed::

        values = {'one': Sentinel, 'two': Sentinel}
        defaults = {'one': 1, 'two': 2}

        # [.. Other code which does things including setting a new value for 'one' ..]
        values['one'] = None
        # [..]

        print('You made changes to:')
        for key, value in values.items():
            if value is Sentinel:
                continue
            print('%s: %s' % (key, value)
    """

    # 官方文档中对__new__的介绍：
    # object.__new__(cls[, ...])
    #     调用以创建一个 cls 类的新实例。__new__() 是一个静态方法 (因为是特例所以你不需要显式地声明)，
    #     它会将所请求实例所属的类作为第一个参数。其余的参数会被传递给对象构造器表达式 (对类的调用)。
    #     __new__() 的返回值应为新对象实例 (通常是 cls 的实例)。

    # 这个类并没有返回一个实例而是返回了这个类本身
    # 目的应该是为了避免一些可能的判断报错
    # 具体效果可以看下面的例子
    def __new__(cls):
        """
        Return the cls itself.  This makes both equality and identity True for comparing the class
        to an instance of the class, preventing common usage errors.

        Preferred usage::

            a = Sentinel
            if a is Sentinel:
                print('Sentinel value')

        However, these are True as well, eliminating common usage errors::

            if Sentinel is Sentinel():
                print('Sentinel value')

            if Sentinel == Sentinel():
                print('Sentinel value')
        """
        return cls

'''
如下代码都是判断为True的
a = Sentinel
b = Sentinel()
if a is b:
    print('ok')

if b is a:
    print('ok')

if a is Sentinel:
    print('ok')

if b is Sentinel:
    print('ok')

if a is Sentinel():
    print('ok')

if b is Sentinel():
    print('ok')
'''

'''
对比下面的代码可以看出修改Sentinel().__new__方法的用处

a = set
b = set()
if a is not b:
    print('ok') # 会显示'ok'

if b is not a:
    print('ok') # 会显示'ok'
'''