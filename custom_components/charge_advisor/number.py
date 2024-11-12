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
from homeassistant.const import UnitOfElectricCurrent, UnitOfPower
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

from .ocpp_central_system.ocpp_central_system.logger import OcppLog
# ----------------------------------------------------------------------------------------------------------------------
# Local files
# ----------------------------------------------------------------------------------------------------------------------

from .const import *
from .enums import Profiles, SubProtocol

from ocpp.v201.enums import AttributeType

@dataclass
class OcppNumberDescription(NumberEntityDescription):
    """Class to describe a Number entity."""

    initial_value: float | None = None


NUMBERS: Final = [
    OcppNumberDescription(
        key="maximum_current",
        name="Maximum Current",
        icon=ICON,
        initial_value=0,
        native_min_value=0,
        native_max_value=DEFAULT_MAX_CURRENT,
        native_step=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
    OcppNumberDescription(
        key="maximum_power",
        name="Maximum Power",
        icon=ICON,
        initial_value=0,
        native_min_value=0,
        native_max_value=DEFAULT_MAX_POWER,
        native_step=10,
        native_unit_of_measurement=UnitOfPower.KILO_WATT
    )
]


async def async_setup_entry(hass, entry, async_add_devices):
    """Configure the number platform."""
    # ------------------------------------------------------------------------------------------------------------------
    # Retrieve the central system object.
    # ------------------------------------------------------------------------------------------------------------------
    central_system: CentralSystem = hass.data[DOMAIN][entry.entry_id]

    entities = []
    # ------------------------------------------------------------------------------------------------------------------
    # Loop through the IDs of all the charge points of the central system in question...
    # ------------------------------------------------------------------------------------------------------------------
    for cp_id in central_system.charge_points:
        # --------------------------------------------------------------------------------------------------------------
        # Retrieve the charge point object itself.
        # --------------------------------------------------------------------------------------------------------------
        charge_point: HomeAssistantChargePoint = central_system.charge_points[cp_id]
        # --------------------------------------------------------------------------------------------------------------
        # For each entity described in the NUMBERS array...
        # --------------------------------------------------------------------------------------------------------------
        for ent in NUMBERS:
            # ----------------------------------------------------------------------------------------------------------
            # If the entity's key is "maximum_current"...
            # ----------------------------------------------------------------------------------------------------------
            if ent.key == "maximum_current":
                ent.initial_value = 0
                ent.native_max_value = entry.data.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT)
            # ----------------------------------------------------------------------------------------------------------
            # Add a ChargePointOcppNumber instance to the list of entities.
            # ----------------------------------------------------------------------------------------------------------
            entities.append(ChargePointOcppNumber(hass, central_system, charge_point, ent))
        # --------------------------------------------------------------------------------------------------------------
        # Check whether the OCPP version of the charge point is 1.6 or 2.0.1...
        # --------------------------------------------------------------------------------------------------------------
        if charge_point.connection_ocpp_version == SubProtocol.OcppV16.value:
            # ----------------------------------------------------------------------------------------------------------
            # If it's 1.6, loop through all the connectors...
            # ----------------------------------------------------------------------------------------------------------
            for connector in charge_point.connectors:
                for ent in NUMBERS:
                    # --------------------------------------------------------------------------------------------------
                    # If the entity's key is "maximum_current"...
                    # --------------------------------------------------------------------------------------------------
                    if ent.key == "maximum_current":
                        ent.initial_value = 0
                        ent.native_max_value = entry.data.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT)
                    # --------------------------------------------------------------------------------------------------
                    # Add a ChargePointConnectorOcppNumber object to the entity list.
                    # --------------------------------------------------------------------------------------------------
                    entities.append(ChargePointConnectorOcppNumber(hass, central_system, charge_point, connector, ent))
        elif charge_point.connection_ocpp_version == SubProtocol.OcppV201.value:
            # ----------------------------------------------------------------------------------------------------------
            # If it's 2.0.1, loop through all the EVSEs...
            # ----------------------------------------------------------------------------------------------------------
            for evse in charge_point.evses:
                for ent in NUMBERS:
                    # --------------------------------------------------------------------------------------------------
                    # If the entity's key is "maximum_current"...
                    # --------------------------------------------------------------------------------------------------
                    if ent.key == "maximum_current":
                        ent.initial_value = 0
                        ent.native_max_value = entry.data.get(CONF_MAX_CURRENT, 375)
                    # --------------------------------------------------------------------------------------------------
                    # Add a ChargePointConnectorOcppNumber object to the entity list.
                    # --------------------------------------------------------------------------------------------------
                    entities.append(ChargePointConnectorOcppNumber(hass, central_system, charge_point, evse, ent))
    # ------------------------------------------------------------------------------------------------------------------
    # Aggiungiamo gli unique_id di ogni entità registrata in fase di setup al
    # Charge Point o al Connector
    # ------------------------------------------------------------------------------------------------------------------
    for entity in entities:
        entity.append_entity_unique_id()
    # ------------------------------------------------------------------------------------------------------------------
    # Add all the entities as devices.
    # ------------------------------------------------------------------------------------------------------------------
    async_add_devices(entities, False)


