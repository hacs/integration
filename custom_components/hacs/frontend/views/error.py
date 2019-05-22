"""CommunityAPI View for HACS."""
import logging
import random
import traceback
import sys

from custom_components.hacs.const import ERROR
from custom_components.hacs.frontend.elements import style, generic_button_external

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

    content += "<div class='container'>"

    content += "<h2>Something is wrong...</h2>"
    content += "<b>Error code:</b> <i>{}</i>".format(random.choice(ERROR))

    if ex_type is not None:
        content += """
            <p><b>Exception type:</b> {}</p>
            <p><b>Exception message:</b> {}</p>
            <p><b>Stacktrace:</b></p>
            <code class="codeblock" style="display: block; margin-bottom: 30px;">{}</code>
        """.format(
            ex_type.__name__,
            ex_value,
            pretty_trace.replace(
                "File :",
                "</br>---------------------------------------------------------------</br><b>File :</b>",
            )
            .replace(", Line :", "</br><b>Line :</b>")
            .replace(", Func.Name :", "</br><b>Func.Name :</b>")
            .replace(", Message :", "</br><b>Message :</b>")[86:-1],
        )

    content += await generic_button_external(
        "https://github.com/custom-components/hacs/issues/new/choose", "OPEN ISSUE"
    )
    content += await generic_button_external("/community_api/log/get", "OPEN LOG")
    content += "<div class='center-align' style='margin-top: 100px'>"
    content += "<img src='https://i.pinimg.com/originals/ec/85/67/ec856744fac64a5a9e407733f190da5a.png'>"
    content += "</div>"

    return content
