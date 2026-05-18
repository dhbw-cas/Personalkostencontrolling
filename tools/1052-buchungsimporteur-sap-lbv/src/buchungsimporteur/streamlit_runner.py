"""Run the Streamlit app via a console script."""

from __future__ import annotations

import sys
from pathlib import Path

from streamlit.web import cli as stcli


def main() -> None:
    app_path = Path(__file__).resolve().parents[2] / "streamlit_app.py"
    if not app_path.exists():
        raise FileNotFoundError(f"Streamlit app not found: {app_path}")

    sys.argv = ["streamlit", "run", str(app_path)]
    stcli.main()


if __name__ == "__main__":
    main()
