from homeassistant import core, loader

_orig_async_suggest_report_issue = loader.async_suggest_report_issue

_async_suggest_report_issue_mock_call_tracker = []


@core.callback
def async_suggest_report_issue_mock(*args, **kwargs):
    _async_suggest_report_issue_mock_call_tracker.append((args, kwargs))
    return _orig_async_suggest_report_issue(*args, **kwargs)


loader.async_suggest_report_issue = async_suggest_report_issue_mock
