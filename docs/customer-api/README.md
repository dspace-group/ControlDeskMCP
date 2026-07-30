# Customer API Artifacts

This folder contains generated MCP API artifacts for the ControlDesk MCP server.

## Update

Run the updater from the repository root:

``` powershell
./scripts/update-customer-api-docs.ps1
```

The script exports the MCP schema surfaces over stdio transport using:

``` powershell
python -m controldesk_mcp
```

## Generated Files

| File | Top-level field | Item count |
| --- | --- | ---: |
| tools_list.json | tools | 54 |
| resources_list.json | resources | 5 |
| resources_templates_list.json | resourceTemplates | 2 |
| prompts_list.json | prompts | 27 |

## Notes

- Generated at: 2026-07-30 16:59:00+05:30
- Inspector source: C:\Users\sureandhar.a\AppData\Local\npm-cache\_npx\5a9d879542beca3a\node_modules\.bin\mcp-inspector.ps1
- Transport: stdio
- Server command: python -m controldesk_mcp
