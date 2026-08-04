from aisc_plugin_interface.models.setting_definition import SettingCategory, SettingDefinition, SettingValueType


def evaluation_setting(
    name: str,
    label: str,
    category: SettingCategory,
    service_type: str = "",
    value_type: SettingValueType | None = None,
    required: bool = True,
):
    def decorator(cls):
        if "_setting_definitions" not in cls.__dict__:
            cls._setting_definitions = []
        if not any(definition.name == name for definition in cls._setting_definitions):
            cls._setting_definitions.append(
                SettingDefinition(
                    name=name,
                    label=label,
                    category=category,
                    service_type=service_type,
                    value_type=value_type,
                    required=required,
                )
            )
        return cls

    return decorator
