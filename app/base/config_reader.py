import configparser
import os

path = os.getcwd() + "/app/base/config.txt"


def load_config():
    if not os.path.exists(path):
        create_config()
    config = configparser.ConfigParser()
    config.read(path)

    return config


def create_config():
    config_frame = {"db": ['host', 'user', 'password', 'name'],
                    "bot": ['token']}
    config = configparser.ConfigParser()
    for key in config_frame.keys():
        config.add_section(key)

    for key, val in config_frame.items():
        for data in val:
            config.set(key, data, "")

    with open(path, "w") as config_file:
        config.write(config_file)


def get_config(section, key):
    config = load_config()

    data = config.get(section, key)
    data_list = data.split(", ")
    if len(data_list) <= 1:
        return config.get(section, key)
    else:
        return data_list


def get_all_params(section):
    config = load_config()
    for key, value in config.items():
        print(key + "\n")
        for data in value.values():
            print(data)


def change_config(section, option, data):
    config = load_config()
    config.set(section, option, data)

    with open(path, "w") as config_file:
        config.write(config_file)


def delete_config(section, option):
    config = load_config()
    config.remove_option(section, option)

    with open(path, "w") as config_file:
        config.write(config_file)
