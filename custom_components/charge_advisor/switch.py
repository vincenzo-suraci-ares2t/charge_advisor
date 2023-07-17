"""Switch platform for ocpp."""

# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Final

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import POWER_KILO_WATT
from homeassistant.helpers.entity import DeviceInfo

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

from ocpp.v16.enums import ChargePointStatus, Measurand, AvailabilityType
# from ocpp_central_system.logger import OcppLog

# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

from .const import DOMAIN, ICON
from .enums import HAChargePointServices, HAChargePointSensors, HAConnectorSensors
from .logger import OcppLog

# Switch configuration definitions
# At a minimum define switch name and on service call,
# metric and condition combination can be used to drive switch state, use default to set initial state to True
@dataclass
class OcppSwitchDescription(SwitchEntityDescription):
    """Class to describe a Switch entity."""

    on_action_service_name: str | None = None
    off_action_service_name: str | None = None
    metric_key: str | None = None
    metric_condition: str | None = None
    default_state: bool = False


"""
Gli switch sono aggiunti "staticamente" dall'integrazione.
Vengono aggiunti 2 switch:
1) Availability > dovrebbe essere uno per ogni connettore!
2) Charge_Control > dovrebbe essere uno per ogni connettore! 
"""
CENTRAL_SYSTEM_SWITCHES: Final = [
    OcppSwitchDescription(
        key="energy_control_communication",
        name="EMS Communication",
        icon=ICON,
        on_action_service_name=HAChargePointServices.service_ems_communication_start.name, # service name (not value)
        off_action_service_name=HAChargePointServices.service_ems_communication_stop.name, # service name (not value)
        metric_key=HAChargePointServices.service_ems_communication_start.value,
        metric_condition=[
            True #Questa è hard coded per il momento, solo provvisorio
        ],
        default_state=False,
    ),
]


CHARGE_POINT_SWITCHES: Final = [
    OcppSwitchDescription(
        key="availability",
        name="Availability",
        icon=ICON,
        on_action_service_name=HAChargePointServices.service_availability.name, # service name (not value)
        off_action_service_name=HAChargePointServices.service_availability.name, # service name (not value)
        metric_key=HAChargePointSensors.availability.value,
        metric_condition=[
            AvailabilityType.operative.value
        ],
        default_state=AvailabilityType.inoperative.value,
    ),
]

CHARGE_POINT_CONNECTOR_SWITCHES: Final = [
    OcppSwitchDescription(
        key="charge_control",
        name="Charge Control",
        icon=ICON,
        on_action_service_name=HAChargePointServices.service_charge_start.name,
        off_action_service_name=HAChargePointServices.service_charge_stop.name,
        metric_key=HAConnectorSensors.status.value,
        metric_condition=[
            ChargePointStatus.preparing.value,
            ChargePointStatus.charging.value,
            ChargePointStatus.suspended_evse.value,
            ChargePointStatus.suspended_ev.value,
        ],
        default_state=False,
    ),
    OcppSwitchDescription(
        key="availability",
        name="Availability",
        icon=ICON,
        on_action_service_name=HAChargePointServices.service_availability.name,
        off_action_service_name=HAChargePointServices.service_availability.name,
        metric_key=HAConnectorSensors.availability.value,
        metric_condition=[
            AvailabilityType.operative.value
        ],
        default_state=AvailabilityType.inoperative.value,
    ),
]


async def async_setup_entry(hass, entry, async_add_devices):
    """Configure the switch platform."""

    # Get the Central system instance
    central_system = hass.data[DOMAIN][entry.entry_id]    

    entities = []
    entities.append(CentralSystemSwitchEntity(central_system, CENTRAL_SYSTEM_SWITCHES[0]))
    # Scorriamo tutti i Charge Point
    for cp_id in central_system.charge_points:
        # Recuperiamo il Charge Point
        charge_point = central_system.charge_points[cp_id]
        for ent in CHARGE_POINT_SWITCHES:
            entities.append(ChargePointSwitchEntity(central_system, charge_point, ent))
        # Scorriamo i connettori del Charge Point        
        for connector in charge_point.connectors:
            for ent in CHARGE_POINT_CONNECTOR_SWITCHES:
                entities.append(ChargePointConnectorSwitchEntity(central_system, charge_point, connector, ent))

    # Aggiungiamo gli unique_id di ogni entità registrata in fase di setup al
    # Charge Point o al Connector
    for entity in entities:
        entity.append_entity_unique_id()

    async_add_devices(entities, False)

