# HACS Backend: Mehrsprachige README-Unterstützung - Implementierungsanleitung

## Übersicht

Diese Dokumentation beschreibt, wie das HACS Backend erweitert werden muss, um mehrsprachige README-Dateien zu unterstützen. Das Frontend sendet bereits einen optionalen `language`-Parameter im Websocket-Request `hacs/repository/info`.

## Backend-Repository

**Repository:** https://github.com/hacs/integration

## Frontend-Implementierung (bereits fertig)

Das Frontend sendet den `language`-Parameter im folgenden Format:

```typescript
{
  type: "hacs/repository/info",
  repository_id: "123456789",
  language: "de"  // Optional: Basis-Sprachcode (z.B. "de", "en", "fr")
}
```

**Wichtige Details:**
- Der Parameter ist **optional** und **backward-kompatibel**
- Format: Basis-Sprachcode (z.B. "de" aus "de-DE", "en" aus "en-US")
- Wird nur gesendet, wenn die Sprache nicht Englisch ist (Englisch verwendet README.md)
- Das Frontend hat automatische Fehlerbehandlung: Wenn das Backend den Parameter ablehnt, wird die Anfrage ohne Parameter wiederholt

## Backend-Implementierung

### 1. Websocket-Handler anpassen

**Datei:** `hacs/websocket/repository/info.py` (oder ähnlich)

**Aktueller Code (Beispiel):**
```python
@websocket_command(
    {
        vol.Required("type"): "hacs/repository/info",
        vol.Required("repository_id"): str,
    }
)
async def repository_info(hass, connection, msg):
    """Get repository information."""
    repository_id = msg["repository_id"]
    # ... Repository-Info abrufen ...
    return repository_info
```

**Neuer Code:**
```python
@websocket_command(
    {
        vol.Required("type"): "hacs/repository/info",
        vol.Required("repository_id"): str,
        vol.Optional("language"): str,  # Neuer optionaler Parameter
    }
)
async def repository_info(hass, connection, msg):
    """Get repository information."""
    repository_id = msg["repository_id"]
    language = msg.get("language")  # Optional: Sprachcode (z.B. "de", "en", "fr")
    
    # ... Repository-Info abrufen ...
    
    # README mit Sprachunterstützung laden
    readme_content = await get_repository_readme(repository, language)
    
    repository_info["additional_info"] = readme_content
    return repository_info
```

### 2. README-Lade-Funktion implementieren

**Neue Funktion erstellen oder bestehende erweitern:**

```python
async def get_repository_readme(repository, language: str | None = None) -> str:
    """
    Lade README-Datei mit Sprachunterstützung.
    
    Args:
        repository: Repository-Objekt
        language: Optionaler Sprachcode (z.B. "de", "en", "fr")
    
    Returns:
        README-Inhalt als String
    """
    # Wenn keine Sprache angegeben oder Englisch, verwende Standard-README
    if not language or language == "en":
        readme_path = "README.md"
    else:
        # Versuche sprachspezifische README zu laden
        readme_path = f"README.{language}.md"
    
    try:
        # Lade README vom Repository
        readme_content = await repository.get_file_contents(readme_path)
        return readme_content
    except FileNotFoundError:
        # Falls sprachspezifische README nicht existiert, verwende Standard-README
        if readme_path != "README.md":
            try:
                readme_content = await repository.get_file_contents("README.md")
                return readme_content
            except FileNotFoundError:
                return ""
        return ""
    except Exception as e:
        # Log Fehler und verwende Standard-README als Fallback
        logger.warning(f"Fehler beim Laden von {readme_path}: {e}")
        if readme_path != "README.md":
            try:
                readme_content = await repository.get_file_contents("README.md")
                return readme_content
            except FileNotFoundError:
                return ""
        return ""
```

### 3. Vollständiges Beispiel

Hier ist ein vollständiges Beispiel, wie die Implementierung aussehen könnte:

