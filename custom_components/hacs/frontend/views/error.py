"""Serve error for HACS."""
# pylint: disable=broad-except
import logging
import random
import sys
import traceback

from aiohttp import web

from custom_components.hacs.blueprints import HacsViewBase
from custom_components.hacs.const import ERROR, ISSUE_URL

_LOGGER = logging.getLogger('custom_components.hacs.frontend')

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
                stack_trace.append(f"File : {trace[0]} , Line : {trace[1]}, Func.Name : {trace[2]}, Message : {trace[3]}")

            # HARD styling
            stacks = ""
            for stack in stack_trace:
                stacks += stack
            stacks = stacks.replace("File :", "</br>---------------------------------------------------------------</br><b>File :</b>")
            stacks = stacks.replace(", Line :", "</br><b>Line :</b>")
            stacks = stacks.replace(", Func.Name :", "</br><b>Func.Name :</b>")
            stacks = stacks.replace(", Message :", "</br><b>Message :</b>")[86:-1]



            if ex_type is not None:
                codeblock = f"""
                    <p><b>Exception type:</b> {ex_type.__name__}</p>
                    <p><b>Exception message:</b> {ex_value}</p>
                    <code class="codeblock errorview"">{stacks}</code>
                """
            else:
                codeblock = ""


            # Generate content
            content = self.base_content
            content += f"""
                <div class='container'>
                    <h2>Something is wrong...</h2>
                    <b>Error code:</b> <i>{random.choice(ERROR)}</i>
                    {codeblock}
                </div>
                <div class='container'>
                    <a href='{ISSUE_URL}/new/choose' class='waves-effect waves-light btn right hacsbutton'
                        target="_blank">OPEN ISSUE</a>

                    <a href='{self.url_path["api"]}/log/get' class='waves-effect waves-light btn right hacsbutton'
                        target="_blank">OPEN LOG</a>
                </div>
                <div class='center-align' style='margin-top: 100px'>
                    <img src='https://i.pinimg.com/originals/ec/85/67/ec856744fac64a5a9e407733f190da5a.png'>
                </div>
            """

        except Exception as exception:
            _LOGGER.debug(f"GREAT!, even the error page is broken... ({exception})")

        return web.Response(body=content, content_type="text/html", charset="utf-8")
