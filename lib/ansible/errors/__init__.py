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

import re
import traceback

from collections.abc import Sequence

from ansible.errors.yaml_strings import (
    YAML_COMMON_DICT_ERROR,
    YAML_COMMON_LEADING_TAB_ERROR,
    YAML_COMMON_PARTIALLY_QUOTED_LINE_ERROR,
    YAML_COMMON_UNBALANCED_QUOTES_ERROR,
    YAML_COMMON_UNQUOTED_COLON_ERROR,
    YAML_COMMON_UNQUOTED_VARIABLE_ERROR,
    YAML_POSITION_DETAILS,
    YAML_AND_SHORTHAND_ERROR,
)
from ansible.module_utils.common.text.converters import to_native, to_text


class AnsibleError(Exception):
    '''
    This is the base class for all errors raised from Ansible code,
    and can be instantiated with two optional parameters beyond the
    error message to control whether detailed information is displayed
    when the error occurred while parsing a data file of some kind.

    Usage:

        raise AnsibleError('some message here', obj=obj, show_content=True)

    Where "obj" is some subclass of ansible.parsing.yaml.objects.AnsibleBaseYAMLObject,
    which should be returned by the DataLoader() class.
    '''

    def __init__(self, message="", obj=None, show_content=True, suppress_extended_error=False, orig_exc=None):
        super(AnsibleError, self).__init__(message)

        self._show_content = show_content
        self._suppress_extended_error = suppress_extended_error
        self._message = to_native(message)
        self.obj = obj
        self.orig_exc = orig_exc


    # @property装饰器
    # 帮一些属性更为简便地添加getter、setter、deleter
    # class C(object):
    #   _x = None
    #   @property 
    #   def x(self):
    #     return self._x
    #   @x.setter 
    #   def x(self, value):
    #     self._x = abs(value)
    #   @x.deleter 
    #   def x(self):
    #     del self._x

    #   c = C()
    #   c.x = -1
    #   print(c.x)
    # 可以看到在赋值时调用了setter将绝对值赋给了x

    # 如果将setter去掉则会报错提示x属性没有setter方法（即只读变量）
    # AttributeError: property 'x' of 'C' object has no setter
    @property
    def message(self):
        # we import this here to prevent an import loop problem,
        # since the objects code also imports ansible.errors
        from ansible.parsing.yaml.objects import AnsibleBaseYAMLObject

        message = [self._message]
        # 如果传入的obj是AnsibleBaseYAMLObject的子类
        # 用_get_extended_error这个方法把错误信息提取出来
        if isinstance(self.obj, AnsibleBaseYAMLObject):
            extended_error = self._get_extended_error()
            if extended_error and not self._suppress_extended_error:
                message.append(
                    '\n\n%s' % to_native(extended_error)
                )
        # 如果传入的obj不是AnsibleBaseYAMLObject的子类
        # 将orig_exc即original exception的信息提取出来
        elif self.orig_exc:
            message.append('. %s' % to_native(self.orig_exc))

        return ''.join(message)

    @message.setter
    def message(self, val):
        self._message = val

    def __str__(self):
        return self.message

    def __repr__(self):
        return self.message


    # 这个方法用来获取发生错误的行以及它的前一行内容
    def _get_error_lines_from_file(self, file_name, line_number):
        '''
        Returns the line in the file which corresponds to the reported error
        location, as well as the line preceding it (if the error did not
        occur on the first line), to provide context to the error.
        '''

        target_line = ''
        prev_line = ''

        with open(file_name, 'r') as f:
            lines = f.readlines()
            # 如果行数超范围的话，会返回最后一行
            # In case of a YAML loading error, PyYAML will report the very last line
            # as the location of the error. Avoid an index error here in order to
            # return a helpful message.
            file_length = len(lines)
            if line_number >= file_length:
                line_number = file_length - 1

            # 如果选择的行是空行的话，一直向上找到不是空行的行返回
            # If target_line contains only whitespace, move backwards until
            # actual code is found. If there are several empty lines after target_line,
            # the error lines would just be blank, which is not very helpful.
            target_line = lines[line_number]
            while not target_line.strip():
                line_number -= 1
                target_line = lines[line_number]

            # 找到目标行的上一行
            if line_number > 0:
                prev_line = lines[line_number - 1]

        return (target_line, prev_line)


    # 这个函数用来显示报错的行内容，指出错误位置的'^'
    # 对于常见的语法错误给出原因和修改建议
    def _get_extended_error(self):
        '''
        Given an object reporting the location of the exception in a file, return
        detailed information regarding it including:

          * the line which caused the error as well as the one preceding it
          * causes and suggested remedies for common syntax errors

        If this error was created with show_content=False, the reporting of content
        is suppressed, as the file contents may be sensitive (ie. vault data).
        '''

        error_message = ''

        try:
            (src_file, line_number, col_number) = self.obj.ansible_pos
            
            # YAML_POSITION_DETAILS：一个用来作为输出模板的字符串
            # YAML_POSITION_DETAILS = """\
            #     The error appears to be in '%s': line %s, column %s, but may
            #     be elsewhere in the file depending on the exact syntax problem.
            # """
            error_message += YAML_POSITION_DETAILS % (src_file, line_number, col_number) # 文件名，行数，列数

            # 这里and前面的这个判断条件没看懂，后面那个是说只有在这个Error类的_show_content属性为True时才会显示详细的错误信息
            if src_file not in ('<string>', '<unicode>') and self._show_content:
                (target_line, prev_line) = self._get_error_lines_from_file(src_file, line_number - 1)
                target_line = to_text(target_line)
                prev_line = to_text(prev_line)
                if target_line:
                    stripped_line = target_line.replace(" ", "")

                    # Check for k=v syntax in addition to YAML syntax and set the appropriate error position,
                    # arrow index
                    # 判断前一行中是否有赋值表达式，即类似于"a=b"、"a = b"、"a= b"的形式
                    if re.search(r'\w+(\s+)?=(\s+)?[\w/-]+', prev_line):
                        # 如果有赋值表达式的话，找到等号的位置
                        error_position = prev_line.rstrip().find('=')
                        # 根据等号的位置，新建一行带箭头的指示行
                        arrow_line = (" " * error_position) + "^ here"
                        # 组装的错误信息类似下面这样
                        # 
                        # The error appears to be in 'src_file': line line_number - 1, column error_position + 1, but may
                        # be elsewhere in the file depending on the exact syntax problem.
                        # 
                        # The offending line appears to be:
                        # 
                        # a = b
                        #   ^ here
                        # 
                        # There appears to be both 'k=v' shorthand syntax and YAML in this task. Only one syntax may be used.
                        error_message = YAML_POSITION_DETAILS % (src_file, line_number - 1, error_position + 1)
                        error_message += "\nThe offending line appears to be:\n\n%s\n%s\n\n" % (prev_line.rstrip(), arrow_line)
                        error_message += YAML_AND_SHORTHAND_ERROR
                    # 如果没有赋值表达式的话，按照col_number指出错误位置返回
                    else:
                        arrow_line = (" " * (col_number - 1)) + "^ here"
                        error_message += "\nThe offending line appears to be:\n\n%s\n%s\n%s\n" % (prev_line.rstrip(), target_line.rstrip(), arrow_line)

                    # TODO: There may be cases where there is a valid tab in a line that has other errors.
                    # yaml不支持'\t'，如果有的话也会报错
                    if '\t' in target_line:
                        error_message += YAML_COMMON_LEADING_TAB_ERROR
                    # common error/remediation checking here:
                    # check for unquoted vars starting lines
                    # 如果在目标行同时存在{{和}}，但是却没有用引号括起来，也会报错
                    if ('{{' in target_line and '}}' in target_line) and ('"{{' not in target_line or "'{{" not in target_line):
                        error_message += YAML_COMMON_UNQUOTED_VARIABLE_ERROR
                    # check for common dictionary mistakes
                    # 和上一个问题类似{{ value }}要用引号括起来
                    elif ":{{" in stripped_line and "}}" in stripped_line:
                        error_message += YAML_COMMON_DICT_ERROR
                    # check for common unquoted colon mistakes
                    # 存在多个冒号的问题
                    elif (len(target_line) and
                            len(target_line) > 1 and
                            len(target_line) > col_number and
                            target_line[col_number] == ":" and
                            target_line.count(':') > 1):
                        error_message += YAML_COMMON_UNQUOTED_COLON_ERROR
                    # otherwise, check for some common quoting mistakes
                    else:
                        # FIXME: This needs to split on the first ':' to account for modules like lineinfile
                        # that may have lines that contain legitimate colons, e.g., line: 'i ALL= (ALL) NOPASSWD: ALL'
                        # and throw off the quote matching logic.
                        parts = target_line.split(":")
                        # 将目标行按冒号拆分
                        # 如果拆分结果多于1个，也就是说至少一个冒号出现在字符串中间了
                        # 但是按照上一个elif的条件，应该最多只有一个冒号
                        if len(parts) > 1:
                            # middle是冒号后面的内容
                            middle = parts[1].strip()
                            match = False
                            unbalanced = False

                            # 如果middle以引号开头却不以引号结尾
                            # 即要求冒号后的内容必须由一对引号包裹
                            if middle.startswith("'") and not middle.endswith("'"):
                                match = True
                            elif middle.startswith('"') and not middle.endswith('"'):
                                match = True

                            # 这里的判断相当于，一行之内必须有某一种引号只有一对
                            # 例如可以使用双引号括起来整个语句，然后语句内所有引号都是用单引号，这样是可行的
                            # 如果都使用双引号则会造成混乱
                            if (len(middle) > 0 and
                                    middle[0] in ['"', "'"] and
                                    middle[-1] in ['"', "'"] and
                                    target_line.count("'") > 2 or
                                    target_line.count('"') > 2):
                                unbalanced = True

                            # 根据引号的情况返回对应的错误提示信息
                            if match:
                                error_message += YAML_COMMON_PARTIALLY_QUOTED_LINE_ERROR
                            if unbalanced:
                                error_message += YAML_COMMON_UNBALANCED_QUOTES_ERROR

        # 文件IO出错
        except (IOError, TypeError):
            error_message += '\n(could not open file to display line)'
        # 索引行超界
        except IndexError:
            error_message += '\n(specified line no longer in file, maybe it changed?)'

        return error_message


