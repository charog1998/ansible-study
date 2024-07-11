# (c) 2016, Ansible by Red Hat <info@ansible.com>
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

from ansible.module_utils.six import string_types


def pct_to_int(value, num_items, min_value=1):
    '''
    Converts a given value to a percentage if specified as "x%",
    otherwise converts the given value to an integer.
    '''

    # 如果value是一个百分比数，则将返回num_items对应的百分比再转成整数
    # 比如pct_to_int('12%',60)，会返回7
    # 因为 60*0.12 = 7.19
    if isinstance(value, string_types) and value.endswith('%'):
        value_pct = int(value.replace("%", ""))
        return int((value_pct / 100.0) * num_items) or min_value
    else:
        return int(value)


def object_to_dict(obj, exclude=None):
    """
    Converts an object into a dict making the properties into keys, allows excluding certain keys
    """
    # 返回一个字典：['obj具有的方法名（不以_开头的）':对应的那个方法]
    # 可以用object_to_dict(obj)['方法名']()，来调用这个方法
    if exclude is None or not isinstance(exclude, list):
        exclude = []
    return dict((key, getattr(obj, key)) for key in dir(obj) if not (key.startswith('_') or key in exclude))


def deduplicate_list(original_list):
    """
    Creates a deduplicated list with the order in which each item is first found.
    """
    # 就是把列表去重，但是没看懂 and not seen.add(x) 这个判断
    # 查了下 set.add 应该始终返回None的
    # 感觉就是为了写到一行里面
    seen = set()
    return [x for x in original_list if x not in seen and not seen.add(x)]
