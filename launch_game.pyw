from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
GAME_DIR = PROJECT_ROOT / "ignore"

if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))

from game import main


if __name__ == "__main__":
    main()