class AnsiblePromptInterrupt(AnsibleError):
    '''User interrupt'''


class AnsiblePromptNoninteractive(AnsibleError):
    '''Unable to get user input'''


class AnsibleAssertionError(AnsibleError, AssertionError):
    '''Invalid assertion'''
    pass


class AnsibleOptionsError(AnsibleError):
    ''' bad or incomplete options passed '''
    pass


class AnsibleRequiredOptionError(AnsibleOptionsError):
    ''' bad or incomplete options passed '''
    pass


class AnsibleParserError(AnsibleError):
    ''' something was detected early that is wrong about a playbook or data file '''
    pass


class AnsibleInternalError(AnsibleError):
    ''' internal safeguards tripped, something happened in the code that should never happen '''
    pass


class AnsibleRuntimeError(AnsibleError):
    ''' ansible had a problem while running a playbook '''
    pass


class AnsibleModuleError(AnsibleRuntimeError):
    ''' a module failed somehow '''
    pass


class AnsibleConnectionFailure(AnsibleRuntimeError):
    ''' the transport / connection_plugin had a fatal error '''
    pass


class AnsibleAuthenticationFailure(AnsibleConnectionFailure):
    '''invalid username/password/key'''
    pass


class AnsibleCallbackError(AnsibleRuntimeError):
    ''' a callback failure '''
    pass


