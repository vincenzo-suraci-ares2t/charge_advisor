"""Additional enumerated values to use in home assistant."""

# ----------------------------------------------------------------------------------------------------------------------
# Python packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Home Assistant packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# External packages
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# Local packages
# ----------------------------------------------------------------------------------------------------------------------

from ocpp_central_system.enums import *

# ----------------------------------------------------------------------------------------------------------------------
# Local files
# ----------------------------------------------------------------------------------------------------------------------

class HACentralSystemServices(str, Enum):
    service_ems_communication_start = "ems_communication_start"
    service_ems_communication_stop = "ems_communication_stop"

class HAChargePointServices(str, Enum):
    """Charging Station status conditions to report in home assistant."""

    # For HA service reference and for function to call use .value
    service_charge_start = "start_transaction"
    service_charge_stop = "stop_transaction"
    service_availability = "availability"
    service_set_charge_rate = "set_charge_rate"
    service_reset = "reset"
    service_unlock = "unlock"
    service_update_firmware = "update_firmware"
    service_configure = "configure"
    service_get_configuration = "get_configuration"
    service_get_diagnostics = "get_diagnostics"
    service_clear_profile = "clear_profile"
    service_data_transfer = "data_transfer"

class HAChargePointSensors(str, Enum):
    """Charge Point status conditions to report in home assistant."""

    availability = ChargingStationStatus.availability.value
    status = ChargingStationStatus.status.value
    heartbeat = ChargingStationStatus.heartbeat.value
    latency_ping = ChargingStationStatus.latency_ping.value
    latency_pong = ChargingStationStatus.latency_pong.value
    error_code = ChargingStationStatus.error_code.value
    firmware_status = ChargingStationStatus.firmware_status.value
    reconnects = ChargingStationStatus.reconnects.value
    identifier = ChargingStationStatus.identifier.value
    model = ChargingStationStatus.model.value
    vendor = ChargingStationStatus.vendor.value
    serial = ChargingStationStatus.serial.value
    firmware_version = ChargingStationStatus.firmware_version.value
    features = ChargingStationStatus.features.value
    connectors = ChargingStationStatus.connectors.value
    data_response = ChargingStationStatus.data_response.value
    data_transfer = ChargingStationStatus.data_transfer.value
    config_response = ChargingStationStatus.config_response.value

class HAEVSESensors(str, Enum):
    availability = EVSEStatus.availability.value
    connectors = EVSEStatus.connectors.value
    identifier = EVSEStatus.identifier.value
    status = EVSEStatus.status.value

class HAConnectorSensors(str, Enum):
    """Connector status conditions to report in home assistant."""

    availability = ConnectorStatus.availability.value
    status = ConnectorStatus.status.value
    error_code = ConnectorStatus.error_code.value
    id_tag = ConnectorStatus.id_tag.value

class HAConnectorChargingSessionSensors(str, Enum):
    """Charger session information to report in home assistant."""

    session_stop_reason = ChargingSessionStatus.session_stop_reason.value
    transaction_id = ChargingSessionStatus.transaction_id.value
    session_start = ChargingSessionStatus.session_start.value
    session_time = ChargingSessionStatus.session_time.value
    session_energy = ChargingSessionStatus.session_energy.value
    session_energy_past = ChargingSessionStatus.session_energy_past.value
    current_setpoint = ChargingSessionStatus.current_setpoint.value
    energy_meter_start = ChargingSessionStatus.energy_meter_start.value


class V201HAConnectorChargingSessionSensors(str, Enum):
    HAConnectorChargingSessionSensors.__members__.items()
    charging_connector = ChargingSessionStatus.charging_connector.value
    charging_state = ChargingSessionStatus.charging_state.value