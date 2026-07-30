# Security Policy

## Supported Versions

The following versions of ControlDesk MCP Server are currently supported with security fixes:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability, open a
[GitHub Security Advisory](../../security/advisories/new) in the Security tab
of this repository. Include as much detail as possible to help reproduce and
understand the scope of the issue.

### What to Include

When reporting a vulnerability, please provide:

- A clear description of the issue and its potential impact
- Steps to reproduce the vulnerability
- Affected version(s)
- Any known workarounds or mitigations

### Response SLA

| Milestone              | Target time                         |
| ---------------------- | ----------------------------------- |
| Initial acknowledgment | Within 3 business days              |
| Severity assessment    | Within 7 business days              |
| Fix or mitigation plan | Communicated after assessment       |
| Public disclosure      | Coordinated with reporter after fix |

### Disclosure Policy

We follow a coordinated disclosure model:

1. Reporter submits vulnerability privately.
2. Maintainers confirm receipt and begin assessment.
3. A fix or mitigation is developed and validated.
4. A patch release is issued.
5. A security advisory is published after affected users have had reasonable
   time to update.

We ask that reporters refrain from publicly disclosing the vulnerability until
we have issued a fix and coordinated the disclosure timeline.

## Scope

This policy covers the ControlDesk MCP Server source code and its distributed
package artifacts. It does not cover third-party dependencies (report those to
their respective maintainers) or the dSPACE ControlDesk product itself (contact
dSPACE support for product-level issues).

## Out of Scope

The following are **not** considered security vulnerabilities for this project:

- Issues that require physical access to a machine where ControlDesk is installed
- Vulnerabilities in dependencies not introduced or modified by this project
- COM automation behaviors that are by-design Windows platform features