class AnsibleTemplateError(AnsibleRuntimeError):
    '''A template related error'''
    pass


class AnsibleFilterError(AnsibleTemplateError):
    ''' a templating failure '''
    pass


class AnsibleLookupError(AnsibleTemplateError):
    ''' a lookup failure '''
    pass


class AnsibleUndefinedVariable(AnsibleTemplateError):
    ''' a templating failure '''
    pass

# 未找到文件报错
class AnsibleFileNotFound(AnsibleRuntimeError):
    ''' a file missing failure '''

    def __init__(self, message="", obj=None, show_content=True, suppress_extended_error=False, orig_exc=None, paths=None, file_name=None):

        self.file_name = file_name
        self.paths = paths

        if message:
            message += "\n"
        if self.file_name:
            message += "Could not find or access '%s'" % to_text(self.file_name)
        else:
            message += "Could not find file"

        # 如果传入的路径是一个序列的话，把它拆成一个列表展示出来，类似下面这样：
        # Searched in:
        #     dir1
        #     dir2
        #     dir3
        #     dir4 on the Ansible Controller.
        # If you are using a module and expect the file to exist on the remote, see the remote_src option

        if self.paths and isinstance(self.paths, Sequence):
            searched = to_text('\n\t'.join(self.paths))
            if message:
                message += "\n"
            message += "Searched in:\n\t%s" % searched

        message += " on the Ansible Controller.\nIf you are using a module and expect the file to exist on the remote, see the remote_src option"

        super(AnsibleFileNotFound, self).__init__(message=message, obj=obj, show_content=show_content,
                                                  suppress_extended_error=suppress_extended_error, orig_exc=orig_exc)