```python
import voluptuous as vol
from homeassistant.components import websocket_api
from hacs.helpers.functions.logger import getLogger

logger = getLogger()

@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/repository/info",
        vol.Required("repository_id"): str,
        vol.Optional("language"): str,  # Neuer optionaler Parameter
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def handle_repository_info(hass, connection, msg):
    """Handle repository info websocket command."""
    repository_id = msg["repository_id"]
    language = msg.get("language")  # Optional: Sprachcode
    
    hacs = get_hacs()
    
    try:
        repository = hacs.repositories.get_by_id(repository_id)
        if not repository:
            connection.send_error(
                msg["id"],
                "repository_not_found",
                f"Repository with ID {repository_id} not found",
            )
            return
        
        # Repository-Informationen abrufen
        repository_info = {
            "id": repository.data.id,
            "name": repository.data.name,
            "full_name": repository.data.full_name,
            # ... weitere Felder ...
        }
        
        # README mit Sprachunterstützung laden
        readme_content = await get_repository_readme(repository, language)
        repository_info["additional_info"] = readme_content
        
        connection.send_result(msg["id"], repository_info)
        
    except Exception as e:
        logger.error(f"Error getting repository info: {e}")
        connection.send_error(
            msg["id"],
            "error",
            str(e),
        )


async def get_repository_readme(repository, language: str | None = None) -> str:
    """
    Lade README-Datei mit Sprachunterstützung.
    
    Unterstützte Dateien:
    - README.md (Standard, wird immer verwendet wenn keine Sprache oder "en")
    - README.de.md (Deutsch)
    - README.fr.md (Französisch)
    - README.es.md (Spanisch)
    - etc.
    
    Args:
        repository: Repository-Objekt
        language: Optionaler Sprachcode (z.B. "de", "en", "fr")
    
    Returns:
        README-Inhalt als String
    """
    # Wenn keine Sprache angegeben oder Englisch, verwende Standard-README
    if not language or language == "en":
        readme_path = "README.md"
    else:
        # Versuche sprachspezifische README zu laden
        readme_path = f"README.{language}.md"
    
    try:
        # Lade README vom Repository
        # Hinweis: Die genaue Methode hängt von Ihrer Repository-Implementierung ab
        readme_content = await repository.get_file_contents(readme_path)
        return readme_content
    except FileNotFoundError:
        # Falls sprachspezifische README nicht existiert, verwende Standard-README
        if readme_path != "README.md":
            logger.debug(
                f"Sprachspezifische README {readme_path} nicht gefunden, "
                f"verwende README.md für Repository {repository.data.full_name}"
            )
            try:
                readme_content = await repository.get_file_contents("README.md")
                return readme_content
            except FileNotFoundError:
                logger.warning(
                    f"README.md nicht gefunden für Repository {repository.data.full_name}"
                )
                return ""
        return ""
    except Exception as e:
        # Log Fehler und verwende Standard-README als Fallback
        logger.warning(
            f"Fehler beim Laden von {readme_path} für Repository "
            f"{repository.data.full_name}: {e}"
        )
        if readme_path != "README.md":
            try:
                readme_content = await repository.get_file_contents("README.md")
                return readme_content
            except FileNotFoundError:
                return ""
        return ""
```

## Unterstützte Dateinamen

Das Backend sollte folgende README-Dateien unterstützen:

- `README.md` - Standard-README (Englisch oder Fallback)
- `README.de.md` - Deutsch
- `README.fr.md` - Französisch
- `README.es.md` - Spanisch
- `README.it.md` - Italienisch
- `README.nl.md` - Niederländisch
- `README.pl.md` - Polnisch
- `README.pt.md` - Portugiesisch
- `README.ru.md` - Russisch
- `README.zh.md` - Chinesisch
- etc.

**Format:** `README.{language_code}.md` (ISO 639-1 Sprachcode, 2 Buchstaben)

## Fallback-Verhalten

1. **Wenn `language` Parameter gesendet wird:**
   - Versuche `README.{language}.md` zu laden
   - Falls nicht vorhanden, verwende `README.md` als Fallback

2. **Wenn kein `language` Parameter gesendet wird:**
   - Verwende `README.md` (Standard-Verhalten, backward-kompatibel)

