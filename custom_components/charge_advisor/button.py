"""Button platform for ocpp."""

# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations
from dataclasses import dataclass
from typing import Final

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

from homeassistant.components.button import (
    DOMAIN as BUTTON_DOMAIN,
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Local files
# ----------------------------------------------------------------------------------------------------------------------

from .const import DOMAIN
from .enums import HAChargePointServices, SubProtocol


@dataclass
class OcppButtonDescription(ButtonEntityDescription):
    """Class to describe a Button entity."""

    press_action_service_name: str | None = None


CHARGE_POINT_BUTTONS: Final = [

    # La azione di RESET è a livello di colonnina
    OcppButtonDescription(
        key="charge_point_reset",
        name="Reset",
        device_class=ButtonDeviceClass.RESTART,
        press_action_service_name=HAChargePointServices.service_reset.name, # service name (not value!)
    ),

]

CHARGE_POINT_CONNECTOR_BUTTONS: Final = [

    # La azione di UNLOCK è a livello di connettore della colonnina
    OcppButtonDescription(
        key="connector_unlock",
        name="Unlock",
        device_class=ButtonDeviceClass.UPDATE,
        press_action_service_name=HAChargePointServices.service_unlock.name, # service name (not value!)
    ),
]


async def async_setup_entry(hass, entry, async_add_devices):
    """Configure the button platform."""

    central_system = hass.data[DOMAIN][entry.entry_id]

    entities = []

    for cp_id in central_system.charge_points:
        
        charge_point: HomeAssistantChargePoint = central_system.charge_points[cp_id]

        for ent in CHARGE_POINT_BUTTONS:
            entities.append(ChargePointButtonEntity(central_system, charge_point, ent))

        if charge_point.connection_ocpp_version == SubProtocol.OcppV16.value:
            for connector in charge_point.connectors:
                for ent in CHARGE_POINT_CONNECTOR_BUTTONS:
                    entities.append(ChargePointConnectorButtonEntity(central_system, charge_point, connector, ent))
        elif charge_point.connection_ocpp_version == SubProtocol.OcppV201.value:
            pass

    # Aggiungiamo gli unique_id di ogni entità registrata in fase di setup al
    # Charge Point o al Connector
    for entity in entities:
        entity.append_entity_unique_id()

    async_add_devices(entities, False)


class ChargePointButtonEntity(ButtonEntity):
    """Individual button for charge point."""

    _attr_has_entity_name = True
    entity_description: OcppButtonDescription

    def __init__(
        self,
        central_system: HomeAssistantCentralSystem,
        charge_point: HomeAssistantChargePoint,
        description: OcppButtonDescription,
    ):
        self._charge_point = charge_point
        self._central_system = central_system
        self.entity_description = description
        self._attr_unique_id = ".".join([
            BUTTON_DOMAIN, 
            DOMAIN, 
            self._charge_point.id, 
            self.entity_description.key
        ])
        self._attr_name = self.entity_description.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._charge_point.id)},
            via_device=(DOMAIN, self._central_system.id),
        )

    @property
    def target(self):
        return self._charge_point

    @property
    def available(self) -> bool:
        # Return if sensor is available.
        if self.target.is_available is None:
            return False
        else:
            return self.target.is_available

    async def async_press(self) -> None:
        """Triggers the charger press action service."""
        await self.target.call_ha_service(self.entity_description.press_action_service_name)

    def append_entity_unique_id(self):
        if self.unique_id not in self.target.ha_entity_unique_ids:
            self.target.ha_entity_unique_ids.append(self.unique_id)


class ChargePointConnectorButtonEntity(ChargePointButtonEntity):

    def __init__(
        self,
        central_system: HomeAssistantCentralSystem,
        charge_point: HomeAssistantChargePoint,
        connector: Connector,
        description: OcppButtonDescription,
    ):
        super().__init__(central_system, charge_point, description)
        self._connector = connector
        self._attr_unique_id = ".".join([
            BUTTON_DOMAIN,
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
