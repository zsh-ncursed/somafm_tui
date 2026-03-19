# 📜 Документация скриптов автоматизации

Эта директория содержит скрипты для автоматизации разработки и релизов.

---

## 🗂 Обзор файлов

| Файл | Назначение | Язык | Зависимости |
|------|------------|------|-------------|
| `release.sh` | Автоматизация релиза | Bash | git, pytest, gh (опц.) |
| `sync_version.py` | Синхронизация версии | Python 3.8+ | git (опц.) |

---

## 📦 `release.sh` — Автоматизация релиза

### Назначение

Полная автоматизация процесса релиза: от обновления версии до публикации на GitHub.

### Использование

```bash
./scripts/release.sh <версия>
./scripts/release.sh 0.6.6
```

### Требования

- **Bash** 4.0+
- **Git**
- **pytest** (для запуска тестов)
- **gh CLI** (опционально, для создания GitHub Release)

### Что делает

| Шаг | Действие |
|-----|----------|
| 1 | Проверка ветки (должна быть `main`) |
| 2 | Проверка отсутствия существующего тега |
| 3 | Предупреждение о незакоммиченных изменениях |
| 4 | Обновление версии в `pyproject.toml` |
| 5 | Запуск тестов (`pytest tests/ -v`) |
| 6 | Создание git-коммита |
| 7 | Создание аннотированного тега |
| 8 | Push ветки и тега в GitHub |
| 9 | Создание GitHub Release (если `gh` установлен) |

### Примеры

```bash
# Патч-релиз (багфикс)
./scripts/release.sh 0.6.6

# Минор-релиз (новая функция)
./scripts/release.sh 0.7.0

# Мажор-релиз (breaking changes)
./scripts/release.sh 1.0.0
```

### Интерактивные prompts

Скрипт запрашивает подтверждение в случаях:

- Вы не на `main` → `Continue anyway? (y/N)`
- Есть незакоммиченные изменения → `Continue anyway? (y/N)`

### Выходные данные

После успешного релиза:

```
✓ Release 0.6.6 completed successfully!

What happens next:
  1. GitHub Actions will run CI tests
  2. If tests pass, packages will be published to:
     - PyPI (https://pypi.org/project/somafm-tui/)
     - AUR (https://aur.archlinux.org/packages/somafm_tui)
  3. GitHub Release will be available at:
     https://github.com/zsh-ncursed/somafm_tui/releases/tag/v0.6.6
```

### Коды возврата

| Код | Описание |
|-----|----------|
| `0` | Успех |
| `1` | Ошибка (версия не указана, тег существует, тесты не прошли) |

### Troubleshooting

#### Тег уже существует

```bash
git tag -d v0.6.6
git push origin :refs/tags/v0.6.6
./scripts/release.sh 0.6.6
```

#### Тесты не прошли

```bash
pytest tests/ -v
# Исправьте ошибки
./scripts/release.sh 0.6.6
```

#### `gh` CLI не установлен

Скрипт продолжит работу, но предложит создать Release вручную:
```
Create GitHub Release manually at:
https://github.com/zsh-ncursed/somafm_tui/releases/new
```

---

## 🔄 `sync_version.py` — Синхронизация версии

### Назначение

Синхронизация версии между файлами проекта из единого источника истины.

### Использование

```bash
# Из pyproject.toml (по умолчанию)
python scripts/sync_version.py

# Из последнего git-тега
python scripts/sync_version.py --from-tag

# Явное указание версии
python scripts/sync_version.py 0.6.6
```

### Требования

- **Python** 3.8+
- **Git** (для опции `--from-tag`)

### Аргументы командной строки

| Аргумент | Описание |
|----------|----------|
| `version` | Целевая версия (опционально) |
| `--from-tag` | Получить версию из последнего тега |

### Что делает

1. Получает версию из источника (тег или `pyproject.toml`)
2. Проверяет формат SemVer (`MAJOR.MINOR.PATCH`)
3. Обновляет `pyproject.toml` если версия отличается
4. Выводит инструкции для следующих шагов

### Примеры

```bash
# Перед релизом - синхронизация из тега
python scripts/sync_version.py --from-tag

# После ручного изменения версии в pyproject.toml
python scripts/sync_version.py

# Принудительная установка версии
python scripts/sync_version.py 0.7.0
```

### Выходные данные

```
Using version from git tag: 0.6.6
✓ Updated pyproject.toml: version = "0.6.6"

✓ Version synchronized: 0.6.6

Next steps:
  1. git add pyproject.toml
  2. git commit -m 'Bump version to 0.6.6'
  3. git push && git push origin v0.6.6
  Or run: ./scripts/release.sh 0.6.6
```

### Коды возврата

| Код | Описание |
|-----|----------|
| `0` | Успех |
| `1` | Ошибка (нет тегов, версия не найдена, неверный формат) |

### Troubleshooting

#### No git tags found

```bash
# Создайте первый тег
git tag -a v0.6.5 -m "Initial release"
git push origin v0.6.5
```

#### Version not found in pyproject.toml

Проверьте, что в `pyproject.toml` есть строка:
```toml
[project]
version = "0.6.5"
```

---

## 🔗 Интеграция между скриптами

### Типичный рабочий процесс

```bash
# 1. Синхронизируйте версию из тега (если нужно)
python scripts/sync_version.py --from-tag

# 2. Внесите изменения в код
git add <файлы>
git commit -m "Feature: новое звучание"

# 3. Запустите релиз
./scripts/release.sh 0.6.6
```

### Альтернативный workflow

```bash
# 1. Измените версию вручную в pyproject.toml
# version = "0.6.6"

# 2. Закоммитьте
git add pyproject.toml
git commit -m "Bump version to 0.6.6"

# 3. Запуште (тег создастся автоматически)
git push origin main
# GitHub Actions создаст тег v0.6.6
```

---

## 📚 Связанная документация

| Файл | Описание |
|------|----------|
| `docs/VERSIONING.md` | Полная документация по версионированию |
| `docs/QUICKSTART_VERSIONING.md` | Быстрый старт |
| `.github/workflows/auto-version-tag.yml` | Авто-создание тега |
| `.github/workflows/publish.yml` | Публикация на PyPI |
| `.github/workflows/publish-aur.yml` | Публикация в AUR |

---

## 🛠️ Разработка скриптов

### Тестирование `release.sh`

```bash
# Запуск с проверкой синтаксиса
bash -n scripts/release.sh

# Запуск в режиме отладки
bash -x scripts/release.sh 0.6.6
```

### Тестирование `sync_version.py`

```bash
# Проверка синтаксиса
python -m py_compile scripts/sync_version.py

# Запуск с help
python scripts/sync_version.py --help
```

### Добавление новых функций

1. Внесите изменения в скрипт
2. Протестируйте локально
3. Обновите документацию в этом файле
4. Добавьте тесты (если применимо)

---

## 📋 Чек-лист перед использованием

```markdown
- [ ] Скрипты исполняемые: `chmod +x scripts/*.sh scripts/*.py`
- [ ] Вы находитесь в корневой директории проекта
- [ ] Все зависимости установлены
- [ ] Вы на ветке `main`
- [ ] Тесты проходят локально
```

---

*Последнее обновление: 19 марта 2026 г.*
