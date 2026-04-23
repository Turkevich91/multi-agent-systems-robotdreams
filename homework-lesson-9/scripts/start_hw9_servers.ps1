$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")

$servers = @(
    @{ Name = "SearchMCP"; Command = "uv run python mcp_servers/search_mcp.py"; Url = "http://127.0.0.1:8901/mcp" },
    @{ Name = "ReportMCP"; Command = "uv run python mcp_servers/report_mcp.py"; Url = "http://127.0.0.1:8902/mcp" },
    @{ Name = "ACP"; Command = "uv run python acp_server.py"; Url = "http://127.0.0.1:8903" }
)

foreach ($server in $servers) {
    $command = "Set-Location '$Root'; $($server.Command)"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $command -WindowStyle Normal
    Write-Host "Started $($server.Name): $($server.Url)"
}

Write-Host ""
Write-Host "After servers are ready, run:"
Write-Host "  cd $Root"
Write-Host "  uv run python main.py"
