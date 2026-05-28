from __future__ import annotations

from database import criar_tabela
from ui.app import App


def main() -> None:
    criar_tabela()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
