"""Custom integration for Chargers that support the Open Charge Point Protocol."""
# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

import asyncio
import logging
import logging
import subprocess
import sys



# Questa variabile deve stare qui, non può essere messa in const
# Perchè const importa ocpp_central_system. Se noi importassimo qui const, non funzionerebbe,
# perchè non troverebbe central system

from .config import *

"""Importing integration"""

logging.error("Importing package")
local_package_name = "./custom_components/ocpp/ocpp_central_system"

# Path assoluto alla chiave per accedere al repository di ocpp_central_system
key_path = "/config/ssh-keys/ocpp-central-system-key"
# Url al repository git (bitbucket) di ocpp_central_system
package_url = "git+ssh://git@bitbucket.org/ares2t/ocpp-central-system.git"

if INTEGRATION_TYPE == INTEGRATION_TYPE_PROD:
    # Installazione del package ocpp_central_system da bitbucket con chiave
    logging.error(subprocess.run([f"eval `ssh-agent -s` && ssh-add {key_path} && ssh -o StrictHostKeyChecking=no -T git@bitbucket.org && pip install {package_url} --upgrade-strategy only-if-needed"], shell=True, capture_output=True))
else:
    logging.debug("Installing Dev Integration")
    # Installazione del package da locale, solo debug
    logging.debug(subprocess.run([f"pip install --upgrade --force-reinstall -e {local_package_name}"], shell=True, capture_output=True))

# Package installato per non andare in conflitto con Home Assistant
# logging.debug(subprocess.run([f"pip install urllib3==1.26.16"], shell=True, capture_output=True))
# Package installato per non andare in conflitto con Home Assistant
# logging.debug(subprocess.run([f"pip install pyOpenSSL==23.1.0"], shell=True, capture_output=True))

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers import device_registry
import homeassistant.helpers.config_validation as cv

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

# pip install voluptuous
import voluptuous as vol


from ocpp.v16.enums import AuthorizationStatus

# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Local files
# ----------------------------------------------------------------------------------------------------------------------

from .central_system import HomeAssistantCentralSystem
from .const import *


# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant Voluptuous SCHEMAS
# ----------------------------------------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------------------------------------
#Come usare il submodule ocpp_central_system
# 1) Scaricare la repository ocpp
# 2) Eseguire il comando git submodule add <url bitbucket>
# 3) Entrare nel submodule ed eseguire: git checkout master
# 4) Eseguire anche: git config core.filemode false
AUTH_LIST_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ID_TAG): cv.string,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_AUTH_STATUS): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_DEFAULT_AUTH_STATUS, default=AuthorizationStatus.accepted.value
        ): cv.string,
        vol.Optional(CONF_AUTH_LIST, default={}): vol.Schema(
            {cv.string: AUTH_LIST_SCHEMA}
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant Functions
# ----------------------------------------------------------------------------------------------------------------------

async def async_setup(hass: HomeAssistant, config: Config):

    """Read configuration from yaml."""

    ocpp_config = config.get(DOMAIN, {})
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][CONFIG] = ocpp_config

    # OcppLog.log_d(f"Read configuration from yaml: {ocpp_config}")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):

    """Set up this integration from config entry."""

    # OcppLog.log_d("Integration setup from config entry")

    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    params = { "hass": hass, "entry":entry }
    cs = await HomeAssistantCentralSystem.create(params)

    dr = device_registry.async_get(hass)

    # Create Central System Device
    # source: https://developers.home-assistant.io/docs/device_registry_index/
    dr.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.data.get(CONF_CSID, DEFAULT_CSID))},
        name=entry.data.get(CONF_CSID, DEFAULT_CSID),
        model=DEFAULT_CENTRAL_SYSTEM_MODEL,
        manufacturer=DEFAULT_CENTRAL_SYSTEM_VENDOR
    )

    # Register Central System Device
    hass.data[DOMAIN][entry.entry_id] = cs

    for platform in PLATFORMS:
        await hass.config_entries.async_forward_entry_setup(
            entry, platform
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    """Handle removal of an entry."""

    # OcppLog.log_d("Central System entry removal")

    central_sys = hass.data[DOMAIN][entry.entry_id]

    central_sys.websocket_server.close()
    await central_sys.websocket_server.wait_closed()

    unloaded = True
    if len(central_sys.charge_points) > 0:
        unloaded = all(
            await asyncio.gather(
                *(
                    hass.config_entries.async_forward_entry_unload(entry, platform)
                    for platform in PLATFORMS
                )
            )
        )

    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:

    """Reload config entry."""

    # OcppLog.log_d("Reload config entry")

    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
