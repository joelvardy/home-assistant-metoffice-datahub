"""Constants for the Met Office (DataHub) integration."""

DOMAIN = "metoffice_datahub"

CONF_API_KEY = "api_key"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"

BASE_URL = "https://data.hub.api.metoffice.gov.uk/sitespecific/v0/point"
ENDPOINTS = {
    "hourly": "/hourly",
    "three_hourly": "/three-hourly",
    "daily": "/daily"
}

DEFAULT_SCAN_INTERVAL = 3600  # 1 hour
