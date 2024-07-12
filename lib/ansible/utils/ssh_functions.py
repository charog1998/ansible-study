# (c) 2016, James Tanner
# (c) 2016, Toshio Kuratomi <tkuratomi@ansible.com>
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

import subprocess

from ansible import constants as C
from ansible.module_utils.common.text.converters import to_bytes
from ansible.module_utils.compat.paramiko import paramiko
from ansible.utils.display import Display

display = Display()


# CONTROLPERSIST，持久化socket连接，短时间内无需密码可再次建立连接
# 这个字典用于保存某个命令是否开启了 CONTROLPERSIST
_HAS_CONTROLPERSIST = {}  # type: dict[str, bool]


def check_for_controlpersist(ssh_executable):
    # 用于判断传入的那个连接方式是否设置了controlpersist
    try:
        # If we've already checked this executable
        return _HAS_CONTROLPERSIST[ssh_executable]
    except KeyError:
        pass

    b_ssh_exec = to_bytes(ssh_executable, errors='surrogate_or_strict')
    has_cp = True
    try:
        cmd = subprocess.Popen([b_ssh_exec, '-o', 'ControlPersist'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = cmd.communicate()
        if b"Bad configuration option" in err or b"Usage:" in err:
            has_cp = False
    except OSError:
        has_cp = False

    _HAS_CONTROLPERSIST[ssh_executable] = has_cp
    return has_cp


# 设置默认的传输方式，如果ssh没开启controlpersist，同时paramiko又可用的话就用paramiko
# 否则就用ssh
def set_default_transport():

    # deal with 'smart' connection .. one time ..
    if C.DEFAULT_TRANSPORT == 'smart':
        display.deprecated("The 'smart' option for connections is deprecated. Set the connection plugin directly instead.", version='2.20')

        # see if SSH can support ControlPersist if not use paramiko
        if not check_for_controlpersist('ssh') and paramiko is not None:
            C.DEFAULT_TRANSPORT = "paramiko"
        else:
            C.DEFAULT_TRANSPORT = "ssh"
