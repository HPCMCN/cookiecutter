__version__ = "{{ cookiecutter.version }}"
__version_info__ = tuple(
    int(num) if num.isdigit() else num
    for num in __version__.replace("-", ".", 1).split(".")
)
{%- if cookiecutter.database_engine == 'mysql' %}
import pymysql

pymysql.install_as_MySQLdb()
{%- endif %}
