import dynaconf

settings = dynaconf.Dynaconf(
    settings_files=["settings.toml", ".secrets.toml"],
    validators=[
        dynaconf.Validator("EXECUTOR.RDBMS", is_in=["postgres", "sqlserver"], must_exist=True),
    ]
)
