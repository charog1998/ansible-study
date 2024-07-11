# (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
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

import os
import select
import shlex
import subprocess
import sys

from ansible.module_utils.common.text.converters import to_bytes


def run_cmd(cmd, live=False, readsize=10):
    # shlex.split用于将字符串按shell风格做拆解
    cmdargs = shlex.split(cmd)

    # 由于子进程需要接受二进制流，因此将命令转为二进制流
    # subprocess should be passed byte strings.
    cmdargs = [to_bytes(a, errors='surrogate_or_strict') for a in cmdargs]

    # 创建一个Popen实例，同时将标准输出和标准错误定向至一个新建的管道
    p = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout = b''
    stderr = b''
    rpipes = [p.stdout, p.stderr]
    while True:
        # select.select，用来监听前三个参数中是否有可读、可写、可执行的通道(文件描述符)
        # 这个方法中的可读可写的判断条件有点复杂，我只能先这样理解了
        # 返回的三个列表分别是可读、可写、可执行的通道列表
        # 第四个参数代表等待的时长(秒)，如果设置为None则会一直等下去
        # 如果指定时间内没有任何一个文件描述符符合条件则会直接返回
        rfd, wfd, efd = select.select(rpipes, [], rpipes, 1)

        if p.stdout in rfd:
            # fileno() 方法返回一个整型的文件描述符(file descriptor FD 整型)，可用于底层操作系统的 I/O 操作
            # 例如:
            # with open('123.txt','r') as fo:
            #     dat = os.read(fo.fileno(),10)
            #     print(dat)

            # 可以看到返回值就是从123.txt中读取到的前十个byte

            # 可以通过chardet检测出编码方式然后再解码回str

            # enc = chardet.detect(dat)
            # print(dat.decode(enc['encoding']))

            dat = os.read(p.stdout.fileno(), readsize)
            if live:
                # 如果设置了live=True的话，会把读取到的二进制数据写入到python的标准输出的缓冲区
                # 例如：
                # test.py
                # with open('123.txt','r') as fo:
                #     dat = os.read(fo.fileno(),15)
                #     sys.stdout.buffer.write(dat)
                
                # > python test.py
                # 会把读取到的信息传到终端

                # > python test.py >> out.txt
                # 则会把读取到的信息追加写入out.txt

                sys.stdout.buffer.write(dat)
            # 把读取到的信息追加到stdout
            stdout += dat
            # 如果dat还是空的，即stdout为空的话
            # 将p.stdout从rpipes中移除
            if dat == b'':
                rpipes.remove(p.stdout)
        # 这里和stdout的处理方法一样
        if p.stderr in rfd:
            dat = os.read(p.stderr.fileno(), readsize)
            stderr += dat
            if live:
                sys.stdout.buffer.write(dat)
            if dat == b'':
                rpipes.remove(p.stderr)
        # only break out if we've emptied the pipes, or there is nothing to
        # read from and the process has finished.
        # 用poll判断子进程是否已经结束，如果已经结束会返回结束状态码，如果没结束会返回None
        # 如果rpipes已经为空（即上面的两个remove都被执行过了，也就是说输出和错误都可读但是却没有读到东西）
        # 或者rfd为空（即select判断rpipes中的文本标识符均不可读）
        # 并且子进程已经结束，跳出while循环
        if (not rpipes or not rfd) and p.poll() is not None:
            break
        # 如果rpipes已经为空但是子进程还没有结束
        # 那么就调用wait等待子进程结束
        # Calling wait while there are still pipes to read can cause a lock
        elif not rpipes and p.poll() is None:
            p.wait()

    # 三个返回值分别是 状态码，标准输出，标准错误
    return p.returncode, stdout, stderr
