# DNP3 SCADA CoCT Add-on
Homeassistant addon for outstations at >100kVA, < 1MVA Embedded Generation Plants communicating with City of Cape Town SCADA master.

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https://github.com/Voyanti/dnp3-scadat-test)

## Usage 
1. Add the repository URL to Homeassistant Add-on Store using the button above. Alternatively, add the repository by going to `Settings>Add-ons>Add-on Store>Three Dots>Repositories` and paste the URL
2. Setup a MQTT broker e.g. Mosquitto
3. Connect to a VPN if needed using the appropraite add-on
4. Enter relevant details in Add-on Configuration

## Configuration
Make sure to set the outstaion address to the CoCT provided site-specific one. Configure you MQTT server user details and ip. The master address should be pre-filled under `server`.

## Development
1. Clone
2. `python3 -m pip install -r requirements.txt`

> Note that opendnp3 (C++ library) is a dependency for dnp3-python, which might not be prebuild for your system/architecture. Use the Dockerfile in that case.