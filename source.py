"""Утилиты для работы с исходными .py файлами."""

from pathlib import Path


SrcFilesDict = dict[str, list[str]]


def resolve_source_file(profile_filename: str, src_files: SrcFilesDict) -> str:
    """Находит ключ в src_files, соответствующий пути из профиля.

    Пробует сопоставление от полного пути до имени файла,
    с учётом регистра и суффиксов пути.

    Args:
        profile_filename: путь к файлу из данных профилировщика
        src_files: словарь {имя/путь -> строки файла}

    Returns:
        Ключ из src_files или исходный profile_filename, если не найден.
    """
    p = Path(profile_filename)
    pf = p.as_posix()
    base = p.name

    if pf in src_files:
        return pf

    if base in src_files:
        return base

    parts = pf.split("/")
    for length in range(len(parts), 0, -1):
        sub = "/".join(parts[-length:])
        if sub in src_files:
            return sub

    for key in src_files.keys():
        if base.lower() == Path(key).name.lower():
            return key

    return pf


def load_src_lines(file_name: str, src_files: SrcFilesDict) -> list[str] | None:
    """Загружает строки исходного файла.

    Сначала ищет в src_files (загруженные пользователем),
    затем пробует прочитать с диска.

    Args:
        file_name: путь из данных профилировщика
        src_files: словарь загруженных исходников

    Returns:
        Список строк файла или None, если файл не найден.
    """
    resolved = resolve_source_file(file_name, src_files)
    src_lines = src_files.get(resolved)

    if not src_lines:
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                src_lines = f.read().splitlines()
        except OSError:
            return None

    return src_lines


def get_source_line(fn: str, lineno: int, src_files: SrcFilesDict) -> str:
    """Возвращает одну строку исходника по номеру.

    Args:
        fn: путь к файлу из профиля
        lineno: номер строки (1-based)
        src_files: словарь загруженных исходников

    Returns:
        Строка кода или пустая строка, если не найдена.
    """
    src_lines = load_src_lines(fn, src_files)

    if not src_lines:
        return ""

    if 0 < lineno <= len(src_lines):
        return src_lines[lineno - 1]

    return ""


def extract_function_by_indent(src_lines: list[str], start_line: int) -> list[tuple[int, str]]:
    """Извлекает строки функции из исходника по отступу.

    Ищет `def` начиная с start_line (пропуская декораторы),
    затем собирает тело функции пока отступ больше отступа def.

    Args:
        src_lines: список строк исходника
        start_line: строка начала функции из профилировщика (1-based)

    Returns:
        Список пар (номер_строки, текст_строки).
    """
    i = start_line - 1

    # пропускаем декораторы
    while i < len(src_lines) and src_lines[i].strip().startswith("@"):
        i += 1

    # ищем def
    while i < len(src_lines) and not src_lines[i].strip().startswith("def "):
        i += 1

    if i >= len(src_lines):
        return []

    def_line_index = i
    def_line = src_lines[def_line_index]
    indent_def = len(def_line) - len(def_line.lstrip())

    func_lines: list[tuple[int, str]] = []

    # строки от start_line до def включительно (декораторы + def)
    for j in range(start_line - 1, def_line_index + 1):
        func_lines.append((j + 1, src_lines[j]))

    # тело функции
    for k in range(def_line_index + 1, len(src_lines)):
        line = src_lines[k]
        stripped = line.strip()

        if stripped == "":
            func_lines.append((k + 1, line))
            continue

        current_indent = len(line) - len(line.lstrip())

        if current_indent <= indent_def:
            break

        func_lines.append((k + 1, line))

    return func_lines