import sys
from pathlib import Path


PYTHON_APP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_APP_ROOT))
