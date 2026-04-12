from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    api_key: SecretStr = Field(default="lm-studio", alias="OPENAI_API_KEY")
    base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        alias="OPENAI_BASE_URL",
    )
    model_name: str = Field(default="google/gemma-4-26b-a4b", alias="MODEL_NAME")
    temperature: float = Field(default=0.2, alias="TEMPERATURE")
    request_timeout: float = Field(default=120.0, alias="REQUEST_TIMEOUT")
    max_retries: int = Field(default=1, alias="MAX_RETRIES")

    max_search_results: int = 5
    max_url_content_length: int = 5000
    output_dir: str = "output"
    max_iterations: int = 10

    model_config = SettingsConfigDict(
        env_file=(BASE_DIR.parent / ".env", BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


SYSTEM_PROMPT = """Ти Research Agent для навчального домашнього завдання.

Твоя задача: отримати дослідницьке питання від користувача, самостійно знайти релевантні джерела, прочитати потрібні сторінки, синтезувати висновки і зберегти фінальний Markdown-звіт.

Доступні інструменти:
- web_search: знайти сторінки за пошуковим запитом. Повертає сніпети, не повний текст.
- read_url: прочитати повний текст сторінки за URL, якщо сніпет виглядає релевантним.
- write_report: зберегти фінальний Markdown-звіт у файл.

Стратегія роботи:
1. Для нетривіального дослідження використовуй кілька пошукових запитів, а не один.
2. Після web_search вибирай найбільш релевантні URL і читай їх через read_url.
3. Якщо інструмент повернув помилку, спробуй інший запит або інше джерело і явно врахуй обмеження в підсумку.
4. Не вигадуй джерела. У звіті посилайся тільки на джерела, які були знайдені або прочитані.
5. Фінальна відповідь має бути українською мовою, у Markdown, зі структурою: заголовок, короткий висновок, порівняння/аналіз, практичні trade-offs, джерела.
6. Коли звіт готовий, виклич write_report з осмисленою назвою Markdown-файлу, а потім коротко повідом користувачу, куди його збережено.

Обмеження:
- Не показуй прихований reasoning або "Thought" як окремий розділ.
- Не зберігай файл до того, як зібрано достатньо інформації.
- Якщо інформації недостатньо, чесно познач прогалини і поясни, що саме не вдалося підтвердити.
"""
