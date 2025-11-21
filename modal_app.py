import modal

# Build an image with all dependencies + Playwright browser
image = (
    modal.Image.debian_slim()
    .pip_install(
        "fastmcp",
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
    secrets=[modal.Secret.from_dotenv()],  # loads your .env into env vars
    keep_warm=1,
)
@modal.asgi_app()
def run():
    import sys
    # Add the app directory to path so we can import event_scraper_mcp_server
    sys.path.insert(0, "/root/app")

    import event_scraper_mcp_server

    # Return the HTTP ASGI application from the FastMCP instance
    # FastMCP.http_app() is a method that returns the Starlette/ASGI application
    return event_scraper_mcp_server.app.http_app()


@app.local_entrypoint()
def main():
    # Run locally using Modal's CLI
    run.remote()
