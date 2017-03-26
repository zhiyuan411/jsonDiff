#!/usr/bin/python
# encoding:utf-8


import ConfigParser
import json
import os
import time
import traceback
import urllib2

import datetime

from JsonUtils import json_assert, generate_html


class JsonDiffTool:
    def __init__(self):
        ###########################################
        # Global Parameters
        # 从profile.cfg中获取相关配置参数
        self.conf = ConfigParser.ConfigParser()
        self.conf.read('profile.cfg')

        self.mode = self.conf.get('Global', 'MODE')
        self.data_path = self.conf.get('Global', 'DATA_PATH')
        if not os.path.isdir(self.data_path):
            raise Exception("DATA_PATH: " + self.data_path + " NOT exist, please check it.")
        if not self.data_path.endswith('/') and not self.data_path.endswith('\\'):
            self.data_path = '%s%s' % (self.data_path, os.path.sep)
        self.html_sum_file = self.data_path + self.conf.get('Global', 'HTML_SUM_FILE')
        self.max_count_to_process = self.conf.getint('Global', 'MAX_COUNT_TO_PROCESS')
        self.absolute_ignore = self.conf.get('Global', 'ABSOLUTE_IGNORE').replace(' ', '').split(';')
        self.relactive_ignore = self.conf.get('Global', 'RELACTIVE_IGNORE').replace(' ', '').split(';')
        self.value_ignore = self.conf.get('Global', 'VALUE_IGNORE').replace(' ', '').split(';')
        self.is_disorder_array = (self.conf.get('Global', 'IS_DISORDER_ARRAY').lower() == "true")
        self.is_full_compare = (self.conf.get('Global', 'IS_FULL_COMPARE').lower() != "false")
        self.analyze_reference = (self.conf.get('Global', 'ANALYZE_REFERENCE').lower() == "true")
        self.diff_results_file = self.data_path + self.conf.get('Global', 'DIFF_RESULTS_FILE')
        self.exception_results_file = self.data_path + self.conf.get('Global', 'EXCEPTION_RESULTS_FILE')

        self.hostname_1 = self.conf.get('QueryDiff', 'HOSTNAME_1')
        self.hostname_2 = self.conf.get('QueryDiff', 'HOSTNAME_2')
        self.sleep_time = self.conf.getfloat('QueryDiff', 'SLEEP_TIME')
        self.url_ignore_words = self.conf.get('QueryDiff', 'URL_IGNORE_WORDS').replace(' ', '').split(';')
        self.url_filter_words = self.conf.get('QueryDiff', 'URL_FILTER_WORDS').replace(' ', '').split(';')
        self.request_file = self.data_path + self.conf.get('QueryDiff', 'REQUEST_FILE')
        self.same_result_urls = self.data_path + self.conf.get('QueryDiff', 'SAME_RESULT_URLS')
        self.retry_urls = self.data_path + self.conf.get('QueryDiff', 'RETRY_URLS')
        self.exception_urls = self.data_path + self.conf.get('QueryDiff', 'EXCEPTION_URLS')
        self.skipped_urls = self.data_path + self.conf.get('QueryDiff', 'SKIPPED_URLS')

        self.json_data_file_1 = self.data_path + self.conf.get('JsonDataDiff', 'JSON_DATA_FILE_1')
        self.json_data_file_2 = self.data_path + self.conf.get('JsonDataDiff', 'JSON_DATA_FILE_2')
        self.retry_json_data_1 = self.data_path + self.conf.get('JsonDataDiff', 'RETRY_JSON_DATA_1')
        self.retry_json_data_2 = self.data_path + self.conf.get('JsonDataDiff', 'RETRY_JSON_DATA_2')
        self.exception_json_data_1 = self.data_path + self.conf.get('JsonDataDiff', 'EXCEPTION_JSON_DATA_1')
        self.exception_json_data_2 = self.data_path + self.conf.get('JsonDataDiff', 'EXCEPTION_JSON_DATA_2')

        self.BUFFER_SIZE = 1024 * 50

        self.total_line_num = 0  # 保存url当前记录数
        ###########################################

    def __get_json(self, url):

        request = urllib2.Request(url)
        response = urllib2.urlopen(request)
        page = response.read()

        return page

    def __log_print(self, desc, times):
        print self.total_line_num, ":", desc, "(", times, ")"

    def query_diff(self):
        request_file_obj = open(self.request_file, 'r')
        diff_results_file_obj = open(self.diff_results_file, 'w')
        exception_results_file_obj = open(self.exception_results_file, 'w')
        same_result_urls_obj = open(self.same_result_urls, 'w')
        retry_urls_obj = open(self.retry_urls, 'w')
        exception_urls_obj = open(self.exception_urls, 'w')
        skipped_urls_obj = open(self.skipped_urls, 'w')

        # 清理目录下的html结果文件
        for sonfile in os.listdir(self.data_path):
            if sonfile.endswith(".html"):
                os.remove(self.data_path + sonfile)

        try:
            while True:

                # 判断发送请求个数是否到达指定个数
                if not self.max_count_to_process == -1:
                    if self.total_line_num >= self.max_count_to_process:
                        break

                # 每次读取一批数据做处理
                lines = request_file_obj.readlines(self.BUFFER_SIZE)
                if len(lines) <= 0:
                    break

                for line in lines:
                    self.total_line_num += 1
                    begin = datetime.datetime.now()

                    # 跳过空行
                    line = line.strip()
                    if not line:
                        self.__log_print("url is skipped", datetime.datetime.now() - begin)
                        skipped_urls_obj.write(line + "\n")
                        continue

                    # 过滤url的白名单关键字
                    if len(self.url_filter_words) > 0:
                        has_filter_flag = False
                        for url_filter_word in self.url_filter_words:
                            if url_filter_word in line:
                                has_filter_flag = True
                                break
                        if not has_filter_flag:
                            self.__log_print("url is skipped", datetime.datetime.now() - begin)
                            skipped_urls_obj.write(line + "\n")
                            continue

                    # 过滤url的忽略关键字
                    has_ignore_flag = False
                    for url_ignore_word in self.url_ignore_words:
                        if url_ignore_word in line:
                            has_ignore_flag = True
                            break
                    if has_ignore_flag:
                        self.__log_print("url is skipped", datetime.datetime.now() - begin)
                        skipped_urls_obj.write(line + "\n")
                        continue

                    left_url = self.hostname_1 + line
                    right_url = self.hostname_2 + line

                    try:
                        left_json = self.__get_json(left_url)
                        right_json = self.__get_json(right_url)

                    except Exception, e:
                        # http请求失败,继续下一条请求
                        self.__log_print("request failed", datetime.datetime.now() - begin)
                        exception_urls_obj.write(line + "\n")
                        exception_results_file_obj.write("=" + str(self.total_line_num) + "=\n")
                        exception_results_file_obj.writelines(e.message + "\n")
                        exception_results_file_obj.writelines(traceback.format_exc())
                        continue

                    try:
                        diff_result = json_assert(left_json, right_json, self.absolute_ignore, self.relactive_ignore,
                                                  self.value_ignore, self.is_disorder_array, self.is_full_compare,
                                                  self.analyze_reference)
                    except Exception, e:
                        self.__log_print("response is NOT json", datetime.datetime.now() - begin)
                        exception_urls_obj.write(line + "\n")
                        exception_results_file_obj.write("=" + str(self.total_line_num) + "=\n")
                        exception_results_file_obj.writelines(e.message + "\n")
                        exception_results_file_obj.writelines(traceback.format_exc())
                        continue

                    if diff_result:
                        # 获取html格式的差异结果
                        self.__log_print("response is different", datetime.datetime.now() - begin)
                        html_diff_result = generate_html(left_json, right_json, left_url, right_url)
                        out_file = '%s%s%s%s%s' % (
                            self.data_path, 'lineNum_', str(self.total_line_num), '_diffResult', '.html')
                        out_file_obj = open(out_file, 'w')
                        try:
                            out_file_obj.write(html_diff_result)
                        finally:
                            out_file_obj.close()
                        retry_urls_obj.write(line + "\n")
                        diff_results_file_obj.write("=" + str(self.total_line_num) + "=\n")
                        diff_results_file_obj.write(json.dumps(diff_result, indent=4) + "\n")

                    else:
                        self.__log_print("response is same", datetime.datetime.now() - begin)
                        same_result_urls_obj.write(line + "\n")

                    # 限速
                    if self.sleep_time != 0:
                        time.sleep(self.sleep_time)
        finally:
            request_file_obj.close()
            diff_results_file_obj.close()
            exception_results_file_obj.close()
            same_result_urls_obj.close()
            retry_urls_obj.close()
            exception_urls_obj.close()
            skipped_urls_obj.close()

        # 合并html结果文件
        html_sum_file_obj = open(self.html_sum_file, 'w')
        for sonfile in os.listdir(self.data_path):
            if sonfile.endswith("_diffResult.html"):
                sonfile_obj = open(self.data_path + sonfile, 'r')
                html_sum_file_obj.write(sonfile_obj.read())
                html_sum_file_obj.write("\n\n")
                sonfile_obj.close()
        html_sum_file_obj.close()

    def json_data_diff(self):
        json_data_file_1_obj = open(self.json_data_file_1, 'r')
        json_data_file_2_obj = open(self.json_data_file_2, 'r')
        diff_results_file_obj = open(self.diff_results_file, 'w')
        exception_results_file_obj = open(self.exception_results_file, 'w')
        retry_json_data_1_obj = open(self.retry_json_data_1, 'w')
        retry_json_data_2_obj = open(self.retry_json_data_2, 'w')
        exception_json_data_1_obj = open(self.exception_json_data_1, 'w')
        exception_json_data_2_obj = open(self.exception_json_data_2, 'w')

        # 清理目录下的html结果文件
        for sonfile in os.listdir(self.data_path):
            if sonfile.endswith(".html"):
                os.remove(self.data_path + sonfile)

        try:
            while True:

                # 判断发送请求个数是否到达指定个数
                if not self.max_count_to_process == -1:
                    if self.total_line_num >= self.max_count_to_process:
                        break

                # 每次读取一批数据做处理
                lines1 = json_data_file_1_obj.readlines(self.BUFFER_SIZE)
                lines2 = json_data_file_2_obj.readlines(self.BUFFER_SIZE)
                if len(lines1) <= 0 or len(lines2) <= 0:
                    break

                total = len(lines2) if len(lines1) > len(lines2) else len(lines1)

                for i in range(total):
                    self.total_line_num += 1
                    begin = datetime.datetime.now()

                    # 提取待比较的字符串
                    left_json = lines1[i]
                    right_json = lines2[i]

                    # 跳过空行
                    left_json = left_json.strip()
                    right_json = right_json.strip()
                    if not left_json or not right_json:
                        self.__log_print("json is skipped", datetime.datetime.now() - begin)
                        continue

                    try:
                        diff_result = json_assert(left_json, right_json, self.absolute_ignore, self.relactive_ignore,
                                                  self.value_ignore, self.is_disorder_array, self.is_full_compare,
                                                  self.analyze_reference)
                    except Exception, e:
                        self.__log_print("json format is wrong", datetime.datetime.now() - begin)
                        exception_json_data_1_obj.write("=" + str(self.total_line_num) + "=\n")
                        exception_json_data_1_obj.write(left_json + "\n")
                        exception_json_data_2_obj.write("=" + str(self.total_line_num) + "=\n")
                        exception_json_data_2_obj.write(right_json + "\n")
                        exception_results_file_obj.write("=" + str(self.total_line_num) + "=\n")
                        exception_results_file_obj.writelines(e.message + "\n")
                        exception_results_file_obj.writelines(traceback.format_exc())
                        continue

                    if diff_result:
                        # 获取html格式的差异结果
                        json_data_index = self.json_data_file_1.rfind(os.path.sep)
                        json_data_name_1 = self.json_data_file_1[json_data_index + 1:]
                        json_data_index = self.json_data_file_2.rfind(os.path.sep)
                        json_data_name_2 = self.json_data_file_2[json_data_index + 1:]
                        self.__log_print("json is different", datetime.datetime.now() - begin)
                        html_diff_result = generate_html(left_json, right_json, json_data_name_1,
                                                         json_data_name_2)
                        out_file = '%s%s%s%s%s' % (
                            self.data_path, 'lineNum_', str(self.total_line_num), '_diffResult', '.html')
                        out_file_obj = open(out_file, 'w')
                        try:
                            out_file_obj.write(html_diff_result)
                        finally:
                            out_file_obj.close()
                        retry_json_data_1_obj.write(left_json + "\n")
                        retry_json_data_2_obj.write(right_json + "\n")
                        diff_results_file_obj.write("=" + str(self.total_line_num) + "=\n")
                        diff_results_file_obj.write(json.dumps(diff_result, indent=4) + "\n")

                    else:
                        self.__log_print("json is same", datetime.datetime.now() - begin)

                    # 限速
                    if self.sleep_time != 0:
                        time.sleep(self.sleep_time)
        finally:
            json_data_file_1_obj.close()
            json_data_file_2_obj.close()
            diff_results_file_obj.close()
            exception_results_file_obj.close()
            retry_json_data_1_obj.close()
            retry_json_data_2_obj.close()
            exception_json_data_1_obj.close()
            exception_json_data_2_obj.close()

        # 合并html结果文件
        html_sum_file_obj = open(self.html_sum_file, 'w')
        for sonfile in os.listdir(self.data_path):
            if sonfile.endswith("_diffResult.html"):
                sonfile_obj = open(self.data_path + sonfile, 'r')
                html_sum_file_obj.write(sonfile_obj.read())
                html_sum_file_obj.write("\n\n")
                sonfile_obj.close()
        html_sum_file_obj.close()


# 运行的入口
if __name__ == '__main__':
    jd = JsonDiffTool()
    if jd.mode.lower() == "query":
        jd.query_diff()
    elif jd.mode.lower() == "jsondata":
        jd.json_data_diff()
    else:
        print "mode is unknown."