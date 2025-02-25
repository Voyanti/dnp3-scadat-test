from enum import Enum


# https://www.home-assistant.io/integrations/sensor#device-class
class HASensorDeviceClass(Enum):
    """Home Assistant Sensor Device Classes defining the type of sensor and their supported units."""
    
    NONE = "none"  # Generic sensor with no specific type or unit
    APPARENT_POWER = "apparent_power"  # Apparent power measurement in VA
    AQI = "aqi"  # Air Quality Index, unitless measurement
    AREA = "area"  # Area measurement in m², cm², km², mm², in², ft², yd², mi², ac, ha
    ATMOSPHERIC_PRESSURE = "atmospheric_pressure"  # Atmospheric pressure in cbar, bar, hPa, mmHg, inHg, kPa, mbar, Pa, psi
    BATTERY = "battery"  # Battery level percentage (%)
    BLOOD_GLUCOSE_CONCENTRATION = "blood_glucose_concentration"  # Blood glucose levels in mg/dL, mmol/L
    CARBON_DIOXIDE = "carbon_dioxide"  # CO2 concentration in parts per million (ppm)
    CARBON_MONOXIDE = "carbon_monoxide"  # CO concentration in parts per million (ppm)
    CURRENT = "current"  # Electrical current in A, mA
    DATA_RATE = "data_rate"  # Data transfer rate in bit/s, kbit/s, Mbit/s, Gbit/s, B/s, kB/s, MB/s, GB/s, KiB/s, MiB/s, GiB/s
    DATA_SIZE = "data_size"  # Data size in bit, kbit, Mbit, Gbit, B, kB, MB, GB, TB, PB, EB, ZB, YB, KiB, MiB, GiB, TiB, PiB, EiB, ZiB, YiB
    DATE = "date"  # Date in ISO 8601 format
    DISTANCE = "distance"  # Distance in km, m, cm, mm, mi, nmi, yd, in
    DURATION = "duration"  # Time duration in d, h, min, s, ms
    ENERGY = "energy"  # Energy consumption in J, kJ, MJ, GJ, mWh, Wh, kWh, MWh, GWh, TWh, cal, kcal, Mcal, Gcal
    ENERGY_STORAGE = "energy_storage"  # Stored energy in J, kJ, MJ, GJ, mWh, Wh, kWh, MWh, GWh, TWh, cal, kcal, Mcal, Gcal
    ENUM = "enum"  # Enumerated states (non-numeric values)
    FREQUENCY = "frequency"  # Frequency in Hz, kHz, MHz, GHz
    GAS = "gas"  # Gas volume in m³, ft³, CCF
    HUMIDITY = "humidity"  # Relative humidity percentage (%)
    ILLUMINANCE = "illuminance"  # Light level in lux (lx)
    IRRADIANCE = "irradiance"  # Irradiance in W/m² or BTU/(h⋅ft²)
    MOISTURE = "moisture"  # Moisture level percentage (%)
    MONETARY = "monetary"  # Currency value (ISO 4217)
    NITROGEN_DIOXIDE = "nitrogen_dioxide"  # NO2 concentration in µg/m³
    NITROGEN_MONOXIDE = "nitrogen_monoxide"  # NO concentration in µg/m³
    NITROUS_OXIDE = "nitrous_oxide"  # N2O concentration in µg/m³
    OZONE = "ozone"  # O3 concentration in µg/m³
    PH = "ph"  # pH value of water solution
    PM1 = "pm1"  # Particulate matter < 1 µm in µg/m³
    PM25 = "pm25"  # Particulate matter < 2.5 µm in µg/m³
    PM10 = "pm10"  # Particulate matter < 10 µm in µg/m³
    POWER_FACTOR = "power_factor"  # Power factor (unitless or %)
    POWER = "power"  # Power in mW, W, kW, MW, GW, TW
    PRECIPITATION = "precipitation"  # Accumulated precipitation in cm, in, mm
    PRECIPITATION_INTENSITY = "precipitation_intensity"  # Precipitation rate in in/d, in/h, mm/d, mm/h
    PRESSURE = "pressure"  # Pressure in Pa, kPa, hPa, bar, cbar, mbar, mmHg, inHg, psi
    REACTIVE_POWER = "reactive_power"  # Reactive power in var
    SIGNAL_STRENGTH = "signal_strength"  # Signal strength in dB or dBm
    SOUND_PRESSURE = "sound_pressure"  # Sound pressure in dB or dBA
    SPEED = "speed"  # Speed in ft/s, in/d, in/h, in/s, km/h, kn, m/s, mph, mm/d, mm/s
    SULPHUR_DIOXIDE = "sulphur_dioxide"  # SO2 concentration in µg/m³
    TEMPERATURE = "temperature"  # Temperature in °C, °F, K
    TIMESTAMP = "timestamp"  # Timestamp in ISO 8601 format or datetime object
    VOLATILE_ORGANIC_COMPOUNDS = "volatile_organic_compounds"  # VOC concentration in µg/m³
    VOLATILE_ORGANIC_COMPOUNDS_PARTS = "volatile_organic_compounds_parts"  # VOC ratio in ppm or ppb
    VOLTAGE = "voltage"  # Voltage in V, mV, µV, kV, MV
    VOLUME = "volume"  # Volume in L, mL, gal, fl. oz., m³, ft³, CCF
    VOLUME_FLOW_RATE = "volume_flow_rate"  # Flow rate in m³/h, ft³/min, L/min, gal/min, mL/s
    VOLUME_STORAGE = "volume_storage"  # Stored volume in L, mL, gal, fl. oz., m³, ft³, CCF
    WATER = "water"  # Water consumption in L, gal, m³, ft³, CCF
    WEIGHT = "weight"  # Mass in kg, g, mg, µg, oz, lb, st
    WIND_SPEED = "wind_speed"  # Wind speed in Beaufort, ft/s, km/h, kn, m/s, mph


