_LANG_MAP = {
    "ru": "ru", "be": "ru", "uk": "ru",
    "he": "he", "iw": "he",
    "es": "es",
}

MSG: dict[str, dict[str, str]] = {
    "en": {
        "welcome": (
            "💃 <b>Milonga Finder</b>\n\n"
            "I'll help you find tango milongas in any city for today."
        ),
        "menu_prompt": "What would you like to do?",
        "btn_find": "🔍 Find milongas today",
        "btn_donate": "☕ Support the project",
        "ask_city": "🏙 <b>Enter the city name:</b>\n<i>e.g. Budapest, Tel Aviv, Buenos Aires</i>",
        "searching": "🔍 Searching for milongas in <b>{city}</b>…\n<i>This may take a few minutes while we search the web.</i>",
        "no_events": (
            "😕 No milongas or practicas found in <b>{city}</b> today.\n\n"
            "Try another city or check back tomorrow."
        ),
        "city_not_found": (
            "🌍 City <b>{city}</b> not found.\n\n"
            "Please check the spelling or try in English (e.g. <i>Moscow</i>, <i>Tbilisi</i>)."
        ),
        "events_header": "💃 <b>Tango in {city}</b>\n📅 {date}\n",
        "back": "↩️ Back",
        "donate_text": (
            "☕ <b>Support Milonga Finder</b>\n\n"
            "If this bot helps you dance more — buy me a coffee!\n"
            "Every ⭐ Star keeps the project running."
        ),
        "donate_title": "Support Milonga Finder",
        "donate_50": "☕ 50 ⭐",
        "donate_250": "🥐 250 ⭐",
        "donate_500": "🌟 500 ⭐",
        "donate_custom": "✏️ Any amount",
        "ask_stars_amount": "Enter the amount in Stars (minimum 50):",
        "invalid_stars": "⚠️ Please enter a valid number (minimum 50 Stars).",
        "close": "✖ Close",
        "donate_desc_tip": "A small tip to support Milonga Finder ☕",
        "donate_desc_30": "Unlock 30 days of unlimited searches in Milonga Finder",
        "donate_desc_90": "Unlock 90 days of unlimited searches in Milonga Finder",
        "donate_thanks": "🙏 Thank you so much! Your support means a lot. ❤️",
        "rate_limit": (
            "⏳ You've used all {limit} free searches for today.\n\n"
            "Support the project to unlock unlimited searches! ☕"
        ),
        "premium_granted": (
            "🎉 Thank you! Unlimited searches unlocked for <b>{days} days</b> (until {until}). ❤️"
        ),
        "status_premium": "⭐ <b>Status:</b> Premium until <b>{until}</b>. Unlimited searches.",
        "status_free": "🔍 <b>Status:</b> Free plan — <b>{remaining}</b> of {limit} searches left today.",
        "searches_left": "\n<i>({remaining} free search(es) left today)</i>",
        "disclaimer": "ℹ️ <i>AI-powered bot — info may be incomplete. Always verify with the organizer.</i>",
        "error": "⚠️ Something went wrong. Please try again.",
    },
    "ru": {
        "welcome": (
            "💃 <b>Milonga Finder</b>\n\n"
            "Помогу найти танго-милонги в любом городе на сегодня."
        ),
        "menu_prompt": "Что хотите сделать?",
        "btn_find": "🔍 Найти милонги сегодня",
        "btn_donate": "☕ Поддержать проект",
        "ask_city": "🏙 <b>Введите название города:</b>\n<i>например: Budapest, Tel Aviv, Buenos Aires</i>",
        "searching": "🔍 Ищу милонги в <b>{city}</b>…\n<i>Это может занять несколько минут — ищем в интернете.</i>",
        "no_events": (
            "😕 Милонги и практики в <b>{city}</b> сегодня не найдены.\n\n"
            "Попробуйте другой город или загляните завтра."
        ),
        "city_not_found": (
            "🌍 Город <b>{city}</b> не найден.\n\n"
            "Проверьте написание или попробуйте на английском (например: <i>Moscow</i>, <i>Tbilisi</i>)."
        ),
        "events_header": "💃 <b>Танго в {city}</b>\n📅 {date}\n",
        "back": "↩️ Назад",
        "donate_text": (
            "☕ <b>Поддержать Milonga Finder</b>\n\n"
            "Если бот помогает вам танцевать — угостите меня кофе!\n"
            "Каждая ⭐ Звезда помогает держать проект живым."
        ),
        "donate_title": "Поддержать Milonga Finder",
        "donate_50": "☕ 50 ⭐",
        "donate_250": "🥐 250 ⭐",
        "donate_500": "🌟 500 ⭐",
        "donate_custom": "✏️ Любая сумма",
        "ask_stars_amount": "Введите сумму в Stars (минимум 50):",
        "invalid_stars": "⚠️ Введите корректное число (минимум 50 Stars).",
        "close": "✖ Закрыть",
        "donate_desc_tip": "Небольшие чаевые для поддержки Milonga Finder ☕",
        "donate_desc_30": "30 дней безлимитного поиска в Milonga Finder",
        "donate_desc_90": "90 дней безлимитного поиска в Milonga Finder",
        "donate_thanks": "🙏 Большое спасибо! Ваша поддержка очень важна. ❤️",
        "rate_limit": (
            "⏳ Вы использовали все {limit} бесплатных поиска сегодня.\n\n"
            "Поддержите проект и получите безлимитный поиск! ☕"
        ),
        "premium_granted": (
            "🎉 Спасибо! Безлимит активирован на <b>{days} дней</b> (до {until}). ❤️"
        ),
        "status_premium": "⭐ <b>Статус:</b> Премиум до <b>{until}</b>. Безлимитный поиск.",
        "status_free": "🔍 <b>Статус:</b> Бесплатный план — осталось <b>{remaining}</b> из {limit} поисков сегодня.",
        "searches_left": "\n<i>(осталось {remaining} поиск(а) сегодня)</i>",
        "disclaimer": "ℹ️ <i>Бот на основе ИИ — информация может быть неполной. Уточняйте у организаторов.</i>",
        "error": "⚠️ Что-то пошло не так. Попробуйте ещё раз.",
    },
    "he": {
        "welcome": (
            "💃 <b>Milonga Finder</b>\n\n"
            "אמצא עבורך מילונגות טנגו בכל עיר להיום."
        ),
        "menu_prompt": "מה תרצה לעשות?",
        "btn_find": "🔍 מצא מילונגות להיום",
        "btn_donate": "☕ תמוך בפרויקט",
        "ask_city": "🏙 <b>הכנס שם עיר:</b>\n<i>לדוגמה: Budapest, Tel Aviv, Buenos Aires</i>",
        "searching": "🔍 מחפש מילונגות ב-<b>{city}</b>…\n<i>זה עשוי לקחת כמה דקות — אנחנו מחפשים באינטרנט.</i>",
        "no_events": (
            "😕 לא נמצאו מילונגות ופרקטיקות ב-<b>{city}</b> היום.\n\n"
            "נסה עיר אחרת או חזור מחר."
        ),
        "city_not_found": (
            "🌍 העיר <b>{city}</b> לא נמצאה.\n\n"
            "בדוק את האיות או נסה באנגלית (לדוגמה: <i>Moscow</i>, <i>Tbilisi</i>)."
        ),
        "events_header": "💃 <b>טנגו ב-{city}</b>\n📅 {date}\n",
        "back": "↩️ חזרה",
        "donate_text": (
            "☕ <b>תמוך ב-Milonga Finder</b>\n\n"
            "אם הבוט עוזר לך לרקוד יותר — קנה לי קפה!\n"
            "כל ⭐ כוכב עוזר להמשיך את הפרויקט."
        ),
        "donate_title": "תמוך ב-Milonga Finder",
        "donate_50": "☕ 50 ⭐",
        "donate_250": "🥐 250 ⭐",
        "donate_500": "🌟 500 ⭐",
        "donate_custom": "✏️ סכום חופשי",
        "ask_stars_amount": "הכנס סכום בכוכבים (מינימום 50):",
        "invalid_stars": "⚠️ הכנס מספר תקין (מינימום 50 כוכבים).",
        "close": "✖ סגור",
        "donate_desc_tip": "טיפ קטן לתמיכה ב-Milonga Finder ☕",
        "donate_desc_30": "30 ימי חיפוש ללא הגבלה ב-Milonga Finder",
        "donate_desc_90": "90 ימי חיפוש ללא הגבלה ב-Milonga Finder",
        "donate_thanks": "🙏 תודה רבה! התמיכה שלך מאוד חשובה. ❤️",
        "rate_limit": (
            "⏳ השתמשת בכל {limit} החיפושים החינמיים של היום.\n\n"
            "תמוך בפרויקט וקבל חיפוש ללא הגבלה! ☕"
        ),
        "premium_granted": (
            "🎉 תודה! חיפוש ללא הגבלה פעיל ל-<b>{days} ימים</b> (עד {until}). ❤️"
        ),
        "status_premium": "⭐ <b>סטטוס:</b> פרימיום עד <b>{until}</b>. חיפוש ללא הגבלה.",
        "status_free": "🔍 <b>סטטוס:</b> תוכנית חינמית — נותרו <b>{remaining}</b> מתוך {limit} חיפושים היום.",
        "searches_left": "\n<i>(נותרו {remaining} חיפוש/ים היום)</i>",
        "disclaimer": "ℹ️ <i>בוט מבוסס בינה מלאכותית — המידע עשוי להיות חלקי. תמיד בדקו עם המארגן.</i>",
        "error": "⚠️ משהו השתבש. נסה שוב.",
    },
    "es": {
        "welcome": (
            "💃 <b>Milonga Finder</b>\n\n"
            "Te ayudo a encontrar milongas de tango en cualquier ciudad para hoy."
        ),
        "menu_prompt": "¿Qué deseas hacer?",
        "btn_find": "🔍 Buscar milongas hoy",
        "btn_donate": "☕ Apoyar el proyecto",
        "ask_city": "🏙 <b>Ingresa el nombre de la ciudad:</b>\n<i>por ejemplo: Budapest, Tel Aviv, Buenos Aires</i>",
        "searching": "🔍 Buscando milongas en <b>{city}</b>…\n<i>Esto puede tardar unos minutos mientras buscamos en internet.</i>",
        "no_events": (
            "😕 No se encontraron milongas ni prácticas en <b>{city}</b> hoy.\n\n"
            "Prueba otra ciudad o vuelve mañana."
        ),
        "city_not_found": (
            "🌍 Ciudad <b>{city}</b> no encontrada.\n\n"
            "Verifica la ortografía o prueba en inglés (ej: <i>Moscow</i>, <i>Tbilisi</i>)."
        ),
        "events_header": "💃 <b>Tango en {city}</b>\n📅 {date}\n",
        "back": "↩️ Volver",
        "donate_text": (
            "☕ <b>Apoyar Milonga Finder</b>\n\n"
            "Si el bot te ayuda a bailar más — ¡invítame un café!\n"
            "Cada ⭐ Estrella mantiene el bot en marcha."
        ),
        "donate_title": "Apoyar Milonga Finder",
        "donate_50": "☕ 50 ⭐",
        "donate_250": "🥐 250 ⭐",
        "donate_500": "🌟 500 ⭐",
        "donate_custom": "✏️ Cualquier monto",
        "ask_stars_amount": "Ingresa el monto en Stars (mínimo 50):",
        "invalid_stars": "⚠️ Ingresa un número válido (mínimo 50 Stars).",
        "close": "✖ Cerrar",
        "donate_desc_tip": "Una propina para apoyar Milonga Finder ☕",
        "donate_desc_30": "30 días de búsquedas ilimitadas en Milonga Finder",
        "donate_desc_90": "90 días de búsquedas ilimitadas en Milonga Finder",
        "donate_thanks": "🙏 ¡Muchas gracias! Tu apoyo es muy importante. ❤️",
        "rate_limit": (
            "⏳ Has usado las {limit} búsquedas gratuitas de hoy.\n\n"
            "¡Apoya el proyecto y desbloquea búsquedas ilimitadas! ☕"
        ),
        "premium_granted": (
            "🎉 ¡Gracias! Búsquedas ilimitadas activadas por <b>{days} días</b> (hasta {until}). ❤️"
        ),
        "status_premium": "⭐ <b>Estado:</b> Premium hasta <b>{until}</b>. Búsquedas ilimitadas.",
        "status_free": "🔍 <b>Estado:</b> Plan gratuito — quedan <b>{remaining}</b> de {limit} búsquedas hoy.",
        "searches_left": "\n<i>(quedan {remaining} búsqueda(s) hoy)</i>",
        "disclaimer": "ℹ️ <i>Bot de IA — la información puede ser incompleta. Verifica siempre con el organizador.</i>",
        "error": "⚠️ Algo salió mal. Inténtalo de nuevo.",
    },
}


def get_lang(language_code: str | None) -> str:
    if not language_code:
        return "en"
    return _LANG_MAP.get(language_code.split("-")[0].lower(), "en")


def t(lang: str, key: str) -> str:
    return MSG.get(lang, MSG["en"]).get(key, MSG["en"].get(key, key))
