# Based on official examples from Auth0
# https://github.com/auth0-blog/auth0-python-fastapi-sample/blob/main/application/utils.py

from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes

from core.config import settings


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str, **kwargs):
        """Returns HTTP 403"""
        super().__init__(status.HTTP_403_FORBIDDEN, detail=detail)


class UnauthenticatedException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Requires authentication"
        )


class VerifyToken:
    """
    Token verification using PyJWT
    """

    def __init__(self):
        self.config = settings

        # This gets the JWKS from a given URL and does processing so you can
        # use any of the keys available
        jwks_url = f"https://{self.config.auth0_domain}/.well-known/jwks.json"
        self.jwks_client = jwt.PyJWKClient(jwks_url)

    async def verify(  # noqa: C901
        self,
        security_scopes: SecurityScopes,
        token: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer()),
    ):
        if settings.skip_auth:
            return "Auth was skipped"

        if token is None:
            raise UnauthenticatedException

        # This gets the 'kid' from the passed token
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(
                token.credentials
            ).key
        except jwt.exceptions.PyJWKClientError as error:
            raise UnauthorizedException(str(error))
        except jwt.exceptions.DecodeError as error:
            raise UnauthorizedException(str(error))

        try:
            payload = jwt.decode(
                token.credentials,
                signing_key,
                algorithms=self.config.auth0_algorithms,
                audience=self.config.auth0_api_audience,
                issuer=self.config.auth0_issuer,
            )
        except Exception as error:
            raise UnauthorizedException(str(error))

        if len(security_scopes.scopes) > 0:
            self._check_claims(payload, "scope", security_scopes.scopes)

        return payload

    def _check_claims(self, payload, claim_name, expected_value) -> None:
        if claim_name not in payload:
            raise UnauthorizedException(
                detail=f'No claim "{claim_name}" found in token'
            )

        payload_claim = payload[claim_name]

        if claim_name == "scope":
            payload_claim = payload[claim_name].split(" ")

        for value in expected_value:
            if value not in payload_claim:
                raise UnauthorizedException(detail=f'Missing "{claim_name}" scope')
