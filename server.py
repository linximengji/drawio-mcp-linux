"""Draw.io MCP — Agent-driven diagram creation via cli-anything-drawio."""
import os
import json
import subprocess

from mcp.server.fastmcp import FastMCP

CLI = os.environ.get("DRAWIO_CLI", "cli-anything-drawio")
DRAWIO = os.environ.get("DRAWIO_BIN", "drawio")
WORKDIR = os.path.join(os.path.dirname(__file__), "diagrams")
os.makedirs(WORKDIR, exist_ok=True)

mcp = FastMCP("drawio-mcp")


def _run(*args) -> str:
    """Run cli-anything-drawio directly (no python wrapper), return JSON or text."""
    result = subprocess.run(
        [CLI, "--json", *args],
        capture_output=True, text=True, timeout=30,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return f"ERROR (rc={result.returncode}): {result.stderr or result.stdout}"
    return result.stdout.strip()


def _export_drawio(path: str, out_path: str, fmt: str = "png", scale: int = 2) -> str:
    """Export using draw.io directly with --no-sandbox (avoid Electron GUI hang)."""
    if not os.path.isfile(path):
        return f"ERROR: input file not found: {path}"
    result = subprocess.run(
        [DRAWIO, "--no-sandbox", "-x", path, "-o", out_path, "-f", fmt,
         "-s", str(scale)],
        capture_output=True, text=True, timeout=60,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return f"ERROR (rc={result.returncode}): {result.stderr or result.stdout}"
    if not os.path.isfile(out_path):
        return f"ERROR: draw.io produced no output file\nstderr: {result.stderr[-300:]}"
    size = os.path.getsize(out_path)
    return json.dumps({"output": out_path, "format": fmt, "file_size": size})


@mcp.tool()
def new_diagram(filename: str, preset: str = "16:9") -> str:
    """Create a new blank draw.io diagram.

    Args:
        filename: Name for the diagram file (e.g., 'architecture.drawio')
        preset: Page size — '16:9', '4:3', 'a3', 'a4', 'letter', 'square'
    """
    path = os.path.join(WORKDIR, filename)
    return _run("project", "new", "-o", path, "--preset", preset)


@mcp.tool()
def add_shape(filename: str, shape: str, label: str = "",
              x: int = 100, y: int = 100,
              width: int = 120, height: int = 80, page: str = "") -> str:
    """Add a shape to a draw.io diagram.

    Args:
        filename: Diagram filename (e.g., 'architecture.drawio')
        shape: Shape type — 'rect', 'ellipse', 'diamond', 'text', 'triangle', 'hexagon'
        label: Text label on the shape
        x: X position in pixels
        y: Y position in pixels
        width: Width in pixels
        height: Height in pixels
        page: Page name (empty string for current page)
    """
    path = os.path.join(WORKDIR, filename)
    opts = ["--label", label, "--x", str(x), "--y", str(y),
            "--width", str(width), "--height", str(height)]
    if page:
        opts += ["--page", page]
    return _run("--project", path, "shape", "add", shape, *opts)


@mcp.tool()
def connect_shapes(filename: str, source: str, target: str,
                   label: str = "", style: str = "") -> str:
    """Connect two shapes with an arrow/connector.

    Args:
        filename: Diagram filename
        source: Source shape ID (e.g., 'v_1780241842236170')
        target: Target shape ID
        label: Optional label on the connector
        style: Connector style — 'straight', 'curved', 'orthogonal'
    """
    path = os.path.join(WORKDIR, filename)
    opts = ["--source", source, "--target", target]
    if label:
        opts += ["--label", label]
    if style:
        opts += ["--style", style]
    return _run("--project", path, "connect", "add", *opts)


@mcp.tool()
def export_diagram(filename: str, format: str = "png", scale: int = 2) -> str:
    """Export diagram to an image file.

    Args:
        filename: Diagram filename
        format: Export format — 'png', 'pdf', 'svg'
        scale: Scale factor for raster formats (1-4)
    """
    path = os.path.join(WORKDIR, filename)
    out_path = os.path.join(WORKDIR, f"{os.path.splitext(filename)[0]}.{format}")
    return _export_drawio(path, out_path, format, scale)


@mcp.tool()
def list_diagrams() -> str:
    """List all saved diagrams in the workspace."""
    files = [f for f in os.listdir(WORKDIR) if f.endswith(".drawio")]
    if not files:
        return "No diagrams found."
    return "\n".join(f"  {f}" for f in sorted(files))


if __name__ == "__main__":
    mcp.run(transport="stdio")
