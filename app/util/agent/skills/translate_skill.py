# -*- coding: UTF-8 -*-
"""Translation skill — prompt injection for translation tasks."""

from app.util.translate.models import ARGOS_LANGUAGES, LANG_NAMES_CN

SUPPORTED_LANGS_CN = ", ".join(f"{code}({name})" for code, name in LANG_NAMES_CN.items())

TRANSLATE_SKILL = f"""## 翻译能力

你可以使用 `translate_text` 工具翻译文本。

### 支持的语言
{SUPPORTED_LANGS_CN} 等 {len(ARGOS_LANGUAGES)} 种语言。

### 使用方式
- 自动检测源语言和目标语言（中文→英文，英文→中文），无需指定 target_lang
- 可显式指定 target_lang 翻译为特定语言
- 可指定翻译风格：general(通用) / formal(正式) / technical(技术文档)
- 回复时简洁展示译文，同时注明源语言和引擎

### 示例
- "翻译这段" → translate_text(text="...")
- "翻译这段为英文" → translate_text(text="...", target_lang="en")
- "把这句话正式翻译成日语" → translate_text(text="...", target_lang="ja", style="formal")
"""


def get_translate_skill() -> str:
    return TRANSLATE_SKILL
