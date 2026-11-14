# Registry endpoints and gotchas

What `scripts/pkgcheck.py` calls. Useful when debugging a check or writing a new one.

## npm

```
GET https://registry.npmjs.org/{name}
GET https://registry.npmjs.org/{name}/{version}
```

- Scoped names need `@scope%2Fname` in the URL path.
- `dist-tags.latest` is the tag, not necessarily the newest publish.
- `versions[v].deprecated` is a string when deprecated.
- `time.modified` is the last publish time.
- A name not in the registry returns `{"error":"Not found"}` with 404.

## PyPI

```
GET https://pypi.org/pypi/{name}/json
GET https://pypi.org/pypi/{name}/{version}/json
```

- Names are normalized: `my_pkg`, `my-pkg` and `My.Pkg` are the same project.
- `releases[v]` is a list; `yanked` per file. A yanked-only version is effectively unusable.
- `info.requires_python` is the runtime constraint.
- Deleted projects may 404 or serve a tombstone.

## crates.io

```
GET https://crates.io/api/v1/crates/{name}
```

- Requires a descriptive `User-Agent`; requests without one are rejected.
- `crate.max_version`, `crate.updated_at`, `versions[].yanked`.

## NuGet

```
GET https://api.nuget.org/v3-flatcontainer/{id}/index.json
```

- Package IDs are case-insensitive; the path must be lowercase.
- The response is a bare version list, oldest to newest.
- Unlisted versions still appear here; the registration API is needed to see listing status.

## RubyGems

```
GET https://rubygems.org/api/v1/gems/{name}.json
GET https://rubygems.org/api/v1/versions/{name}.json
```

- 404 means the gem name is free or unknown.

## Go modules

```
GET https://proxy.golang.org/{module}/@v/list
```

- Module paths are case-sensitive with `!` escaping for uppercase; the proxy handles simple
  paths directly.
- `+incompatible` and pseudo-versions show up in the list.

## GitHub

```
GET https://api.github.com/repos/{owner}/{repo}
```

- Unauthenticated: 60 requests/hour per IP; 403 with `rate limit` is not a 404.
- `archived`, `pushed_at`, `stargazers_count`, `license.spdx_id`.
- Redirects for renamed repositories are followed; the final repo name may differ.

## URLs

```bash
pkgcheck.py url https://example.com/page
```

- Sends `HEAD`, falls back to a ranged `GET` for servers that reject `HEAD`.
- 403/429 means blocked, not missing; report it as unverified.
- A 200 on a redirect means the redirect target is what you verified - check `response.url`
  when the exact page matters.

## Failure semantics

| Signal | Verdict |
|---|---|
| 404 | not present on that registry as of the check |
| 403 / 429 / 5xx / timeout / DNS | unverified |
| 200 with empty body | inspect the payload; may be a soft delete |

Never turn a transport failure into a factual claim.
