"""
Custom authentication for STEAD video streaming.

Allows authentication via query parameter for HTML5 video elements
which cannot send custom Authorization headers.
"""

from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework import exceptions


class QueryParamTokenAuthentication(TokenAuthentication):
    """
    Token authentication via query parameter.
    
    HTML5 video elements cannot send custom headers, so we need to accept
    the token as a query parameter for video streaming endpoints.
    
    Usage:
        <video src="/api/stead/video/stream/?token=YOUR_TOKEN">
    """
    
    def authenticate(self, request):
        # First try standard header authentication
        auth = super().authenticate(request)
        if auth:
            return auth
        
        # Then try query parameter
        token_key = request.GET.get('token') or request.query_params.get('token')
        
        if not token_key:
            return None
        
        return self.authenticate_credentials(token_key)
    
    def authenticate_credentials(self, key):
        """
        Authenticate the token key and return user.
        """
        try:
            token = Token.objects.select_related('user').get(key=key)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')
        
        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')
        
        return (token.user, token)


class OptionalQueryParamTokenAuthentication(QueryParamTokenAuthentication):
    """
    Same as QueryParamTokenAuthentication but doesn't require authentication.
    Returns None if no valid token is found instead of raising an exception.
    """
    
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except exceptions.AuthenticationFailed:
            return None
