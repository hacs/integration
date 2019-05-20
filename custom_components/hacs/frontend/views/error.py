"""CommunityAPI View for HACS."""
import logging
import traceback
import sys

from custom_components.hacs.frontend.elements import style

_LOGGER = logging.getLogger(__name__)


async def error_view():
    """Return this on error."""
    ex_type, ex_value, ex_traceback = sys.exc_info()

    trace_back = traceback.extract_tb(ex_traceback)
    stack_trace = list()
    for trace in trace_back:
        stack_trace.append(
            "File : %s , Line : %d, Func.Name : %s, Message : %s"
            % (trace[0], trace[1], trace[2], trace[3])
        )
    pretty_trace = ""
    for trace in stack_trace:
        pretty_trace += """
            {}
        """.format(
            trace
        )
    content = await style()

    content += "<h2>Something is super wrong...</h2>"

    if ex_type is not None:
        content += """
            <p>Exception type: {}</p>
            <p>Exception message: {}</p>
            <code class="codeblock">{}</code>
        """.format(
            ex_type.__name__, ex_value, pretty_trace
        )

    content += """
    </br></br>
    <a href='https://github.com/custom-components/hacs/issues/new'
        class='waves-effect waves-light btn'
        target="_blank">
        OPEN ISSUE
    </a>
    """
    return content
