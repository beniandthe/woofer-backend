from .base import *  # noqa

DEBUG = True

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "core.renderers.EnvelopeJSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