class CentralSystemSwitchEntity(SwitchEntity):
    _attr_has_entity_name = True
    entity_description: OcppSwitchDescription

    def __init__(
        self,
        central_system: CentralSystem,
        description: OcppSwitchDescription,
    ):
        self._central_system = central_system
        self.entity_description = description
        self._state = self.entity_description.default_state
        self._attr_unique_id = ".".join([
            SWITCH_DOMAIN,
            DOMAIN,
            self._central_system.id,
            self.entity_description.key
            ])
        self._attr_name = self.entity_description.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._central_system.id)}
        )
        # OcppLog.log_d(f"{self._attr_unique_id} switch created!")

    @property
    def target(self):
        return self._central_system

    @property
    def available(self) -> bool:
        # Return if switch is available.
        return self.target.is_available()

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        """Test metric state against condition if present"""
        resp = self.target.get_metric_value(self.entity_description.metric_key)
        if resp is not None:
            if resp in self.entity_description.metric_condition:
                self._state = True
            else:
                self._state = False
        # OcppLog.log_d(f"{self._attr_unique_id} is_on: {self._state}")
        return self._state  # type: ignore [no-any-return]


    async def async_turn_off(self, **kwargs: Any) -> None:
        # Turn the switch off.
        """Response is True if successful but State is False"""
        if self.entity_description.off_action_service_name is None:
            resp = True
        elif self.entity_description.off_action_service_name == self.entity_description.on_action_service_name:
            resp = await self.target.call_ha_service(
                service_name=self.entity_description.off_action_service_name,
                state=False
            )
        else:
            resp = await self.target.call_ha_service(
                service_name=self.entity_description.off_action_service_name,
            )
        self._state = not resp

    async def async_turn_on(self, **kwargs: Any) -> None:
        # Turn the switch on.
        # OcppLog.log_d(f"{self.entity_description.on_action_service_name} service called")
        self._state = await self.target.call_ha_service(
            service_name=self.entity_description.on_action_service_name,
            state=True
        )

    def append_entity_unique_id(self):
        if self.unique_id not in self.target.ha_entity_unique_ids:
            self.target.ha_entity_unique_ids.append(self.unique_id)



class ChargePointSwitchEntity(SwitchEntity):
    """Individual switch for charge point."""

    _attr_has_entity_name = True
    entity_description: OcppSwitchDescription

    def __init__(
        self,
        central_system: CentralSystem,
        charge_point: ChargePoint,
        description: OcppSwitchDescription,
    ):
        self._charge_point = charge_point
        self._central_system = central_system
        self.entity_description = description
        self._state = self.entity_description.default_state
        self._attr_unique_id = ".".join([
            SWITCH_DOMAIN,
            DOMAIN,
            self._charge_point.id,
            self.entity_description.key
            ])
        self._attr_name = self.entity_description.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._charge_point.id)},
            via_device=(DOMAIN, self._central_system.id),
        )
        # OcppLog.log_d(f"{self._attr_unique_id} switch created!")

    @property
    def target(self):
        return self._charge_point

    @property
    def available(self) -> bool:
        # Return if switch is available.
        return self.target.is_available()

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        """Test metric state against condition if present"""
        resp = self.target.get_metric_value(self.entity_description.metric_key)
        if resp is not None:
            if resp in self.entity_description.metric_condition:
                self._state = True
            else:
                self._state = False
        # OcppLog.log_d(f"{self._attr_unique_id} is_on: {self._state}")
        return self._state  # type: ignore [no-any-return]


    async def async_turn_on(self, **kwargs: Any) -> None:
        # Turn the switch on.
        # OcppLog.log_d(f"{self.entity_description.on_action_service_name} service called")
        self._state = await self.target.call_ha_service(
            service_name=self.entity_description.on_action_service_name,
            state=True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        # Turn the switch off.
        """Response is True if successful but State is False"""
        if self.entity_description.off_action_service_name is None:
            resp = True
        elif self.entity_description.off_action_service_name == self.entity_description.on_action_service_name:
            resp = await self.target.call_ha_service(
                service_name=self.entity_description.off_action_service_name,
                state=False
            )
        else:
            resp = await self.target.call_ha_service(
                service_name=self.entity_description.off_action_service_name,
            )
        self._state = not resp

    @property
    def current_power_w(self) -> Any:
        """Return the current power usage in W."""
        if self.entity_description.key == "charge_control":
            value = self.target.get_metric_value(Measurand.power_active_import.value)
            ha_unit = self.target.get_metric_ha_unit(Measurand.power_active_import.value)
            if ha_unit == POWER_KILO_WATT:
                value = value * 1000
            return value
        return None

    def append_entity_unique_id(self):
        if self.unique_id not in self.target.ha_entity_unique_ids:
            self.target.ha_entity_unique_ids.append(self.unique_id)

class ChargePointConnectorSwitchEntity(ChargePointSwitchEntity):
    """Individual switch for charge point."""

    _attr_has_entity_name = True
    entity_description: OcppSwitchDescription

    def __init__(
        self,
        central_system: CentralSystem,
        charge_point: ChargePoint,
        connector: Connector,
        description: OcppSwitchDescription,
    ):
        super().__init__(central_system, charge_point, description)
        self._connector = connector
        self._attr_unique_id = ".".join([
            SWITCH_DOMAIN,
            DOMAIN,
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
