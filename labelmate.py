from src.paths import ensure_user_data
from src.db import init_db
from src.qt_gui import run_gui


def main():
    ensure_user_data()
    init_db()
    run_gui()


if __name__ == '__main__':
    main()
