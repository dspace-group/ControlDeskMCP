# Release Verification and Artifact Policy

## Release Controls

Published releases are built from the annotated release tag. The workflow
rejects a release unless its tag, `pyproject.toml`, canonical runtime import
path, and a versioned `CHANGELOG.md` section agree.

Each release contains the source distribution, wheel, and `SHA256SUMS.txt`.
Verify a downloaded artifact with:

```powershell
Get-FileHash .\controldesk_mcp_server-<version>-py3-none-any.whl -Algorithm SHA256
```

Compare the resulting hash with the corresponding line in `SHA256SUMS.txt`.

The release workflow also creates a GitHub artifact attestation for the wheel
and source distribution. Verify provenance with:

```powershell
gh attestation verify <artifact-path> -R dSPACEGroup/ControlDeskMCP
```

## Signing Policy

The project does not publish separately key-signed wheels or source archives.
GitHub Actions signs build attestations with a short-lived Sigstore certificate;
consumers should verify the attestation and checksum before installation.

## Third-Party Dependencies and Notices

Published Python distributions contain this project's code and metadata, not
vendored third-party dependency code. Runtime dependencies are resolved from
the committed `uv.lock` and installed separately by the package manager.

Before changing a dependency or publishing a release, maintainers must review
the dependency's license and notice obligations. Any dependency that requires
redistribution of notices must have its notice included with the release assets
and recorded in the corresponding changelog entry.