import modal

# Build an image with all dependencies + Playwright browser
image = (
    modal.Image.debian_slim()
    .pip_install(
        "fastapi",
        "fastmcp",
        "pydantic",
        "httpx",
        "beautifulsoup4",
        "lxml",
        "python-dotenv",
        "playwright",
    )
    .run_commands(
        # Install Chromium for Playwright
        "python -m playwright install --with-deps chromium"
    )
    .add_local_dir(".", "/root/app")
)

app = modal.App("event-scraper-mcp")

@app.function(
    image=image,
    secrets=[modal.Secret.from_dotenv()],
    keep_warm=1,
)
@modal.asgi_app()
def web():
    import sys

    sys.path.insert(0, "/root/app")
    from event_scraper_mcp_server import make_mcp_server

    # Create the MCP server instance
    mcp = make_mcp_server()

    # Return the MCP HTTP app directly without FastAPI wrapper
    # This allows proper HTTP/JSON-RPC exposure for tool discovery
    return mcp.http_app(
        transport="streamable-http",
        stateless_http=True,
    )