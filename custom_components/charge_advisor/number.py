"""Number platform for ocpp."""

# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations
from dataclasses import dataclass
from typing import Final


# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

from homeassistant.components.number import (
    DOMAIN as NUMBER_DOMAIN,
    NumberEntity,
    NumberEntityDescription,
    RestoreNumber,
)
from homeassistant.const import ELECTRIC_CURRENT_AMPERE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

# from ocpp_central_system.time_utils import TimeUtils

# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

from ocpp_central_system.time_utils import TimeUtils

# ----------------------------------------------------------------------------------------------------------------------
# Local files
# ----------------------------------------------------------------------------------------------------------------------

from .const import *
from .enums import Profiles, SubProtocol

@dataclass
class OcppNumberDescription(NumberEntityDescription):
    """Class to describe a Number entity."""

    initial_value: float | None = None


NUMBERS: Final = [
    OcppNumberDescription(
        key="maximum_current",
        name="Maximum Current",
        icon=ICON,
        initial_value=DEFAULT_MAX_CURRENT,
        native_min_value=0,
        native_max_value=DEFAULT_MAX_CURRENT,
        native_step=1,
        native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
    ),
]


async def async_setup_entry(hass, entry, async_add_devices):
    """Configure the number platform."""

    central_system: CentralSystem = hass.data[DOMAIN][entry.entry_id]

    entities = []

    for cp_id in central_system.charge_points:
        
        charge_point: HomeAssistantChargePoint = central_system.charge_points[cp_id]

        for ent in NUMBERS:
            if ent.key == "maximum_current":
                ent.initial_value = 0
                ent.native_max_value = entry.data.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT)
            entities.append(ChargePointOcppNumber(hass, central_system, charge_point, ent))

        if charge_point.connection_ocpp_version == SubProtocol.OcppV16.value:
            for connector in charge_point.connectors:
                for ent in NUMBERS:
                    if ent.key == "maximum_current":
                        ent.initial_value = 0
                        ent.native_max_value = entry.data.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT)
                    entities.append(ChargePointConnectorOcppNumber(hass, central_system, charge_point, connector, ent))
        elif charge_point.connection_ocpp_version == SubProtocol.OcppV201.value:
            pass

    # Aggiungiamo gli unique_id di ogni entità registrata in fase di setup al
    # Charge Point o al Connector
    for entity in entities:
        entity.append_entity_unique_id()

    async_add_devices(entities, False)


class ChargePointOcppNumber(RestoreNumber, NumberEntity):
    """Individual slider for setting charge rate."""

    _attr_has_entity_name = True
    entity_description: OcppNumberDescription

    def __init__(
        self,
        hass: HomeAssistant,
        central_system: CentralSystem,
        charge_point: ChargePoint,
        description: OcppNumberDescription,
    ):
        """Initialize a Number instance."""        
        self._hass = hass
        self._central_system = central_system
        self._charge_point = charge_point
        self.entity_description = description
        self._attr_unique_id = ".".join([
            NUMBER_DOMAIN,
            self._charge_point.id,
            self.entity_description.key
        ])
        self._attr_name = self.entity_description.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._charge_point.id)},
            via_device=(DOMAIN, self._central_system.id),
        )
        self._attr_native_value = self.entity_description.initial_value
        self._attr_should_poll = False
        self._attr_available = True

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        if restored := await self.async_get_last_number_data():
            self._attr_native_value = restored.native_value
            self.target.limit_amps = self._attr_native_value
        async_dispatcher_connect(
            self._hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @property
    def target(self):
        return self._charge_point

    @property
    def available(self) -> bool:
        # Return if sensor is available.
        return self.target.is_available()

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

    # @property
    # def available(self) -> bool:
    #    """Return if entity is available."""
    #    if not (
    #        Profiles.SMART & self._central_system.get_supported_features(self.cp_id)
    #    ):
    #        return False
    #    return self._central_system.get_available(self.cp_id)  # type: ignore [no-any-return]

    async def async_set_native_value(self, value):
        """Set new value."""
        num_value = int(value)
        if self.target.is_available() and ((Profiles.SMART & self._charge_point.supported_features) or True) :

            resp = await self.target.set_max_charge_rate(
                limit_amps=num_value * 3
            )

            if resp is True:
                self._attr_native_value = num_value
                self.async_write_ha_state()

    def append_entity_unique_id(self):
        if self.unique_id not in self.target.ha_entity_unique_ids:
            self.target.ha_entity_unique_ids.append(self.unique_id)

class ChargePointConnectorOcppNumber(ChargePointOcppNumber):

    def __init__(
            self,
            hass: HomeAssistant,
            central_system: CentralSystem,
            charge_point: ChargePoint,
            connector: Connector,
            description: OcppNumberDescription,
    ):
        super().__init__(hass, central_system, charge_point, description)
        self._connector = connector
        self._attr_unique_id = ".".join([
            NUMBER_DOMAIN,
            self._charge_point.id,
            str(self._connector.id),
            self.entity_description.key
        ])
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._connector.identifier)},
            via_device=(DOMAIN, self._charge_point.id),
        )

    @property
    def target(self):
        return self._connector
