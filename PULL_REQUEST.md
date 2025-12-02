# Add Multilingual README and Description Support

## Summary

This PR adds support for multilingual README files and repository descriptions in HACS. Users will automatically see content in their Home Assistant language setting if available, with fallback to default English content.

## Changes

1. **Multilingual README Support**
   - Added `async_get_info_file_contents_with_language()` method
   - Supports `README.{language_code}.md` files (e.g., `README.de.md`, `README.fr.md`)
   - Automatic language detection with fallback to `README.md`

2. **Multilingual Description Support**
   - Added `async_get_description_with_language()` method
   - Supports `DESCRIPTION.{language_code}.txt` files (e.g., `DESCRIPTION.de.txt`, `DESCRIPTION.fr.txt`)
   - Falls back to GitHub repository description if language-specific file not found

3. **Manifest Updates**
   - Renamed `supported_languages` to `content_languages` in `hacs.json` manifest
   - Updated validator to use `content_languages` key
   - Validates language codes and checks for corresponding README files

4. **WebSocket Handler Updates**
   - Extended `hacs/repository/info` to use language for both README and descriptions
   - Extended `hacs/repositories/list` to support language parameter for descriptions

## Related PRs

- **Frontend PR:** https://github.com/hacs/frontend/pull/XXX
- **Documentation PR:** https://github.com/hacs/documentation/pull/660

## Checklist

- [x] Code follows project style guidelines
- [x] Changes are backward compatible
- [x] Code tested locally
- [x] Validators updated
- [x] WebSocket handlers updated

## Notes

- Repository maintainers can provide multilingual content using:
  - `README.{language_code}.md` for README files
  - `DESCRIPTION.{language_code}.txt` for repository descriptions
- Language codes must be 2-letter ISO 639-1 codes (e.g., `de`, `fr`, `es`)
- The `content_languages` key in `hacs.json` can optionally declare supported languages for validation

