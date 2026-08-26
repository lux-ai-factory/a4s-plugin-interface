from aisc_plugin_interface.models.setting_definition import SettingCategory, SettingDefinition, SettingValueType


def project_setting(
        key: str,
        name: str,
        category: SettingCategory,
        value_type: SettingValueType | None = None,
        required: bool = True,
):
    def decorator(cls):
        if "_setting_definitions" not in cls.__dict__:
            cls._setting_definitions = []
        if not any(definition.key == key for definition in cls._setting_definitions):
            cls._setting_definitions.append(
                SettingDefinition(
                    key=key,
                    name=name,
                    category=category,
                    value_type=value_type,
                    required=required,
                )
            )
        return cls

    return decorator