class ChargePointOcppNumber(RestoreNumber, NumberEntity):

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

    # ------------------------------------------------------------------------------------------------------------------
    # Method to handle what happens when the slider is used.
    # ------------------------------------------------------------------------------------------------------------------
    async def async_set_native_value(self, value):
        # --------------------------------------------------------------------------------------------------------------
        # Cast the new value to integer.
        # --------------------------------------------------------------------------------------------------------------
        num_value = int(value)
        # --------------------------------------------------------------------------------------------------------------
        # Check whether OCPP 1.6 or 2.0.1 is used...
        # --------------------------------------------------------------------------------------------------------------
        if self._charge_point.connection_ocpp_version == SubProtocol.OcppV16.value:
            # ----------------------------------------------------------------------------------------------------------
            # Check whether the Connector is available and the supported features are enabled.
            # ----------------------------------------------------------------------------------------------------------
            if self.target.is_available() and ((Profiles.SMART & self._charge_point.supported_features) or True):
                # ------------------------------------------------------------------------------------------------------
                # Set the maximum current to the new value multiplied by the number of phases.
                #
                # TODO: the number of phases is currently (21/10/24) hard-coded to 3, it has to be made dynamic
                #  depending on the number of phases actually supported by the Connector.
                # ------------------------------------------------------------------------------------------------------
                resp = await self.target.set_max_charge_rate(
                    limit_amps=num_value * 3
                )
                # ------------------------------------------------------------------------------------------------------
                # If the outcome of the attempt to set the new charge rate is successful, set the new value attribute
                # and update the value of the Home Assistant object itself.
                # ------------------------------------------------------------------------------------------------------
                if resp is True:
                    self._attr_native_value = num_value
                    self.async_write_ha_state()
        elif self._charge_point.connection_ocpp_version == SubProtocol.OcppV201.value:
            if self.target.is_available() and self._charge_point.get_metric("SmartChargingCtrlr.Available"):
                # ------------------------------------------------------------------------------------------------------
                # Check whether the attribute to be changed is current or power...
                # ------------------------------------------------------------------------------------------------------
                if self._attr_name == "Maximum Current":
                    # --------------------------------------------------------------------------------------------------
                    # Retrieve the number of phases used by the EVSE.
                    # --------------------------------------------------------------------------------------------------
                    phases_variable = await self.target.charging_station.get_single_variable_generic(
                        component_name=self.target.get_component("EVSE").name,
                        evse_id=self.target.id,
                        variable_name="SupplyPhases",
                        attribute_type=AttributeType.actual.value
                    )
                    phases = int(phases_variable[0])
                    # --------------------------------------------------------------------------------------------------
                    # Using the number of phases, check whether the Charging Station operates in AC or DC.
                    #
                    # According to the OCPP 2.0.1 specifications, section "Referenced Components and Variables",
                    # paragraph 2.13.6, if the number of phases is 0 the charging station uses DC.
                    # --------------------------------------------------------------------------------------------------
                    if phases == 0:
                        # ----------------------------------------------------------------------------------------------
                        # Set the number of phases to 1 to avoid multiplying by 0.
                        # ----------------------------------------------------------------------------------------------
                        phases = 1
                    # --------------------------------------------------------------------------------------------------
                    # Set the maximum current to the new value multiplied by the number of phases.
                    # --------------------------------------------------------------------------------------------------
                    resp = await self.target.set_max_charge_rate(
                        limit_amps=num_value * phases
                    )
                elif self._attr_name == "Maximum Power":
                    # --------------------------------------------------------------------------------------------------
                    # Set the maximum power to the new value. Since the slider expresses the value in kilowatts, its
                    # value has to be converted to watts first.
                    # --------------------------------------------------------------------------------------------------
                    resp = await self.target.set_max_charge_rate(
                        limit_watts=num_value * 1000
                    )
                # ------------------------------------------------------------------------------------------------------
                # If the outcome of the attempt to set the new charge rate is successful, set the new value attribute
                # and update the value of the Home Assistant object itself.
                # ------------------------------------------------------------------------------------------------------
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

class ChargePointEVSEOcppNumber(ChargePointOcppNumber):

    def __init__(
            self,
            hass: HomeAssistant,
            central_system: CentralSystem,
            charge_point: ChargePoint,
            evse: EVSE,
            description: OcppNumberDescription,
    ):
        super().__init__(hass, central_system, charge_point, description)
        self._evse = evse
        self._attr_unique_id = ".".join([
            NUMBER_DOMAIN,
            self._charge_point.id,
            str(self._evse.id),
            self.entity_description.key
        ])
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._connector.identifier)},
            via_device=(DOMAIN, self._charge_point.id),
        )

    @property
    def target(self):
        return self._evse