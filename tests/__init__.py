import json

from awesomeversion import AwesomeVersion
from homeassistant import const, core, loader

_async_suggest_report_issue_mock_call_tracker = []
_orig_async_suggest_report_issue = loader.async_suggest_report_issue


@core.callback
def async_suggest_report_issue_mock(*args, **kwargs):
    result = _orig_async_suggest_report_issue(*args, **kwargs)
    _async_suggest_report_issue_mock_call_tracker.append(result)
    return result


loader.async_suggest_report_issue = async_suggest_report_issue_mock