3. **Wenn `language` = "en" oder None:**
   - Verwende `README.md` (Englisch ist die Standard-Sprache)

## Validierung

Der `language`-Parameter sollte validiert werden:

```python
# Optional: Validierung des Sprachcodes
if language:
    # Prüfe, ob es ein gültiger 2-Buchstaben-Sprachcode ist
    if not language.isalpha() or len(language) != 2:
        logger.warning(f"Ungültiger Sprachcode: {language}, verwende README.md")
        language = None
    else:
        language = language.lower()  # Normalisiere zu Kleinbuchstaben
```

## Testing

### Test-Szenarien

1. **Repository mit nur README.md:**
   - Request ohne `language`: Sollte README.md zurückgeben ✅
   - Request mit `language: "de"`: Sollte README.md zurückgeben (Fallback) ✅

2. **Repository mit README.md und README.de.md:**
   - Request ohne `language`: Sollte README.md zurückgeben ✅
   - Request mit `language: "de"`: Sollte README.de.md zurückgeben ✅
   - Request mit `language: "fr"`: Sollte README.md zurückgeben (Fallback) ✅

3. **Repository mit nur README.de.md (kein README.md):**
   - Request ohne `language`: Sollte Fehler oder leeren String zurückgeben
   - Request mit `language: "de"`: Sollte README.de.md zurückgeben ✅

### Test-Commands

```python
# Test 1: Ohne language Parameter (backward-kompatibel)
{
    "type": "hacs/repository/info",
    "repository_id": "123456789"
}

# Test 2: Mit language Parameter
{
    "type": "hacs/repository/info",
    "repository_id": "123456789",
    "language": "de"
}

# Test 3: Mit language Parameter (Englisch)
{
    "type": "hacs/repository/info",
    "repository_id": "123456789",
    "language": "en"
}
```

## Migration und Backward-Kompatibilität

**Wichtig:** Die Implementierung muss **vollständig backward-kompatibel** sein:

- Alte Frontend-Versionen (ohne `language`-Parameter) müssen weiterhin funktionieren
- Neue Frontend-Versionen (mit `language`-Parameter) sollten funktionieren, auch wenn das Backend den Parameter noch nicht unterstützt (Frontend hat Fehlerbehandlung)

**Empfehlung:**
- Der `language`-Parameter sollte als `vol.Optional()` definiert werden
- Wenn der Parameter nicht vorhanden ist, sollte das Standard-Verhalten (README.md) verwendet werden

## Beispiel-Repository

Ein Beispiel-Repository mit mehrsprachigen READMEs:

```
repository/
├── README.md          (Englisch, Standard)
├── README.de.md       (Deutsch)
├── README.fr.md       (Französisch)
└── ...
```

## Zusammenfassung

**Was muss implementiert werden:**

1. ✅ Websocket-Handler erweitern: `vol.Optional("language"): str` hinzufügen
2. ✅ README-Lade-Funktion erweitern: Sprachspezifische README-Dateien unterstützen
3. ✅ Fallback-Logik implementieren: README.md verwenden, wenn sprachspezifische README nicht existiert
4. ✅ Validierung: Sprachcode validieren (optional, aber empfohlen)
5. ✅ Testing: Verschiedene Szenarien testen

**Frontend-Status:**
- ✅ Frontend sendet bereits den `language`-Parameter
- ✅ Frontend hat automatische Fehlerbehandlung
- ✅ Frontend ist backward-kompatibel

**Backend-Status:**
- ⏳ Backend muss noch implementiert werden (diese Dokumentation)

## Weitere Ressourcen

- **Frontend-Repository:** https://github.com/hacs/frontend
- **Backend-Repository:** https://github.com/hacs/integration
- **HACS Dokumentation:** https://hacs.xyz/docs/

## Fragen oder Probleme?

Bei Fragen zur Implementierung:
1. Prüfen Sie die Frontend-Implementierung in `src/data/repository.ts`
2. Prüfen Sie die Websocket-Nachrichten in der Browser-Konsole
3. Erstellen Sie ein Issue im Backend-Repository: https://github.com/hacs/integration/issues

