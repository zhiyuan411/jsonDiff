#! /bin/env python
# encoding:utf8

import json
import re
from difflib import HtmlDiff

KEY_PREFIX_SEPARATOR = "."
VALUES_SEPARATOR = u"@@@"
DEFAULT_ENCODING = "UTF-8"
NOT_EXIST_FLAG = "__Not_Exist__"


def __merge_values(value1, value2):
    if isinstance(value1, (unicode, str)):
        value1 = "\"" + value1 + "\""
    if isinstance(value2, (unicode, str)):
        value2 = "\"" + value2 + "\""
    if value1 is None:
        value1 = u"Null"
    if value2 is None:
        value2 = u"Null"
    if not isinstance(value1, unicode):
        value1 = unicode(str(value1), DEFAULT_ENCODING)
    if not isinstance(value2, unicode):
        value2 = unicode(str(value2), DEFAULT_ENCODING)
    return value1 + VALUES_SEPARATOR + value2


def json_diff(json1, json2):
    """
    将2个json进行比较，找出差异，并存储为ignore文件
    :param json1: 第1遍运行时的request的json字符串
    :param json2: 第2遍运行时的request的json字符串
    :return: 有差异的键的绝对路径，以及该键在2个json中对应的值（这些信息是用于提供xts系统对使用者展示）
    """
    # todo: 入参校验
    # f1=open(file1_path)
    # f2=open(file2_path)
    # json1=f1.read()
    # json2=f2.read()
    # f1.close()
    # f2.close()
    # print type(json1), json1
    # print json2
    # print "\n+++++++++++++++\n"
    # print json1
    # print "\n+++++++++++++++\n"
    # print json2
    # print "\n+++++++++++++++\n"
    json_obj1 = json.loads(json1, encoding=DEFAULT_ENCODING)
    json_obj2 = json.loads(json2, encoding=DEFAULT_ENCODING)
    # print type(json_obj1), json_obj1
    # print type(json_obj2), json_obj2
    result = {}  # 差异结果dict
    result1 = {}
    result2 = {}
    __get_key_prefix_dict(None, result1, json_obj1)
    __get_key_prefix_dict(None, result2, json_obj2)
    # print "\n+++++++++++++++\n"
    # print result1
    # print "\n+++++++++++++++\n"
    # print result2
    # print "\n+++++++++++++++\n"
    # print type(result1["key1"].encode("utf-8"))
    # print result1["key1"].encode("utf-8") == "中文1"

    # 遍历得到的前缀key数组并进行比较,将不同记入结果dict
    for k in result1:
        if k in result2:
            # 均存在,比较值是否相同
            if not isinstance(result1[k], type(result2[k])) or result1[k] != result2[k]:
                result[k] = __merge_values(result1[k], result2[k])
        else:
            # 只在result1存在,记入差异结果dict
            result[k] = __merge_values(result1[k], NOT_EXIST_FLAG)

    for k in result2:
        if k not in result1:
            result[k] = __merge_values(NOT_EXIST_FLAG, result2[k])

    return result