# 既然下面是临时的就先跳过了
# These Exceptions are temporary, using them as flow control until we can get a better solution.
# DO NOT USE as they will probably be removed soon.
# We will port the action modules in our tree to use a context manager instead.
class AnsibleAction(AnsibleRuntimeError):
    ''' Base Exception for Action plugin flow control '''

    def __init__(self, message="", obj=None, show_content=True, suppress_extended_error=False, orig_exc=None, result=None):

        super(AnsibleAction, self).__init__(message=message, obj=obj, show_content=show_content,
                                            suppress_extended_error=suppress_extended_error, orig_exc=orig_exc)
        if result is None:
            self.result = {}
        else:
            self.result = result


class AnsibleActionSkip(AnsibleAction):
    ''' an action runtime skip'''

    def __init__(self, message="", obj=None, show_content=True, suppress_extended_error=False, orig_exc=None, result=None):
        super(AnsibleActionSkip, self).__init__(message=message, obj=obj, show_content=show_content,
                                                suppress_extended_error=suppress_extended_error, orig_exc=orig_exc, result=result)
        self.result.update({'skipped': True, 'msg': message})


class AnsibleActionFail(AnsibleAction):
    ''' an action runtime failure'''
    def __init__(self, message="", obj=None, show_content=True, suppress_extended_error=False, orig_exc=None, result=None):
        super(AnsibleActionFail, self).__init__(message=message, obj=obj, show_content=show_content,
                                                suppress_extended_error=suppress_extended_error, orig_exc=orig_exc, result=result)
        self.result.update({'failed': True, 'msg': message, 'exception': traceback.format_exc()})


class _AnsibleActionDone(AnsibleAction):
    ''' an action runtime early exit'''
    pass


class AnsiblePluginError(AnsibleError):
    ''' base class for Ansible plugin-related errors that do not need AnsibleError contextual data '''
    def __init__(self, message=None, plugin_load_context=None):
        super(AnsiblePluginError, self).__init__(message)
        self.plugin_load_context = plugin_load_context


class AnsiblePluginRemovedError(AnsiblePluginError):
    ''' a requested plugin has been removed '''
    pass


class AnsiblePluginCircularRedirect(AnsiblePluginError):
    '''a cycle was detected in plugin redirection'''
    pass


class AnsibleCollectionUnsupportedVersionError(AnsiblePluginError):
    '''a collection is not supported by this version of Ansible'''
    pass


class AnsibleFilterTypeError(AnsibleTemplateError, TypeError):
    ''' a Jinja filter templating failure due to bad type'''
    pass


class AnsiblePluginNotFound(AnsiblePluginError):
    ''' Indicates we did not find an Ansible plugin '''
    pass
