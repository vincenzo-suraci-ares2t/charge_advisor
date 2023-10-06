"""Sensor platform for ocpp."""

# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

from __future__ import annotations
from dataclasses import dataclass
from typing import Final
from datetime import timedelta

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

import homeassistant
from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

from ocpp.v16.enums import ChargePointStatus

# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Local files
# ----------------------------------------------------------------------------------------------------------------------

from .const import *
from .enums import *
from .logger import OcppLog

SCAN_INTERVAL = timedelta(seconds=DEFAULT_METER_INTERVAL)

# Questo insieme contiene gli stati del connettore che rendono i sensori dipsonibili nella plancia di HA
CONNECTOR_CHARGING_SESSION_SENSORS_AVAILABILTY_SET: Final = [
    ChargePointStatus.charging.value,
    ChargePointStatus.suspended_evse.value,
    ChargePointStatus.suspended_ev.value,
]

@dataclass
class OcppSensorDescription(SensorEntityDescription):
    """Class to describe a Sensor entity."""

    scale: int = 1  # used for rounding metric
    metric_key: str | None = None
    connector_id: int | None = None
    availability_set: list | None = None


class OcppSensor:

    @staticmethod
    def get_charge_point_entities(hass, charge_point: ChargePoint):

        central_system = charge_point.central

        sensors = []

        for metric_key in list(HAChargePointSensors):
            if metric_key in HA_CHARGE_POINT_DIAGNOSTIC_SENSORS:
                sensors.append(
                    OcppSensorDescription(
                        key=metric_key.lower(),
                        name=metric_key.replace(".", " "),
                        metric_key=metric_key,
                        entity_category=EntityCategory.DIAGNOSTIC,
                    )
                )
            else:
                sensors.append(
                    OcppSensorDescription(
                        key=metric_key.lower(),
                        name=metric_key.replace(".", " "),
                        metric_key=metric_key,
                    )
                )

        for connector_id in range(1, charge_point.num_connectors + 1):            
            for metric_key in list(HAConnectorSensors):
                sensors.append(
                    OcppSensorDescription(
                        key=metric_key.lower(),
                        name=metric_key.replace(".", " "),
                        metric_key=metric_key,
                        connector_id=connector_id,
                    )
                )
            for metric_key in list(HAConnectorChargingSessionSensors):
                sensors.append(
                    OcppSensorDescription(
                        key=metric_key.lower(),
                        name=metric_key.replace(".", " "),
                        metric_key=metric_key,
                        connector_id=connector_id,
                        availability_set=CONNECTOR_CHARGING_SESSION_SENSORS_AVAILABILTY_SET,
                    )
                )
            for metric_key in charge_point.measurands:
                sensors.append(
                    OcppSensorDescription(
                        key=metric_key.lower(),
                        name=metric_key.replace(".", " "),
                        metric_key=metric_key,
                        connector_id=connector_id,
                        availability_set=CONNECTOR_CHARGING_SESSION_SENSORS_AVAILABILTY_SET,
                    )
                )

        entities = []

        for sensor in sensors:
            if sensor.connector_id is None:
                entities.append(
                    ChargePointMetric(
                        hass,
                        central_system,
                        charge_point,
                        sensor
                    )
                )
            else:
                connector = charge_point.get_connector_by_id(sensor.connector_id)
                entities.append(
                    ChargePointConnectorMetric(
                        hass,
                        central_system,
                        charge_point,
                        connector,
                        sensor
                    )
                )

        return entities


#  Static Sensor Platform entities registration done at CONFIG TIME (not at RUNTIME)
# A workaround to do it at runtime: https://community.home-assistant.io/t/adding-entities-at-runtime/200855/2
async def async_setup_entry(hass, entry, async_add_devices):

    # Configure the sensor platform
    central_system: CentralSystem = hass.data[DOMAIN][entry.entry_id]

    entities = []

    for cp_id in central_system.charge_points:
        charge_point = central_system.charge_points[cp_id]
        for charge_point_entity in OcppSensor.get_charge_point_entities(hass, charge_point):
            entities.append(charge_point_entity)

    # Aggiungiamo gli unique_id di ogni entità registrata in fase di setup al
    # Charge Point o al Connector
    for entity in entities:
        entity.append_entity_unique_id()

    async_add_devices(entities, False)