def json_assert(expect_json, actual_json, absolute_ignore, relactive_ignore, value_ignore, is_disorder_array,
                is_full_compare, analyze_reference):
    """
    验证实际的json是否和期望的json相符
    :param expect_json: 期望的json字符串
    :param actual_json: 实际的json字符串
    :param absolute_ignore: 绝对路径表示的ignore集合;对性能几乎无影响
    :param relactive_ignore: 相对路径表示的ignore集合(正则形式);随着输入个数的增加,性能成线性下降
    :param value_ignore: 要忽略的value的集合(正则形式);随着输入个数的增加,性能成线性下降
    :param is_disorder_array: 是否需要无需比较数组;开启后性能下降,性能下降幅度取决于无序的结果个数和验证失败的个数,且随着数组的层级上升成n^2比例下降
    :param is_full_compare: 为false时只验证期望是否是实际的子集;为true时验证期望和实际为相等集;对性能几乎无影响
    :param analyze_reference: 是否对值为引用的情况进行解析并展开;开启后性能验证下降,建议仅对失败的结果使用该选项复查
    :return: 有差异的键的绝对路径，以及该键在2个json中对应的值
    """

    # todo: 入参校验
    # 对JSONP做兼容
    expect_json = expect_json.strip()
    actual_json = actual_json.strip()
    if not expect_json.startswith("{"):
        start_index = expect_json.find("(")
        end_index = expect_json.rfind(")")
        if end_index >= 0 and 0 <= start_index < end_index:
            expect_json = expect_json[start_index + 1:end_index]
    if not actual_json.startswith("{"):
        start_index = actual_json.find("(")
        end_index = actual_json.rfind(")")
        if end_index >= 0 and 0 <= start_index < end_index:
            actual_json = actual_json[start_index + 1:end_index]

    json_exp = json.loads(expect_json, encoding=DEFAULT_ENCODING)
    json_act = json.loads(actual_json, encoding=DEFAULT_ENCODING)
    result = {}
    result_exp = {}
    result_act = {}
    __get_key_prefix_dict(None, result_exp, json_exp)
    __get_key_prefix_dict(None, result_act, json_act)

    # 处理需要忽略的绝对路径(可以不存在)
    for abs_key in absolute_ignore:
        if not abs_key:
            continue
        if abs_key in result_exp:
            # print "ERROR"  # todo:
            # return None
            del result_exp[abs_key]
        if abs_key in result_act:
            del result_act[abs_key]

    # 处理需要忽略的相对路径(使用正则匹配,可以无匹配结果)
    for rel_key in relactive_ignore:
        if not rel_key:
            continue
        # 因为有删除操作,所以,使用dict.keys()来遍历
        for exp_key in result_exp.keys():
            if re.search(rel_key, exp_key):
                del result_exp[exp_key]
        for act_key in result_act.keys():
            if re.search(rel_key, act_key):
                del result_act[act_key]

    # 处理需要忽略的值的集合(使用正则匹配,可以无匹配结果)
    for ign_value in value_ignore:
        if not ign_value:
            continue
        # 因为有删除操作,所以,使用dict.keys()来遍历
        for exp_key in result_exp.keys():
            if not isinstance(result_exp[exp_key], unicode):
                value_exp = unicode(str(result_exp[exp_key]), DEFAULT_ENCODING)
            else:
                value_exp = result_exp[exp_key]
            if re.search(ign_value, value_exp):
                del result_exp[exp_key]
        for act_key in result_act.keys():
            if not isinstance(result_act[act_key], unicode):
                value_act = unicode(str(result_act[act_key]), DEFAULT_ENCODING)
            else:
                value_act = result_act[act_key]
            if re.search(ign_value, value_act):
                del result_act[act_key]

    # 递归地处理引用形式：xxx.xxx.$ref=$.xxx.xxx.xx[x].xxx
    if analyze_reference:
        REF_PARTERN = '\.\$ref$'
        # 处理期望结果dict
        has_recursive_reference = True
        while has_recursive_reference:
            has_recursive_reference = False
            for exp_key in result_exp.keys():
                # 匹配出引用形式，然后再循环匹配其值的前缀，然后替换前缀后，加入expand_rst数组
                if re.search(REF_PARTERN, exp_key):
                    ref_value = result_exp[exp_key][2:].replace('[', '.[')
                    if not ref_value:
                        # 例如内容为..即表示循环引用,类似这样的情况不做引用解析
                        continue
                    ref_value_pattern = u'^' + ref_value.replace('.', '\.').replace('[', '\[').replace(']', '\]')
                    replace_sucessful = False
                    for exp_key_inner in result_exp.keys():
                        if re.search(ref_value_pattern, exp_key_inner):
                            if re.search(REF_PARTERN, exp_key_inner):
                                # 说明为递归引用,被引用的地方仍然引用了其他地方
                                has_recursive_reference = True
                            # 解析后引用放到result_exp中，但是需要下轮大循环才能使用
                            result_exp[exp_key_inner.replace(ref_value, exp_key[0:-5], 1)] = result_exp[exp_key_inner]
                            replace_sucessful = True
                    if replace_sucessful:
                        del result_exp[exp_key]
                    else:
                        print exp_key

        # 处理实际结果dict
        has_recursive_reference = True
        while has_recursive_reference:
            has_recursive_reference = False
            for act_key in result_act.keys():
                # 匹配出引用形式，然后再循环匹配其值的前缀，然后替换前缀后，加入expand_rst数组
                if re.search(REF_PARTERN, act_key):
                    ref_value = result_act[act_key][2:].replace('[', '.[')
                    if not ref_value:
                        # 例如内容为..即表示循环引用,类似这样的情况不做引用解析
                        continue
                    ref_value_pattern = u'^' + ref_value.replace('.', '\.').replace('[', '\[').replace(']', '\]')
                    replace_sucessful = False
                    for act_key_inner in result_act.keys():
                        if re.search(ref_value_pattern, act_key_inner):
                            if re.search(REF_PARTERN, act_key_inner):
                                # 说明为递归引用,被引用的地方仍然引用了其他地方
                                has_recursive_reference = True
                            # 解析后引用放到result_act中，但是需要下轮大循环才能使用
                            result_act[act_key_inner.replace(ref_value, act_key[0:-5], 1)] = result_act[act_key_inner]
                            replace_sucessful = True
                    if replace_sucessful:
                        del result_act[act_key]
                    else:
                        print act_key

    # 区分数组比较方式,2种方法进行比较
    if is_disorder_array:
        # 无序比较数组,验证期望数据在实际中是否存在
        for exp_key in result_exp:
            # 直接验证存在的值是否相等,提高数组有序时的比较效率
            if exp_key in result_act:
                if result_exp[exp_key] == result_act[exp_key]:
                    continue
            # 进行数组的无序比较
            if not __disorder_array_assert(None, exp_key, result_exp[exp_key], result_act):
                # 无序比较存在不同,记录结果
                if exp_key in result_act:
                    result[exp_key] = __merge_values(result_exp[exp_key], result_act[exp_key])
                else:
                    result[exp_key] = __merge_values(result_exp[exp_key], NOT_EXIST_FLAG)
    else:
        # 有序比较数组,验证期望数据在实际中是否存在
        for exp_key in result_exp:
            if exp_key not in result_act:
                result[exp_key] = __merge_values(result_exp[exp_key], NOT_EXIST_FLAG)
            elif result_exp[exp_key] != result_act[exp_key]:
                result[exp_key] = __merge_values(result_exp[exp_key], result_act[exp_key])

    # 上面的比较是判断了期望包含的在实际结果的情况,相等判断则需要再添加不再期望中却在实际结果中的情况
    if is_full_compare:
        # 验证是否有实际数据在期望中不存在
        # fixme: 此处不支持数组无序比较
        for act_key in result_act:
            if act_key not in result_exp:
                result[act_key] = __merge_values(NOT_EXIST_FLAG, result_act[act_key])

    return result


