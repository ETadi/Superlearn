# Security Policy

## Reporting a vulnerability

Please use **GitHub's private vulnerability reporting** on this repository
(Security → Report a vulnerability) rather than a public issue, so a fix can
land before details are public. Reports are read on a best-effort basis — this
is a personal open-source project, not a staffed security team.

Only the latest `master` is supported; there are no maintained release
branches.

## Threat model

Superlearn is a **local, single-user tool**: a loopback HTTP server hosting a
web app over board files on your own disk, driven by your own Claude Code
session. There are no accounts, no secrets, and nothing listens beyond
127.0.0.1 unless you pass `--host` yourself.

The interesting attack surface is that **board content is untrusted** — it is
authored by a model from scraped web pages. The defenses in place:

| Surface | Defense |
|---|---|
| Rendered markdown | Escape-first renderer; raw HTML in board text is never interpreted |
| Links & images | `http(s)` only via `safeUrl`; images additionally allow raster-only `data:` URIs (SVG excluded — it can carry script) |
| Video embeds | Pinned to validated 11-char YouTube IDs, played in YouTube's own iframe |
| Runnable code blocks | Sandboxed iframe with `allow-scripts` and **no** `allow-same-origin` — opaque origin, no access to the app's DOM, storage, or API; results cross by postMessage matched on frame identity |
| Standalone HTML exports | Board JSON neutralized for script context (`<` → `<`, U+2028/29 escaped) against `</script>` breakout |
| DNS rebinding | The server validates the `Host` header; loopback names only by default, bare IPs allowed only when deliberately bound wider |
| Research file API | Read-only, path-traversal checked, whitelisted extensions |
| Board writes (PUT) | Slug-validated IDs, size-capped bodies, JSON-validated, unique-temp-file atomic writes |

## Out of scope

- Anything reachable only by running the server with `--host 0.0.0.0` on a
  hostile network — widening the bind is an explicit opt-in.
- Denial of service against your own local server.
- The content of third-party pages, videos, and papers the researcher links to.
