# (c) 2012-2014, Toshio Kuratomi <a.badger@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import annotations

from ansible.module_utils.common.text.converters import to_text


__all__ = ("unicode_wrap",)


# 这是一个装饰器，用来将函数返回值转为 text string 在python3中就是str类型
def unicode_wrap(func, *args, **kwargs):
    """If a function returns a string, force it to be a text string.

    Use with partial to ensure that filter plugins will return text values.
    """
    return to_text(func(*args, **kwargs), nonstring="passthru")


# if __name__ == '__main__':
#     def add(a, b):
#         return str(a + b).encode("utf-8")


#     from functools import partial

#     # 偏函数：把unicode_wrap的第一个参数锁定为add这个函数之后的函数
#     # a = partial(unicode_wrap, add)
#     # 偏函数可以实现一些不错的自定义效果，比如配合int函数实现二进制转十进制：
#     # bin2dec = partial(int, base=2)
#     
#     print(type(add(1, 2)))
#     print(type(a(a=1, b=2)))
#     # 可以看到add的返回值是bytes
#     # 但是a的返回值已经变成strle
