import os
from pathlib import Path

ROOT_DIR_PATH = Path(__file__).parent.resolve()
PRODUCTION_DOTENVS_DIR_PATH = ROOT_DIR_PATH / ".envs" / ".production"
PRODUCTION_DOTENV_FILE_PATHS = [
    PRODUCTION_DOTENVS_DIR_PATH / ".django",
    {%- if cookiecutter.database_engine == "postgres" %}
        PRODUCTION_DOTENVS_DIR_PATH / ".postgres",
    {%- elif cookiecutter.database_engine == 'mysql' %}
        PRODUCTION_DOTENVS_DIR_PATH / ".mysql",
    {%- endif %}
]

DOTENV_FILE_PATH = ROOT_DIR_PATH / ".env"


def merge(output_file_path, merged_file_paths, append_linesep=True) -> None:
    with open(output_file_path, "w") as output_file:
        for merged_file_path in merged_file_paths:
            with open(merged_file_path) as merged_file:
                merged_file_content = merged_file.read()
                output_file.write(merged_file_content)
                if append_linesep:
                    output_file.write(os.linesep)


def main():
    merge(DOTENV_FILE_PATH, PRODUCTION_DOTENV_FILE_PATHS)


if __name__ == "__main__":
    main()