# source: https://developers.home-assistant.io/docs/core/entity/sensor?_highlight=restoresensor#restoring-sensor-states
class ChargePointMetric(RestoreSensor, SensorEntity):
    # Individual sensor for charge point metrics.

    _attr_has_entity_name = True
    entity_description: OcppSensorDescription

    def __init__(
        self,
        hass,
        central_system,
        charge_point,
        description: OcppSensorDescription,
    ):
        # Instantiate instance of a ChargePointMetrics.
        self._central_system = central_system
        self._charge_point = charge_point
        self.entity_description = description
        self._hass = hass
        self._extra_attr = {}
        self._last_reset = homeassistant.util.dt.utc_from_timestamp(0)
        self._attr_unique_id = ".".join([
            SENSOR_DOMAIN,
            DOMAIN,
            self._charge_point.id,
            self.entity_description.key
        ])
        self._attr_name = self.entity_description.name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._charge_point.id)},
            via_device=(DOMAIN, self._central_system.id),
        )
        self._attr_native_unit_of_measurement = None
        self._attr_native_value = None

    @property
    def target(self):
        return self._charge_point

    @property
    def _metric_key(self):
        return self.entity_description.metric_key

    # source: https://developers.home-assistant.io/docs/core/entity/#property-function
    @property
    def icon(self) -> str | None:
        # Icon of the entity.
        if self._metric_key in MEASURAND_ICON:
            return MEASURAND_ICON[self._metric_key]
        return ICON

    @property
    def available(self) -> bool:
        # Return if sensor is available.
        return self.target.is_available()

    @property
    def should_poll(self):
        # Return True if entity has to be polled for state.
        # False if entity pushes its state to HA.
        return True

    @property
    def force_update(self):

        return True

    @property
    def extra_state_attributes(self):
        # Return the state attributes.
        return self.target.get_metric_extra_attr(self._metric_key)

    @property
    def state_class(self):
        # Return the state class of the sensor.
        state_class = None
        if self.device_class is SensorDeviceClass.ENERGY:
            state_class = SensorStateClass.TOTAL_INCREASING
        elif self.device_class in [
            SensorDeviceClass.CURRENT,
            SensorDeviceClass.VOLTAGE,
            SensorDeviceClass.POWER,
            SensorDeviceClass.TEMPERATURE,
            SensorDeviceClass.BATTERY,
            SensorDeviceClass.FREQUENCY,
            SensorDeviceClass.DURATION
        ] or self._metric_key in [
            HAChargePointSensors.latency_ping.value,
            HAChargePointSensors.latency_pong.value,
        ]:
            state_class = SensorStateClass.MEASUREMENT

        return state_class

    def append_entity_unique_id(self):
        if self.unique_id not in self.target.ha_entity_unique_ids:
            self.target.ha_entity_unique_ids.append(self.unique_id)

    # Aggiornamento del 08/02/2023
    # I measurand di Energia e Potenza REATTIVA non hanno in Home Assistant una unità di misura standardizzata.
    # Home Assistant supporta solo W, kW, Wh e kWh.
    #
    # Pertanto, impostando Energia e Potenza REATTIVA con le loro unità di misura (var, kvar per la potenza e
    # varh, kvarh per la energia) nelle classi Home Assistant SensorDeviceClass.ENERGY e SensorDeviceClass.POWER
    # dà i seguenti errori:
    # a) WARNING(MainThread)[homeassistant.components.sensor] Entity sensor.charge_point_1_1_energy_reactive_export_interval
    #    (<class 'custom_components.ocpp.sensor.ChargePointConnectorMetric'> ) is using native unit of measurement
    #    'UnitOfMeasure.kvarh' which is not a valid unit for the device
    # b) WARNING(MainThread)[homeassistant.components.sensor] Entity sensor.charge_point_1_1_power_reactive_import
    #    (<class 'custom_components.ocpp.sensor.ChargePointConnectorMetric'> ) is using native unit of measurement
    #    'UnitOfMeasure.kvar' which is not a valid unit for the device
    #
    # Per ovviare al problema, evitiamo di attribuire tali classi ai sensori di Energia e Potenza REATTIVA

    @property
    def device_class(self):
        # Return the device class of the sensor.
        device_class = None
        mk = self._metric_key.lower()
        if mk.startswith("current."):
            device_class = SensorDeviceClass.CURRENT
        elif mk.startswith("voltage"):
            device_class = SensorDeviceClass.VOLTAGE
        elif mk.startswith("energy.") and not mk.startswith("energy.reactive"):
            device_class = SensorDeviceClass.ENERGY
        elif self._metric_key in [
            Measurand.frequency.value,
            Measurand.rpm.value,
        ] or mk.startswith("frequency"):
            device_class = SensorDeviceClass.FREQUENCY
        elif mk.startswith(tuple(["power.active", "power.offered"])) and not mk.startswith("power.reactive"):
            device_class = SensorDeviceClass.POWER
        elif mk.startswith("temperature."):
            device_class = SensorDeviceClass.TEMPERATURE
        elif mk.startswith("session.time"):
            device_class = SensorDeviceClass.DURATION
        elif mk.startswith("timestamp.") or self._metric_key in [
            HAChargePointSensors.config_response.value,
            HAChargePointSensors.data_response.value,
            HAChargePointSensors.heartbeat.value,
        ]:
            device_class = SensorDeviceClass.TIMESTAMP
        elif mk.startswith("soc"):
            device_class = SensorDeviceClass.BATTERY
        return device_class

    @property
    def native_value(self):
        # Return the state of the sensor, rounding if a number.
        value = self.target.get_metric_value(self._metric_key)
        if isinstance(value, float):
            value = round(value, self.entity_description.scale)
        if value is not None:
            self._attr_native_value = value
        # OcppLog.log_d(f"{self._attr_unique_id} value: {self._attr_native_value}")
        return self._attr_native_value

    @property
    def native_unit_of_measurement(self):
        # Return the native unit of measurement.
        uom = self.target.get_metric_ha_unit(self._metric_key)
        if uom is not None:
            self._attr_native_unit_of_measurement = uom
        else:
            self._attr_native_unit_of_measurement = DEFAULT_CLASS_UNITS_HA.get(
                self.device_class
            )
        return self._attr_native_unit_of_measurement

    """
    Restoring sensor states
    Sensors which restore the state after restart or reload should not extend RestoreEntity because that does not store 
    the native_value, but instead the state which may have been modifed by the sensor base entity. Sensors which restore 
    the state should extend RestoreSensor and call await self.async_get_last_sensor_data from async_added_to_hass to get 
    access to the stored native_value and native_unit_of_measurement.
    source: https://developers.home-assistant.io/docs/core/entity/sensor?_highlight=restoresensor#restoring-sensor-states
    """
    async def async_added_to_hass(self) -> None:
        # Handle entity which will be added.
        await super().async_added_to_hass()

        if restored := await self.async_get_last_sensor_data():
            # Recuperiamo il valore solo se i sensori sono di categoria DIAGNOSTIC
            if self.entity_description.entity_category == EntityCategory.DIAGNOSTIC:
                self._attr_native_value = restored.native_value
            self._attr_native_unit_of_measurement = restored.native_unit_of_measurement

        async_dispatcher_connect(
            self._hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

class ChargePointConnectorMetric(ChargePointMetric):

    def __init__(
        self,
        hass: HomeAssistant,
        central_system: CentralSystem,
        charge_point: ChargePoint,
        connector: Connector,
        description: OcppSensorDescription,
    ):
        super().__init__(hass, central_system, charge_point, description)
        self._connector = connector
        self._attr_unique_id = ".".join([
            SENSOR_DOMAIN,
            DOMAIN,
            self._charge_point.id,
            str(self._connector.id),
            self.entity_description.key
        ])
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._connector.identifier)},
            via_device=(DOMAIN, self._charge_point.id),
        )

        # OcppLog.log_d(f"Adding {self._attr_unique_id} entity")

    @property
    def target(self):
        return self._connector

    @property
    def available(self) -> bool:
        # Return if sensor is available
        available = False
        if self.entity_description.availability_set is not None:
            value = self._connector.get_metric_value(HAConnectorSensors.status.value)
            if value in self.entity_description.availability_set:
                available = super().available
        else:
            available = super().available
        return available
