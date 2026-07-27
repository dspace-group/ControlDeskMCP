# Release Verification and Artifact Policy

## Release Controls

Published releases are built from the annotated release tag. The workflow
rejects a release unless its tag, `pyproject.toml`, canonical runtime import
path, and a versioned `CHANGELOG.md` section agree.

Each release contains `ControlDeskMCP.exe` and its corresponding
`ControlDeskMCP.exe.sha256` checksum. Verify a downloaded executable with:

```powershell
Get-FileHash .\ControlDeskMCP.exe -Algorithm SHA256
```

Compare the resulting hash with the value in `ControlDeskMCP.exe.sha256` from
the same release.

The release workflow also creates a GitHub artifact attestation for the
executable. Verify provenance with:

```powershell
gh attestation verify <artifact-path> -R dSPACEGroup/ControlDeskMCP
```

## Signing Policy

The project does not yet publish a separately code-signed executable.
GitHub Actions signs build attestations with a short-lived Sigstore certificate;
consumers should verify the attestation and checksum before installation.

## Third-Party Dependencies and Notices

The executable bundles this project's runtime dependencies. The committed
`uv.lock` records the exact source dependencies used for the release build.

Before changing a dependency or publishing a release, maintainers must review
the dependency's license and notice obligations. Any dependency that requires
redistribution of notices must have its notice included with the release assets
and recorded in the corresponding changelog entry.
