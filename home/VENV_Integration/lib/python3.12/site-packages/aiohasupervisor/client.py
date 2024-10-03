"""Internal client for making requests and managing session with Supervisor."""

from dataclasses import dataclass, field
from http import HTTPMethod, HTTPStatus
from importlib import metadata
from typing import Any

from aiohttp import (
    ClientError,
    ClientResponse,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
)
from yarl import URL

from .const import ResponseType
from .exceptions import (
    SupervisorAuthenticationError,
    SupervisorBadRequestError,
    SupervisorConnectionError,
    SupervisorError,
    SupervisorForbiddenError,
    SupervisorNotFoundError,
    SupervisorResponseError,
    SupervisorServiceUnavailableError,
    SupervisorTimeoutError,
)
from .models.base import Response, ResultType

VERSION = metadata.version(__package__)


def is_json(response: ClientResponse, *, raise_on_fail: bool = False) -> bool:
    """Check if response is json according to Content-Type."""
    content_type = response.headers.get("Content-Type", "")
    if "application/json" not in content_type:
        if raise_on_fail:
            raise SupervisorResponseError(
                "Unexpected response received from supervisor when expecting"
                f"JSON. Status: {response.status}, content type: {content_type}",
            )
        return False
    return True


@dataclass(slots=True)
class _SupervisorClient:
    """Main class for handling connections with Supervisor."""

    api_host: str
    token: str
    request_timeout: int
    session: ClientSession | None = None
    _close_session: bool = field(default=False, init=False)

    @property
    def timeout(self) -> ClientTimeout:
        """Timeout for requests."""
        return ClientTimeout(total=self.request_timeout)

    async def _request(
        self,
        method: HTTPMethod,
        uri: str,
        *,
        params: dict[str, str] | None,
        response_type: ResponseType,
        json: dict[str, Any] | None = None,
        data: Any = None,
    ) -> Response:
        """Handle a request to Supervisor."""
        try:
            url = URL(self.api_host).joinpath(uri)
        except ValueError as err:
            raise SupervisorError from err

        # This check is to make sure the normalized URL string is the same as the URL
        # string that was passed in. If they are different, then the passed in uri
        # contained characters that were removed by the normalization
        # such as ../../../../etc/passwd
        if not url.raw_path.endswith(uri):
            raise SupervisorError(f"Invalid request {uri}")

        match response_type:
            case ResponseType.TEXT:
                accept = "text/plain, */*"
            case _:
                accept = "application/json, text/plain, */*"

        headers = {
            "User-Agent": f"AioHASupervisor/{VERSION}",
            "Accept": accept,
            "Authorization": f"Bearer {self.token}",
        }

        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        try:
            async with self.session.request(
                method.value,
                url,
                timeout=self.timeout,
                headers=headers,
                params=params,
                json=json,
                data=data,
            ) as response:
                if response.status >= HTTPStatus.BAD_REQUEST.value:
                    exc_type: type[SupervisorError] = SupervisorError
                    match response.status:
                        case HTTPStatus.BAD_REQUEST:
                            exc_type = SupervisorBadRequestError
                        case HTTPStatus.UNAUTHORIZED:
                            exc_type = SupervisorAuthenticationError
                        case HTTPStatus.FORBIDDEN:
                            exc_type = SupervisorForbiddenError
                        case HTTPStatus.NOT_FOUND:
                            exc_type = SupervisorNotFoundError
                        case HTTPStatus.SERVICE_UNAVAILABLE:
                            exc_type = SupervisorServiceUnavailableError

                    if is_json(response):
                        result = Response.from_json(await response.text())
                        raise exc_type(result.message, result.job_id)
                    raise exc_type()

                match response_type:
                    case ResponseType.JSON:
                        is_json(response, raise_on_fail=True)
                        return Response.from_json(await response.text())
                    case ResponseType.TEXT:
                        return Response(ResultType.OK, await response.text())
                    case _:
                        return Response(ResultType.OK)

        except (UnicodeDecodeError, ClientResponseError) as err:
            raise SupervisorResponseError(
                "Unusable response received from Supervisor, check logs",
            ) from err
        except TimeoutError as err:
            raise SupervisorTimeoutError("Timeout connecting to Supervisor") from err
        except ClientError as err:
            raise SupervisorConnectionError(
                "Error occurred connecting to supervisor",
            ) from err

    async def get(
        self,
        uri: str,
        *,
        params: dict[str, str] | None = None,
        response_type: ResponseType = ResponseType.JSON,
    ) -> Response:
        """Handle a GET request to Supervisor."""
        return await self._request(
            HTTPMethod.GET,
            uri,
            params=params,
            response_type=response_type,
        )

    async def post(
        self,
        uri: str,
        *,
        params: dict[str, str] | None = None,
        response_type: ResponseType = ResponseType.NONE,
        json: dict[str, Any] | None = None,
        data: Any = None,
    ) -> Response:
        """Handle a POST request to Supervisor."""
        return await self._request(
            HTTPMethod.POST,
            uri,
            params=params,
            response_type=response_type,
            json=json,
            data=data,
        )

    async def put(
        self,
        uri: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Response:
        """Handle a PUT request to Supervisor."""
        return await self._request(
            HTTPMethod.PUT,
            uri,
            params=params,
            response_type=ResponseType.NONE,
            json=json,
        )

    async def delete(
        self,
        uri: str,
        *,
        params: dict[str, str] | None = None,
    ) -> Response:
        """Handle a DELETE request to Supervisor."""
        return await self._request(
            HTTPMethod.DELETE,
            uri,
            params=params,
            response_type=ResponseType.NONE,
        )

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()


class _SupervisorComponentClient:
    """Common ancestor for all component clients of supervisor."""

    def __init__(self, client: _SupervisorClient) -> None:
        """Initialize sub module with client for API calls."""
        self._client = client
