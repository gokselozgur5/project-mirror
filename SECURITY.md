# Security policy

Please report vulnerabilities privately through GitHub Security Advisories.
Do not open a public issue containing credentials, personal media, or a working
exploit against a deployed device.

## Trust boundaries

- Treat camera, microphone, browser, serial, and network input as untrusted.
- The character model cannot issue raw actuator values.
- The embodiment gateway clamps position, velocity, acceleration, and timeout.
- The firmware stops motion when its command heartbeat expires.
- Secrets belong in process environment or a secret manager, never Git.
- Enabling a serial controller requires a bearer token for pose and arm calls;
  emergency stop remains callable without authentication.
