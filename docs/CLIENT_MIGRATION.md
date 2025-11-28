# Client Migration Guide: Azure to Docker Stack

This guide documents the changes needed in the frontend client to migrate from Azure Static Web Apps (SWA) authentication to the new Docker-based JWT authentication.

## Overview

| Component | Azure Stack | Docker Stack |
|-----------|-------------|--------------|
| Authentication | Azure SWA (/.auth/*) | JWT Bearer tokens |
| Real-time | Azure Web PubSub SDK | Native WebSocket |
| API Base | /api/* | /api/* (unchanged) |
| User Info | /.auth/me | /auth/me |

## 1. Authentication Changes

### Remove Azure SWA Auth

**Before (Azure SWA):**
```typescript
// Login was handled by Azure SWA redirect
window.location.href = '/.auth/login/aad';

// Get user info
const response = await fetch('/.auth/me');
const { clientPrincipal } = await response.json();
```

**After (JWT):**
```typescript
// Login with email/password
const response = await fetch('/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({
    username: email,
    password: password,
  }),
});
const { access_token, refresh_token } = await response.json();

// Store tokens securely
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);

// Get user info
const userResponse = await fetch('/auth/me', {
  headers: { 'Authorization': `Bearer ${access_token}` },
});
const user = await userResponse.json();
```

### OAuth/SSO Login (Optional)

If using external OAuth providers (Azure AD, Google, etc.), the flow is:

1. Frontend handles OAuth redirect to provider
2. Provider redirects back with token/code
3. Frontend verifies with provider and gets user email
4. Frontend calls new endpoint:

```typescript
const response = await fetch('/auth/oauth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: verifiedEmail,
    name: displayName,
    provider: 'azure'  // or 'google', 'github', etc.
  }),
});
const { access_token, refresh_token } = await response.json();
```

### Token Management

**Add to API client:**
```typescript
// api-client.ts
class ApiClient {
  private getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers = new Headers(options.headers);

    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const response = await fetch(endpoint, { ...options, headers });

    // Handle 401 - try refresh token
    if (response.status === 401) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        headers.set('Authorization', `Bearer ${this.getToken()}`);
        return fetch(endpoint, { ...options, headers }).then(r => r.json());
      }
      // Redirect to login
      window.location.href = '/login';
    }

    return response.json();
  }

  async refreshToken(): Promise<boolean> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return false;

    try {
      const response = await fetch('/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (response.ok) {
        const { access_token, refresh_token } = await response.json();
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', refresh_token);
        return true;
      }
    } catch (e) {
      console.error('Token refresh failed', e);
    }
    return false;
  }
}
```

### User Types and Roles

The JWT token now contains user claims directly:

```typescript
// Decode JWT to get user info (for display only - server validates)
interface JWTPayload {
  sub: string;           // User ID (UUID)
  email: string;
  name: string;
  user_type: 'PLATFORM' | 'ORG';
  is_superuser: boolean;
  org_id: string | null;
  roles: string[];       // ['authenticated', 'PlatformAdmin'] or ['authenticated', 'OrgUser', ...]
  exp: number;
}

function parseJwt(token: string): JWTPayload {
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  return JSON.parse(window.atob(base64));
}
```

## 2. WebSocket Changes

### Remove Azure Web PubSub

**Before (Azure Web PubSub):**
```typescript
import { WebPubSubClient } from '@azure/web-pubsub-client';

const client = new WebPubSubClient(negotiatedUrl);
client.on('server-message', (message) => {
  // Handle message
});
await client.start();
```

**After (Native WebSocket):**
```typescript
class BifrostWebSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnects = 5;

  connect(token: string) {
    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws?token=${token}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onclose = () => {
      this.attemptReconnect(token);
    };
  }

  private handleMessage(message: any) {
    switch (message.type) {
      case 'execution_update':
        // Handle execution status change
        this.onExecutionUpdate?.(message.data);
        break;
      case 'execution_log':
        // Handle new log entry
        this.onExecutionLog?.(message.data);
        break;
    }
  }

  private attemptReconnect(token: string) {
    if (this.reconnectAttempts < this.maxReconnects) {
      this.reconnectAttempts++;
      setTimeout(() => this.connect(token), 1000 * this.reconnectAttempts);
    }
  }

  subscribe(executionId: string) {
    this.ws?.send(JSON.stringify({
      action: 'subscribe',
      execution_id: executionId,
    }));
  }

  unsubscribe(executionId: string) {
    this.ws?.send(JSON.stringify({
      action: 'unsubscribe',
      execution_id: executionId,
    }));
  }

  // Event handlers (set by consumer)
  onExecutionUpdate?: (data: ExecutionUpdate) => void;
  onExecutionLog?: (data: ExecutionLog) => void;
}
```

## 3. API Endpoint Changes

Most API endpoints remain unchanged. Key differences:

| Endpoint | Change |
|----------|--------|
| `/.auth/login/*` | Removed - use `/auth/login` |
| `/.auth/logout` | Removed - clear tokens client-side |
| `/.auth/me` | Changed to `/auth/me` (requires Bearer token) |
| `/api/*` | Unchanged (add Bearer token header) |

## 4. Organization Header

For org-scoped operations, continue using the `X-Organization-Id` header:

```typescript
// Fetch org-specific data
const response = await fetch('/api/executions', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'X-Organization-Id': orgId,  // Optional for platform admins
  },
});
```

## 5. Environment Configuration

Update your client environment configuration:

```typescript
// Before
const config = {
  authProvider: 'aad',
  pubsubEndpoint: process.env.REACT_APP_PUBSUB_ENDPOINT,
};

// After
const config = {
  apiBaseUrl: process.env.REACT_APP_API_URL || '',
  wsBaseUrl: process.env.REACT_APP_WS_URL || '',
};
```

## 6. Migration Checklist

- [ ] Remove `@azure/web-pubsub-client` dependency
- [ ] Remove Azure SWA auth redirect logic
- [ ] Add JWT token storage and management
- [ ] Update API client to use Bearer token
- [ ] Implement token refresh logic
- [ ] Replace Azure Web PubSub with native WebSocket
- [ ] Update user info fetching to use `/auth/me`
- [ ] Add login/logout UI components
- [ ] Update environment configuration
- [ ] Test first-user registration (becomes PlatformAdmin)
- [ ] Test org-user auto-provisioning by email domain

## 7. TypeScript Types

The API types remain largely compatible. Key additions:

```typescript
// Auth response types
interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
}

interface UserResponse {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  user_type: 'PLATFORM' | 'ORG';
  organization_id: string | null;
  roles: string[];
}

// WebSocket message types
interface WSMessage {
  type: 'execution_update' | 'execution_log';
  data: ExecutionUpdate | ExecutionLog;
}

interface ExecutionUpdate {
  execution_id: string;
  status: string;
  result?: any;
  error_message?: string;
}

interface ExecutionLog {
  execution_id: string;
  level: string;
  message: string;
  timestamp: string;
}
```

## 8. Security Notes

1. **Token Storage**: Store tokens in `localStorage` or `sessionStorage`. For higher security, consider httpOnly cookies (requires API changes).

2. **Token Expiration**: Access tokens expire in 30 minutes by default. Use refresh tokens to get new access tokens.

3. **CORS**: The API allows origins configured in `CORS_ORIGINS`. Update this in production.

4. **First User**: The first user to log in becomes a PlatformAdmin automatically. Subsequent users must either:
   - Have their email domain match an organization's domain
   - Be manually added by an admin
