# GitHub Workflows

## Обзор

Эта директория содержит GitHub Actions workflows для автоматизации CI/CD.

## Workflows

### 1. CI (`ci.yml`)

**Когда запускается:**
- Push в ветку `main`
- Pull Request в `main`
- Создание релиза (release created)

**Что делает:**
```
✅ Установка Python 3.8-3.12 (matrix)
✅ Установка зависимостей (mpv, libmpv-dev)
✅ Проверка синтаксиса Python
✅ Проверка импорта пакета
✅ Запуск всех тестов (pytest)
✅ Отчёт о покрытии (требуется 60%+)
✅ (Опционально) Загрузка в Codecov
```

**Требования:**
- Тесты должны проходить на всех версиях Python
- Покрытие кода ≥ 60%

---

### 2. Publish to PyPI (`publish.yml`)

**Когда запускается:**
- Изменение `pyproject.toml` в ветке `main`
- Ручной запуск (workflow_dispatch)

**Что делает:**
```
✅ Запуск тестов (как в CI)
✅ Сборка wheel и source tarball
✅ Публикация на PyPI
✅ Подпись Sigstore
✅ Загрузка на GitHub Release
```

**Важно:** Публикация блокируется, если тесты не прошли.

---

### 3. Publish to AUR (`publish-aur.yml`)

**Когда запускается:**
- Push тега версии (v*)
- Публикация релиза на GitHub
- Ручной запуск (workflow_dispatch)

**Что делает:**
```
✅ Запуск тестов (как в CI)
✅ Валидация PKGBUILD
✅ Обновление pkgver
✅ Публикация в AUR через SSH
```

**Важно:** Публикация блокируется, если тесты не прошли.

**Требуемые секреты:**
- `AUR_SSH_PRIVATE_KEY` — SSH ключ для AUR
- `AUR_USERNAME` — имя пользователя AUR
- `AUR_EMAIL` — email для AUR

---

## Требования к тестам

### Минимальное покрытие

| Модуль | Требуемое покрытие |
|--------|-------------------|
| Core логика (config, models, timer) | ≥ 85% |
| Сетевые модули (http_client, channels) | ≥ 85% |
| Состояние (state, playback, input) | ≥ 85% |
| UI (ui.py, player.py) | ≥ 15% (интеграция сложная) |
| **Общее покрытие** | **≥ 60%** |

### Запуск тестов локально

```bash
# Все тесты
pytest tests/ -v

# С покрытием
pytest tests/ --cov=somafm_tui --cov-report=term-missing

# Проверка порога покрытия
pytest tests/ --cov=somafm_tui --cov-fail-under=60
```

---

## Добавление новых тестов

1. Создайте файл `tests/test_<module>.py`
2. Используйте фикстуры из `tests/conftest.py`
3. Избегайте реальных сетевых вызовов (mock requests)
4. Запустите локально перед коммитом

### Пример теста

```python
# tests/test_example.py
from somafm_tui.config import validate_config

class TestConfig:
    def test_valid_config(self, sample_config_dict):
        """Should validate valid config without errors."""
        # Arrange
        config = sample_config_dict
        
        # Act & Assert (should not raise)
        validate_config(config)
```

---

## Troubleshooting

### Тесты не проходят в CI

1. Проверьте логи GitHub Actions
2. Запустите тесты локально с той же версией Python
3. Убедитесь, что все зависимости установлены

### Покрытие ниже 60%

```bash
# Узнать какие строки не покрыты
pytest --cov=somafm_tui --cov-report=term-missing

# Добавить тесты для непокрытых строк
```

### Ошибки импорта в CI

Убедитесь, что:
- Все импорты относительные (`from somafm_tui import ...`)
- Нет циклических импортов
- Все зависимости в `requirements.txt`

---

## Версионирование

При релизе новой версии:

1. Обновите версию в `pyproject.toml`:
   ```toml
   version = "0.7.0"  # SemVer: MAJOR.MINOR.PATCH
   ```

2. Обновите `CHANGELOG.md`

3. Создайте тег:
   ```bash
   git tag v0.7.0
   git push origin v0.7.0
   ```

4. GitHub Actions автоматически:
   - Запустит тесты
   - Опубликует на PyPI
   - Опубликует в AUR
   - Создаст релиз на GitHub

---

## Контакты

- **Issues**: https://github.com/zsh-ncursed/somafm_tui/issues
- **Discussions**: https://github.com/zsh-ncursed/somafm_tui/discussions
