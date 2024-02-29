# -*- coding:utf-8 -*-
# author: HPCM
# time: 2022/2/23 14:31
# file: renders.py
import os
import logging
from datetime import datetime
from collections import OrderedDict

import pandas as pd
from django.conf import settings
from rest_framework import renderers, serializers


class SerializerReadMapping(object):
    """序列化器数据转换"""

    def __init__(self, data, context, is_map=True):
        self.data = data
        self.context = context
        self.is_map = is_map

    # noinspection PyProtectedMember
    def serializer_read_fields(self, ser):
        mappings = OrderedDict()
        ignore_fields = getattr(ser.Meta, "render_ignore_fields", [])
        for field in ser.fields.values():
            if field.field_name not in ser.Meta.fields:
                continue
            if field.write_only or field.field_name in ignore_fields:
                continue
            if field.field_name in ser._declared_fields and isinstance(field, serializers.Serializer):
                mappings[field.field_name] = self.serializer_read_fields(field)
            else:
                mappings[field.field_name] = field.label
        return mappings

    # noinspection PyAttributeOutsideInit
    @property
    def mappings(self):
        if not hasattr(self, "_mappings"):
            ser = self.context["view"].get_serializer_class()()
            self._mappings = self.serializer_read_fields(ser)
        return self._mappings

    def parse_items(self, mappings, attrs):
        items = OrderedDict()
        for k in attrs:
            if k not in mappings:
                continue
            if isinstance(mappings[k], dict):
                [items.setdefault(x, y) for x, y in self.parse_items(mappings[k], attrs[k]).items()]
            else:
                items[mappings[k]] = attrs[k]
        return items

    def mappings_empty_values(self, mappings):
        items = OrderedDict()
        for k in mappings:
            if isinstance(mappings[k], dict):
                [items.setdefault(x, y) for x, y in self.no_mapping_empty_values(mappings[k]).items()]
            else:
                items[mappings[k]] = ""
        return items

    def no_mapping_empty_values(self, mappings):
        """下发空数据, 也就是模板"""
        items = OrderedDict()
        for k in mappings:
            if isinstance(mappings[k], dict):
                [items.setdefault(x, y) for x, y in self.no_mapping_empty_values(mappings[k]).items()]
            else:
                items[k] = ""
        return items

    def extra_data(self):
        # 常规drf结构, 不需要这个data
        if "data" in self.data:
            self.data = self.data["data"]
        if "results" in self.data:
            self.data = self.data["results"]
        self.data = pd.DataFrame(self.data)

    def parse(self):
        logging.info("进入序列化转换阶段")
        self.extra_data()
        if self.data.empty:
            return pd.DataFrame([self.mappings_empty_values(self.mappings)])
        if self.is_map:
            self.data.rename(columns=self.mappings, inplace=True)
        self.data.replace({None: ""})
        logging.info("序列化数据转换完成")
        return self.data


class ExcelWriter(object):
    """直接渲染数据"""

    def __init__(self, filename, data, context):
        self.filename = filename
        self.context = context
        self.data = pd.DataFrame(data)

    @property
    def local_filename(self):
        base_dir = settings.DOWNLOAD_CACHE_PATH
        if not os.path.exists(base_dir):
            os.mkdir(base_dir)
        return os.path.join(base_dir, self.filename)

    def write(self):
        self.data.to_excel(self.local_filename, index=False)

    def render_response(self):
        self.context["response"]["Content-Type"] = "application/octet-stream"
        self.context["response"][
            "Content-Disposition"] = f"attachment; filename=\"{self.filename.encode('utf-8').decode('ISO-8859-1')}\""
        logging.info(self.context["response"]["Content-Disposition"])
        with open(self.local_filename, "rb") as fp:
            return fp.read()

    def render(self):
        logging.info(f"已写入文件: {self.filename}")
        self.write()
        return self.render_response()


class DefaultExcelRender(renderers.BaseRenderer):
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    format = "xlsx"
    charset = 'utf-8'
    render_style = 'binary'
    writer = ExcelWriter
    parser = SerializerReadMapping

    def render(self, data, accepted_media_type=None, renderer_context=None):
        view = renderer_context["view"]
        filename = getattr(renderer_context["view"], "DOWNLOAD_PREFIX",
                           type(renderer_context[
                                    "view"]).__name__) + f"-{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.{self.format}"
        is_mapping = getattr(renderer_context["view"], "IS_MAP", True)
        view.download_url = filename
        data = self.parser(data, renderer_context, is_mapping).parse()
        return self.writer(filename, data, renderer_context).render()


class ExcelRender(DefaultExcelRender):
    media_type = "text/xlsx"


class JSONParser(renderers.JSONRenderer):
    pass