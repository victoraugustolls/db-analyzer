from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    settings_files=["settings.toml", ".secrets.toml"],
    validators=[
        Validator("EXECUTOR.RDBMS", must_exist=True),
        Validator("EXECUTOR.RDBMS", is_in=["postgres"]),
    ]
)
