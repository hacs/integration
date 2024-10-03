"""Helpers to manage Cluster attributes."""

from typing import Any

from ...common.helpers.util import create_attribute_path


def parse_attributes_from_read_result(
    raw_tlv_attributes: dict[int, dict[int, dict[int, Any]]],
) -> dict[str, Any]:
    """Parse attributes from ReadResult's TLV Attributes."""
    result = {}
    # prefer raw tlv attributes as it requires less parsing back and forth
    for endpoint_id, clusters in raw_tlv_attributes.items():
        for cluster_id, attribute in clusters.items():
            for attribute_id, attr_value in attribute.items():
                # we are only interested in the raw values and let the client
                # match back from the id's to the correct cluster/attribute classes
                # attributes are stored in form of AttributePath:
                # ENDPOINT/CLUSTER_ID/ATTRIBUTE_ID
                attribute_path = create_attribute_path(
                    endpoint_id, cluster_id, attribute_id
                )
                result[attribute_path] = attr_value
    return result
