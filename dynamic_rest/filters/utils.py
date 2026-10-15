"""Filter utils."""
from __future__ import annotations

from django.db.models import Q, QuerySet

from dynamic_rest.compat import RestFrameworkBooleanField
from dynamic_rest.constants import VALID_FILTER_OPERATORS
from dynamic_rest.datastructures import FilterNode, TreeMap
from dynamic_rest.serializers import DynamicModelSerializer
from dynamic_rest.utils import is_truthy


def _or(a: Q, b: Q) -> Q:
    """Return a or b."""
    return a | b


def _and(a: Q, b: Q) -> Q:
    """Return a and b."""
    return a & b


def has_joins(queryset: QuerySet) -> bool:
    """Return True iff. a queryset includes joins.

    If this is the case, it is possible for the queryset
    to return duplicate results.

    Arguments:
        queryset: A queryset.

    Returns:
        True if the queryset includes joins.
    """
    return any(join.join_type for join in queryset.query.alias_map.values())


def has_multivalued_joins(queryset: QuerySet) -> bool:
    """Return True iff. a queryset joins across a multi-valued relation.

    Only joins that can match several rows per row of the base table
    (many-to-many and reverse foreign key / generic relations) can make
    the queryset return duplicate results. Joins that follow a forward
    foreign key or a one-to-one relation cannot.

    A join that cannot be classified is treated as multi-valued.

    Arguments:
        queryset: A queryset.

    Returns:
        True if the queryset can return duplicate results.
    """
    for join in queryset.query.alias_map.values():
        if not join.join_type:
            continue
        join_field = getattr(join, "join_field", None)
        if join_field is None or join_field.one_to_many or join_field.many_to_many:
            return True
    return False


def rewrite_filters(
    filters: TreeMap, serializer: DynamicModelSerializer
) -> dict[str, str | bool]:
    """Rewrite filter keys to use model field names."""
    out = {}
    for node in filters.values():
        filter_key, field = node.generate_query_key(serializer)
        if isinstance(field, RestFrameworkBooleanField):
            node.value = is_truthy(node.value)
        out[filter_key] = node.value
    return out


def clause_to_q(clause: tuple[str, str | int], serializer: DynamicModelSerializer) -> Q:
    """Convert a filter clause to a Django Q object."""
    key, value = clause
    negate = False
    if key.startswith("-"):
        negate = True
        key = key[1:]
    parts = key.split(".")
    operator = parts.pop() if parts[-1] in VALID_FILTER_OPERATORS else "eq"
    if operator == "eq":
        operator = None
    node = FilterNode(parts, operator, value)
    key, _ = node.generate_query_key(serializer)
    q = Q(**{key: node.value})
    if negate:
        q = ~q
    return q
