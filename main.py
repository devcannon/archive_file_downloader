#!/usr/bin/python3

import tarfile
import zipfile
import logging
import tomllib
import requests
from pathlib import Path
import platform


class ToolsInitializerError(Exception):
    pass


class ConfigError(ToolsInitializerError):
    pass


class UnsupportedPlatformError(ToolsInitializerError):
    pass


def download_file(url, local_filename: Path):
    # Create the parent directory if it doesn't exist
    directory = local_filename.parent
    directory.mkdir(parents=True, exist_ok=True)

    with requests.get(url, stream=True) as response:
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            with open(local_filename, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
            logging.info(f"File downloaded successfully and saved as {local_filename}")
        else:
            raise ToolsInitializerError(
                f"Failed to download file. Status code: {response.status_code}"
            )


def unpack_archive(archive: Path, out_path: Path):
    try:
        if tarfile.is_tarfile(archive):
            with tarfile.open(archive) as opened_archive:
                opened_archive.extractall(path=out_path)
        elif zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as opened_archive:
                opened_archive.extractall(path=out_path / archive.stem)
        else:
            raise ToolsInitializerError("Unsupported archive format")
    except Exception as e:
        raise ToolsInitializerError(f"Unpack error: {e}")
    else:
        logging.info(f"File unpacked to: `{out_path}`")


def get_config_value(config, config_value_key):
    value = config.get(config_value_key)
    if value is None:
        raise ConfigError(
            f"Key `{config_value_key}` not set in config value. The value is: {config}"
        )

    return value


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if (current_platform := platform.system()) == "Windows":
        download_url_key = "url_win64"
    elif current_platform == "Linux":
        download_url_key = "url_linux"
    else:
        raise UnsupportedPlatformError(f"Unknown platform: {current_platform}")

    logging.info(f"Running on {current_platform}")

    try:
        with open("config.toml", "rb") as f:
            configuration = tomllib.load(f)
    except Exception as e:
        logging.error(f"Could not load config file: {e}")
    else:
        download_override = get_config_value(configuration, "download_override")
        tools = get_config_value(configuration, "tool")
        temp_path = Path(get_config_value(configuration, "temp_path"))
        delete_after_extract = get_config_value(configuration, "delete_after_extract")

        download_both_platforms = get_config_value(
            configuration, "download_both_platforms"
        )

        if (override_url_key := download_override.get("url")) is not None:
            download_url_key = override_url_key
            logging.warn(
                f"Config value `download_key_override` is set. Overriding url key to: `{override_url_key}`"
            )

        for tool in tools:
            name = get_config_value(tool, "name")
            extract_to = Path(get_config_value(tool, "extract_to"))
            url = get_config_value(tool, download_url_key)

            # TODO: Handle both platforms
            download_path = temp_path / Path(url.rsplit("/", 1)[-1])
            logging.info(
                f"Download tool `{name}` in temporary dir `{download_path}` from URL `{url}`"
            )

            download_file(url, download_path)
            unpack_archive(download_path, extract_to)

            if delete_after_extract:
                download_path.unlink()
        
        if delete_after_extract:
            temp_path.rmdir()