def __get_key_prefix_dict(key_prefix, result, json_obj):
    if not isinstance(result, dict):
        print "输入参数错误:存储结果用的变量result类型错误."  # todo:
        return None

    if isinstance(json_obj, dict):
        # json串的情况,循环调用该Json串的所有键值
        if not json_obj:
            # dict为空,类似:"key":{},出口
            result[key_prefix] = "{}"
            return
        next_key_prefix = "" if (key_prefix is None) else (key_prefix + KEY_PREFIX_SEPARATOR)
        for (k, v) in json_obj.items():
            __get_key_prefix_dict(next_key_prefix + k, result, v)

    elif isinstance(json_obj, list):
        # json数组情况,循环调用该json数组的所有元素
        if not json_obj:
            # list为空,类似:"key":[],出口
            result[key_prefix] = "[]"
            return
        next_key_prefix = "" if (key_prefix is None) else (key_prefix + KEY_PREFIX_SEPARATOR)
        for i in range(0, len(json_obj)):
            __get_key_prefix_dict(next_key_prefix + "[" + str(i) + "]", result, json_obj[i])

    else:
        # 基本元素,即递归函数出口,得到一个结果放入结果dict
        result[key_prefix] = json_obj


def __disorder_array_assert(key_prefix, exp_key, exp_value, result_act):
    array_begin = exp_key.find("[")
    if array_begin < 0:
        # 递归出口:不含有数组,直接进行比较即可
        full_key = ("" if key_prefix is None else key_prefix) + exp_key
        if full_key in result_act:
            if exp_value == result_act[full_key]:
                return True
            else:
                return False
        else:
            return False
    else:
        # 将最上层的数组循环进行处理,递归调用求解
        array_end = exp_key.find("]")
        if array_end < array_begin:
            print "ERROR"  # todo:
            return None
        array_prefix = ("" if key_prefix is None else key_prefix) + exp_key[0:array_begin + 1]
        array_postfix = exp_key[array_end:]
        i = 0
        while True:
            array_full = array_prefix + str(i) + array_postfix
            if array_full in result_act:
                # 期望中存在对应的数组原因,递归调用进行比较
                if __disorder_array_assert(array_prefix + str(i) + "]", array_postfix[1:], exp_value, result_act):
                    return True
            else:
                # 数组越界
                return False
            i += 1


def generate_html(json_left, json_right, left_url, right_url):

    # 对JSONP做兼容
    json_left = json_left.strip()
    json_right = json_right.strip()
    if not json_left.startswith("{"):
        start_index = json_left.find("(")
        end_index = json_left.rfind(")")
        if end_index >= 0 and 0 <= start_index < end_index:
            json_left = json_left[start_index + 1:end_index]
    if not json_right.startswith("{"):
        start_index = json_right.find("(")
        end_index = json_right.rfind(")")
        if end_index >= 0 and 0 <= start_index < end_index:
            json_right = json_right[start_index + 1:end_index]

    # 对输入做格式化
    json_left = json.dumps(json.loads(json_left), indent=4).decode('raw_unicode_escape')
    json_left_list = json_left.splitlines()
    json_right = json.dumps(json.loads(json_right), indent=4).decode('raw_unicode_escape')
    json_right_list = json_right.splitlines()

    res_tmp = HtmlDiff().make_file(json_left_list,
                                   json_right_list,
                                   fromdesc='<a href="' + left_url + '" target="_blank">' + left_url + '</a>',
                                   todesc='<a href="' + right_url + '" target="_blank">' + right_url + '</a>',
                                   context=False)

    # 对原生脚本生成的HTML文件的进一步处理
    page_to_process = res_tmp.replace('charset=ISO-8859-1', 'charset=UTF-8')

    result = ''
    page_to_list = page_to_process.encode('utf-8').splitlines()
    for line in page_to_list:
        if line.find('difflib_chg_to0__0') > 0:
            result = result + '\n' + line
        elif line.find('<a href=') > 0:
            result = result + '\n' + line.replace('<tr>', '<tr class="diff_next">')
        elif line.find('<span class="diff_sub">') > 0:
            result = result + '\n' + line.replace('<tr>', '<tr class="diff_sub">')
        elif line.find('<span class="diff_add">') > 0:
            result = result + '\n' + line.replace('<tr>', '<tr class="diff_add">')
        else:
            result = result + '\n' + line

    return result
