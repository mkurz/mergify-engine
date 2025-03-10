# -*- encoding: utf-8 -*-
#
# Copyright © 2020 Mergify SAS
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import fastapi
from starlette import requests
from starlette import responses

from mergify_engine import exceptions as engine_exceptions


app = fastapi.FastAPI()


def _get_badge_url(
    owner: str, repo: str, ext: str, style: str
) -> responses.RedirectResponse:
    return responses.RedirectResponse(
        url=f"https://img.shields.io/endpoint.{ext}?url=https://dashboard.mergify.com/badges/{owner}/{repo}&style={style}",
        status_code=302,
    )


@app.get("/{owner}/{repo}.png")  # noqa: FS003
async def badge_png(
    owner: str, repo: str, style: str = "flat"
) -> responses.RedirectResponse:  # pragma: no cover
    return _get_badge_url(owner, repo, "png", style)


@app.get("/{owner}/{repo}.svg")  # noqa: FS003
async def badge_svg(
    owner: str, repo: str, style: str = "flat"
) -> responses.RedirectResponse:  # pragma: no cover
    return _get_badge_url(owner, repo, "svg", style)


@app.get("/{owner}/{repo}")  # noqa: FS003
async def badge(owner: str, repo: str) -> responses.RedirectResponse:
    return responses.RedirectResponse(
        url=f"https://dashboard.mergify.com/badges/{owner}/{repo}"
    )


@app.exception_handler(engine_exceptions.RateLimited)
async def rate_limited_handler(
    request: requests.Request, exc: engine_exceptions.RateLimited
) -> responses.JSONResponse:
    return responses.JSONResponse(
        status_code=403,
        content={"message": "Organization or user has hit GitHub API rate limit"},
    )
