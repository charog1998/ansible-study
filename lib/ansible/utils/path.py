# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
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
import shutil

from errno import EEXIST
from ansible.errors import AnsibleError
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text
# to_native 转为python系统的原生字符串，在python3中就代表str


__all__ = ['unfrackpath', 'makedirs_safe']


def unfrackpath(path, follow=True, basedir=None):
    '''
    Returns a path that is free of symlinks (if follow=True), environment variables, relative path traversals and symbols (~)

    :arg path: A byte or text string representing a path to be canonicalized
    :arg follow: A boolean to indicate of symlinks should be resolved or not
    :arg basedir: A byte string, text string, PathLike object, or `None`
        representing where a relative path should be resolved from.
        `None` will be substituted for the current working directory.
    :raises UnicodeDecodeError: If the canonicalized version of the path
        contains non-utf8 byte sequences.
    :rtype: A text string (unicode on pyyhon2, str on python3).
    :returns: An absolute path with symlinks, environment variables, and tilde
        expanded.  Note that this does not check whether a path exists.

    example::
        '$HOME/../../var/mail' becomes '/var/spool/mail'
    '''
    # 这个方法主要是用来解析路径中的各种符号，并且返回一个最规范的绝对路径

    b_basedir = to_bytes(basedir, errors='surrogate_or_strict', nonstring='passthru')

    # 如果未提供basedir则代表以当前工作路径作为basedir
    if b_basedir is None:
        b_basedir = to_bytes(os.getcwd(), errors='surrogate_or_strict')
    # 如果basedir是一个文件路径的话，则将它所在的文件夹作为base
    elif os.path.isfile(b_basedir):
        b_basedir = os.path.dirname(b_basedir)

    # expandvars: 用来替换掉路径中的环境变量，例如 '$path'
    # expanduser: 用来把波浪号 '~' 替换成用户的根目录
    b_final_path = os.path.expanduser(os.path.expandvars(to_bytes(path, errors='surrogate_or_strict')))

    # isabs: 用来判断路径是否为绝对路径
    # 如果不是绝对路径就把 basedir 和 final_path 拼成绝对路径
    if not os.path.isabs(b_final_path):
        b_final_path = os.path.join(b_basedir, b_final_path)

    # follow 表示是否要解析符号链接
    # 如果需要的话用realpath进行解析
    if follow:
        b_final_path = os.path.realpath(b_final_path)

    # normpath用来规范化路径
    # 例如：A//B A/B/ A/./B A/xxx/../B
    # 都会简化为 A/B
    # Windows系统会把 / 转为 \ 
    return to_text(os.path.normpath(b_final_path), errors='surrogate_or_strict')


def makedirs_safe(path, mode=None):
    '''
    A *potentially insecure* way to ensure the existence of a directory chain. The "safe" in this function's name
    refers only to its ability to ignore `EEXIST` in the case of multiple callers operating on the same part of
    the directory chain. This function is not safe to use under world-writable locations when the first level of the
    path to be created contains a predictable component. Always create a randomly-named element first if there is any
    chance the parent directory might be world-writable (eg, /tmp) to prevent symlink hijacking and potential
    disclosure or modification of sensitive file contents.

    :arg path: A byte or text string representing a directory chain to be created
    :kwarg mode: If given, the mode to set the directory to
    :raises AnsibleError: If the directory cannot be created and does not already exist.
    :raises UnicodeDecodeError: if the path is not decodable in the utf-8 encoding.
    '''

    # EEXIST
    # exception FileExistsError
    #     当试图创建一个已存在的文件或目录时将被引发。 对应于 errno EEXIST。

    rpath = unfrackpath(path)
    b_rpath = to_bytes(rpath)

    # 首先判断这个路径是否存在
    # 如果存在的话则什么都不做
    if not os.path.exists(b_rpath):
        try:
            if mode:
                # mode是一个int变量，代表着linux系统中的文件权限，默认为八进制的777，十进制的511

                # makedirs是直接创建整个路径的方法，如果路径中的某个中间路径不存在则会试图去创建它
                # 默认情况下(exist_ok = False)当试图创建的目标文件夹已存在时则会报错
                # 但是由于上面已经判断过 b_rpath 是否存在，因此这个方法能保证始终不会抛出EEXIST异常
                os.makedirs(b_rpath, mode)
            else:
                os.makedirs(b_rpath)
        except OSError as e:
            if e.errno != EEXIST:
                # 如果遇到其他异常则正常报错
                raise AnsibleError("Unable to create local directories(%s): %s" % (to_native(rpath), to_native(e)))


def basedir(source):
    """ returns directory for inventory or playbook """
    source = to_bytes(source, errors='surrogate_or_strict')
    dname = None
    # 如果source是文件夹，则dname直接取source的值
    if os.path.isdir(source):
        dname = source
    # 如果source为空或者是'.'，则取当前工作目录
    elif source in [None, '', '.']:
        dname = os.getcwd()
    # 如果是文件则取文件所在目录
    elif os.path.isfile(source):
        dname = os.path.dirname(source)

    if dname:
        # don't follow symlinks for basedir, enables source re-use
        # 确保dname是绝对路径
        dname = os.path.abspath(dname)

    return to_text(dname, errors='surrogate_or_strict')


def cleanup_tmp_file(path, warn=False):
    """
    Removes temporary file or directory. Optionally display a warning if unable
    to remove the file or directory.

    :arg path: Path to file or directory to be removed
    :kwarg warn: Whether or not to display a warning when the file or directory
        cannot be removed
    """
    try:
        if os.path.exists(path):
            try:
                if os.path.isdir(path):
                    # 递归地删除文件夹及其内容
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    # 删除单个文件
                    os.unlink(path)
            except Exception as e:
                # warn用来提示是否要抛出异常
                if warn:
                    # Importing here to avoid circular import
                    from ansible.utils.display import Display
                    display = Display()
                    display.display(u'Unable to remove temporary file {0}'.format(to_text(e)))
    except Exception:
        pass


def is_subpath(child, parent, real=False):
    """
    Compares paths to check if one is contained in the other
    :arg: child: Path to test
    :arg parent; Path to test against
     """
    # 比较两个路径 判断parent是否包含child
    # 即child是parent的子文件夹
    test = False

    # 对两个路径做unfrack处理
    abs_child = unfrackpath(child, follow=False)
    abs_parent = unfrackpath(parent, follow=False)

    # real表示要解析符号链接
    if real:
        abs_child = os.path.realpath(abs_child)
        abs_parent = os.path.realpath(abs_parent)

    # 按照分隔符进行拆分
    c = abs_child.split(os.path.sep)
    p = abs_parent.split(os.path.sep)

    # 判断子路径的前len(p)个元素是否和p相同
    # 如果相同则说明是父子路径关系
    try:
        test = c[:len(p)] == p
    except IndexError:
        # child is shorter than parent so cannot be subpath
        # 如果索引报错则说明子路径比父路径还短，那就一定不是子路径
        pass

    return test
