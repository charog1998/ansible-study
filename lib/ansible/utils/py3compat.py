# -*- coding: utf-8 -*-
#
# (c) 2018, Toshio Kuratomi <a.badger@gmail.com>
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import inspect
import os

from ansible.utils.display import Display


display = Display()


def __getattr__(name):
    # ansible.utils.py3compat 在获取environ属性会转为os.environ，即系统的环境变量
    # 如果获取其他属性的话会报AttributeError错误
    if name != 'environ':
        raise AttributeError(name)

    caller = inspect.stack()[1]

    display.deprecated(
        (
            'ansible.utils.py3compat.environ is deprecated in favor of os.environ. '
            f'Accessed by {caller.filename} line number {caller.lineno}'
        ),
        version='2.20',
    )

    return os.environ
