# -*- coding:utf-8 -*-
# author: HPCM
# time: 2022/2/17 18:01
# file: parser.py
import logging
from collections import ChainMap

import numpy as np
import pandas as pd
from rest_framework import parsers, exceptions, serializers

logger = logging.getLogger(__name__)


class SerializerWriteMapping(object):
    """序列化器数据转换"""

    def __init__(self, df, context, is_map=True):
        self.data = df
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
        return ChainMap(mappings, depth_mappings, find_mappings)

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

    def parse(self):
        if self.mappings:
            self.data.rename(columns=self.mappings, inplace=True)
        self.data.replace({np.nan: None})
        res = self.data.to_dict(orient="records")
        logger.info(f"{res[0]}")
        return res


class ExcelReader(object):
    """读取数据"""

    def __init__(self, obj, context):
        self.stream = self.open_file(obj)
        self.context = context

    @staticmethod
    def open_file(obj):
        if isinstance(obj, str):
            return open(obj, "rb")
        assert hasattr(obj, "read"), "not file-object!"
        return obj

    def read(self, index=0, name_index=0):
        df = pd.read_excel(self.stream.read(), sheet_name=index, header=name_index, engine="openpyxl")
        assert df.shape[0] >= 1, "当前内容为空"
        return df

    def reader(self):
        return self.read()


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