# https://www.home-assistant.io/integrations/binary_sensor/
class HABinarySensorDeviceClass(Enum):
    """Home Assistant Binary Sensor Device Classes."""

    # none should not be sent as str. device_class should be excluded
    # NONE = "none"  # Generic on/off sensor with no specific type
    BATTERY = "battery"  # Battery level: on=low, off=normal
    BATTERY_CHARGING = (
        "battery_charging"  # Battery charging status: on=charging, off=not charging
    )
    CARBON_MONOXIDE = "carbon_monoxide"  # CO detector: on=detected, off=clear
    COLD = "cold"  # Temperature sensor: on=cold, off=normal
    CONNECTIVITY = (
        "connectivity"  # Network connectivity: on=connected, off=disconnected
    )
    DOOR = "door"  # Door position sensor: on=open, off=closed
    GARAGE_DOOR = "garage_door"  # Garage door position: on=open, off=closed
    GAS = "gas"  # Gas detector: on=detected, off=clear
    HEAT = "heat"  # Temperature sensor: on=hot, off=normal
    LIGHT = "light"  # Light sensor: on=light detected, off=no light
    LOCK = "lock"  # Lock status: on=unlocked, off=locked
    MOISTURE = "moisture"  # Moisture sensor: on=wet, off=dry
    MOTION = "motion"  # Motion sensor: on=motion detected, off=clear
    MOVING = "moving"  # Movement sensor: on=moving, off=stopped
    OCCUPANCY = "occupancy"  # Occupancy sensor: on=occupied, off=clear
    OPENING = "opening"  # Generic opening sensor: on=open, off=closed
    PLUG = "plug"  # Plug status: on=plugged in, off=unplugged
    POWER = "power"  # Power sensor: on=power detected, off=no power
    PRESENCE = "presence"  # Presence sensor: on=home, off=away
    PROBLEM = "problem"  # Problem sensor: on=problem detected, off=OK
    RUNNING = "running"  # Running status: on=running, off=not running
    SAFETY = "safety"  # Safety sensor: on=unsafe, off=safe
    SMOKE = "smoke"  # Smoke detector: on=detected, off=clear
    SOUND = "sound"  # Sound sensor: on=sound detected, off=clear
    TAMPER = "tamper"  # Tamper sensor: on=tampering detected, off=clear
    UPDATE = "update"  # Update status: on=update available, off=up-to-date
    VIBRATION = "vibration"  # Vibration sensor: on=vibration detected, off=clear
    WINDOW = "window"  # Window position: on=open, off=closed


class HASensorType(Enum):
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
