import curses


def _select_item(stdscr: curses.window, items: list[str], page_step: int = 5) -> str | None:
    if not items:
        return None

    curses.curs_set(0)
    stdscr.keypad(True)

    current_idx: int = 0
    num_items: int = len(items)

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        for i in range(min(num_items, height - 1)):
            idx: int = i
            item: str = items[idx]

            if idx == current_idx:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(i, 0, f"> {item}"[: width - 1])
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(i, 0, f"  {item}"[: width - 1])

        stdscr.refresh()
        key: int = stdscr.getch()

        if key in (curses.KEY_ENTER, 10, 13):
            return items[current_idx]
        if key == 27:  # Escape key
            return None
        if key == curses.KEY_UP:
            current_idx = max(0, current_idx - 1)
        elif key == curses.KEY_DOWN:
            current_idx = min(num_items - 1, current_idx + 1)
        elif key == curses.KEY_PPAGE:  # Page Up
            current_idx = max(0, current_idx - page_step)
        elif key == curses.KEY_NPAGE:  # Page Down
            current_idx = min(num_items - 1, current_idx + page_step)


def select_item(items: list[str], page_step: int = 5) -> str | None:
    return curses.wrapper(_select_item, items, page_step)
