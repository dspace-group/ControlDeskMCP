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

- These files are generated artifacts. Do not edit them manually.
- Regenerate them after changing tools, resources, prompts, or their schemas, then
	review and commit the resulting JSON together with the code change.
- The generated counts are informational and may change as the server surface
	evolves.
- Transport: stdio
- Server command: python -m controldesk_mcp
