"""Utilities for dynamic_rest."""
from functools import lru_cache

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.module_loading import import_string
from sqids import Sqids

FALSEY_STRINGS = (
    "0",
    "false",
    "",
)


@lru_cache()
def is_truthy(x):
    """Return True if x is truthy, False otherwise."""
    if isinstance(x, str):
        return x.lower() not in FALSEY_STRINGS
    return bool(x)


def unpack(content):
    """Unpack a content dict from a DynamicSerializer."""
    if not content:
        # empty values pass through
        return content

    keys = [k for k in content.keys() if k != "meta"]
    unpacked = content[keys[0]]
    return unpacked


def external_id_from_model_and_internal_id(model, internal_id):
    """Return a hash for the model and internal ID combination."""
    sqids = Sqids()

    if sqids is None:
        raise AssertionError(
            "To use hashids features you must set "
            "ENABLE_HASHID_FIELDS to true in your dynamic_rest settings."
        )
    return sqids.encode([ContentType.objects.get_for_model(model).id, internal_id])


def internal_id_from_model_and_external_id(model, external_id):
    """Return the internal ID from the external ID and model combination.

    Because the SqID is a combination of the model's content type and the
    internal ID, we validate here that the external ID decodes as expected,
    and that the content type corresponds to the model we're expecting.
    """
    sqids = Sqids()

    if sqids is None:
        raise AssertionError(
            "To use hashids features you must set "
            "ENABLE_HASHID_FIELDS to true in your dynamic_rest settings."
        )

    try:
        (  # pylint: disable=unbalanced-tuple-unpacking
            content_type_id,
            instance_id,
        ) = sqids.decode(external_id)
    except (TypeError, ValueError) as exc:
        raise model.DoesNotExist from exc

    content_type = ContentType.objects.get_for_id(content_type_id)

    if content_type.model_class() != model:
        raise model.DoesNotExist

    return instance_id


def model_from_definition(model_definition):
    """Return a Django model corresponding to model_definition.

    Model definition can either be a string defining how to import the model,
    or a model class.

    Arguments:
        model_definition: (str|django.db.models.Model)

    Returns:
        (django.db.models.Model)

    Implementation from
    https://github.com/evenicoulddoit/django-rest-framework-serializer-extensions
    """
    if isinstance(model_definition, str):
        model = import_string(model_definition)
    else:
        model = model_definition

    try:
        assert issubclass(model, models.Model)
    except (AssertionError, TypeError) as exc:
        raise AssertionError(f'"{model_definition}"" is not a Django model') from exc

    return model
