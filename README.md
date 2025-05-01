# Met Office (DataHub) Integration

This integration provides access to weather data from the Met Office DataHub API.

Troon from the Home Assistant forum did a huge amount of heavy lifting to get this integration working. See his post explaining how to access the Met Office DataHub API [here](https://community.home-assistant.io/t/template-weather-provider-from-uk-met-office-datahub-api/695692).

## Installation

1. Copy the `metoffice_datahub` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration > Integrations
4. Click the "+" button and search for "Met Office (DataHub)"
5. Enter your API key and location coordinates

Alternatively, you can install this integration using HACS (Home Assistant Community Store). If you don't have HACS installed, you can find instructions [here](https://hacs.xyz/docs/installation/installation).
