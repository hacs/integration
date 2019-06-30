"""Serve error for HACS."""
# pylint: disable=broad-except
import logging
import random
import sys
import traceback

from aiohttp import web

from ...blueprints import HacsViewBase
from ...const import ERROR, ISSUE_URL

_LOGGER = logging.getLogger("custom_components.hacs..frontend")


class HacsErrorView(HacsViewBase):
    """Serve error."""

    name = "community_error"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["error"]

    async def get(self, request):  # pylint: disable=unused-argument
        """Serve error."""
        try:
            # Get last error
            ex_type, ex_value, ex_traceback = sys.exc_info()
            trace_back = traceback.extract_tb(ex_traceback)
            stack_trace = list()

            for trace in trace_back:
                stack_trace.append(
                    "File : {} , Line : {}, Func.Name : {}, Message : {}",
                    format(trace[0], trace[1], trace[2], trace[3]),
                )

            # HARD styling
            stacks = ""
            for stack in stack_trace:
                stacks += stack
            stacks = stacks.replace(
                "File :",
                "</br>---------------------------------------------------------------</br><b>File :</b>",
            )
            stacks = stacks.replace(", Line :", "</br><b>Line :</b>")
            stacks = stacks.replace(", Func.Name :", "</br><b>Func.Name :</b>")
            stacks = stacks.replace(", Message :", "</br><b>Message :</b>")[86:-1]

            if ex_type is not None:
                codeblock = """
                    <p><b>Exception type:</b> {}</p>
                    <p><b>Exception message:</b> {}</p>
                    <code class="codeblock errorview"">{}</code>
                """.format(
                    ex_type.__name__, ex_value, stacks
                )
            else:
                codeblock = ""

            # Generate content
            content = self.base_content
            content += """
                <div class='container'>
                    <h2>Something is wrong...</h2>
                    <b>Error code:</b> <i>{}</i>
                    {}
                </div>
                <div class='container'>
                    <a href='{}/new/choose' class='waves-effect waves-light btn right hacsbutton'
                        target="_blank">OPEN ISSUE</a>
                </div>
                <div class='center-align' style='margin-top: 100px'>
                    <img rel="noreferrer" src='https://i.pinimg.com/originals/ec/85/67/ec856744fac64a5a9e407733f190da5a.png'>
                </div>
            """.format(
                random.choice(ERROR), codeblock, ISSUE_URL)

        except Exception as exception:
            message = "GREAT!, even the error page is broken... ({})".format(exception)
            _LOGGER.error(message)
            content = self.base_content
            content += message

        return web.Response(body=content, content_type="text/html", charset="utf-8")
