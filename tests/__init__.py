import json

from awesomeversion import AwesomeVersion
from homeassistant import const, core, loader

_async_suggest_report_issue_mock_call_tracker = []

try:
    _orig_async_suggest_report_issue = loader.async_suggest_report_issue
except AttributeError:
    if AwesomeVersion(const.__version__) >= "2023.11.0":
        raise RuntimeError("loader.async_suggest_report_issue does not exist")

    @core.callback
    def _fallback_async_suggest_report_issue(*args, **kwargs):
        return json.dumps(kwargs)

    _orig_async_suggest_report_issue = _fallback_async_suggest_report_issue


@core.callback
def async_suggest_report_issue_mock(*args, **kwargs):
    result = _orig_async_suggest_report_issue(*args, **kwargs)
    _async_suggest_report_issue_mock_call_tracker.append(result)
    return result


loader.async_suggest_report_issue = async_suggest_report_issue_mock
