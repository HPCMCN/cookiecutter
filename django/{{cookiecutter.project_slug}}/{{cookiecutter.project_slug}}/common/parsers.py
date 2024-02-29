# -*- coding:utf-8 -*-
# author: HPCM
# time: 2022/2/17 18:01
# file: parser.py
import logging

import pyexcel
from rest_framework import parsers, exceptions, serializers

logger = logging.getLogger(__name__)


class SerializerWriteMapping(object):
    """序列化器数据转换"""

    def __init__(self, data, context, is_map=True):
        self.data = data
        self.context = context
        self.is_map = is_map

    # noinspection PyProtectedMember
    def serializer_read_fields(self, ser):
        mappings, depth_mappings, find_mappings = {}, {}, {}
        for field in ser.fields.values():
            if field.read_only:
                continue
            if field.field_name in ser._declared_fields and isinstance(field, serializers.Serializer):
                mappings[field.field_name] = self.serializer_read_fields(field)[0]
                [depth_mappings.setdefault(x, y) for x, y in self.serializer_read_fields(field)[1].items()]
                find_mappings.update(self.serializer_read_fields(field)[2])
                [find_mappings.setdefault(x, field.field_name) for x in self.serializer_read_fields(field)[1]]
            else:
                mappings[field.label] = field.field_name
                depth_mappings[field.label] = field.field_name
        return mappings, depth_mappings, find_mappings

    # noinspection PyAttributeOutsideInit
    @property
    def mappings(self):
        if not hasattr(self, "_mappings"):
            self.context["view"].get_queryset()
            if self.is_map:
                ser = self.context["view"].get_serializer_class()()
                self._mappings = self.serializer_read_fields(ser)
            else:
                self._mappings = {}
        return self._mappings

    @classmethod
    def parse_items(cls, mappings, attrs):
        items = {}
        for k in attrs:
            if k not in mappings[1]:
                continue
            if k not in mappings[0]:
                if mappings[2][k] not in items:
                    items[mappings[2][k]] = {}
                items[mappings[2][k]][mappings[1][k]] = attrs[k]
            else:
                items[mappings[1][k]] = attrs[k]
        return items

    def parse(self):
        res = self.mappings and (
            [self.parse_items(self.mappings, d) for d in self.data] or
            [{v: "" for v in self.mappings.values()}]
        ) or self.data
        res = [d for d in res if any(d.values())]
        logger.info(f"{res[0]}")
        return res


class ExcelReader(object):
    """读取数据"""

    def __init__(self, obj, context):
        self.stream = self.open_file(obj)
        self.context = context
        self.sheet = None
        self.names = None

    @staticmethod
    def open_file(obj):
        if isinstance(obj, str):
            return open(obj, "rb")
        assert hasattr(obj, "read"), "not file-object!"
        return obj

    def read(self, index=0, name_index=0):
        fp = pyexcel.get_book(file_type="xlsx", file_content=self.stream.read())
        self.sheet = fp.sheet_by_index(index)
        self.sheet.name_columns_by_row(name_index)
        assert self.sheet.number_of_rows() >= 1, "当前内容为空"

    def reader(self):
        self.read()
        return self.sheet.to_records()


class DefaultExcelParser(parsers.BaseParser):
    mappings = {}
    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    reader = ExcelReader
    parser = SerializerWriteMapping

    def init_params(self, raw):
        pass

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            data = self.reader(stream, parser_context).reader()
            return self.parser(data, parser_context).parse()
        except Exception as e:
            logger.exception(e)
            raise exceptions.ParseError(f"Parse error - {e}")


class ExcelParser(DefaultExcelParser):
    media_type = "text/xlsx"
