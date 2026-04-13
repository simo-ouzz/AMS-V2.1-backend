# Backward compatibility: DJANGO_SETTINGS_MODULE=config.settings still works.
# For explicit environments, use config.settings.dev or config.settings.prod.
from config.settings.base import *  # noqa
